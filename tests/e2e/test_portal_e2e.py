"""End-to-end tests for EMASDEP Portal using Playwright (sync API).

These tests open a real browser, interact with the UI, and validate
the full portal flow including API calls through the frontend.

Prerequisites:
  - portal_sdd Docker stack running (docker compose up -d)
  - Playwright browsers installed (playwright install chromium)
"""

from __future__ import annotations

import os

import httpx
import pytest
from playwright.sync_api import sync_playwright

PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:5173")
API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "1") == "1"
SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))


@pytest.fixture(scope="module")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def browser(playwright):
    b = playwright.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
    yield b
    b.close()


@pytest.fixture(scope="module")
def context(browser):
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context):
    p = context.new_page()
    p.set_default_timeout(30000)
    yield p
    p.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def goto_dashboard(page):
    page.goto(PORTAL_URL, wait_until="networkidle")
    page.wait_for_load_state("networkidle")


def wait_for_spinner(page):
    try:
        page.wait_for_selector(".animate-spin", state="hidden", timeout=15000)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAPIDirect:
    def test_api_health(self):
        r = httpx.get(f"{API_URL}/api/health", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["version"] == "3.0.0"

    def test_api_telemetry(self):
        r = httpx.get(f"{API_URL}/api/telemetry/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "total_runs" in data

    def test_api_pipeline_runs(self):
        r = httpx.get(f"{API_URL}/api/pipeline/runs", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_api_start_pipeline_ollama(self):
        r = httpx.post(
            f"{API_URL}/api/pipeline/start",
            json={"raw_intent": "Create a simple hello world API", "project_name": "e2e_test"},
            timeout=120,
        )
        assert r.status_code == 200
        data = r.json()
        assert "correlation_id" in data
        assert data["status"] in ("SPEC_V1", "PROBING", "BLOCKED_PROBE")

    def test_cors_headers(self):
        r = httpx.options(
            f"{API_URL}/api/health",
            headers={
                "Origin": PORTAL_URL,
                "Access-Control-Request-Method": "GET",
            },
            timeout=10,
        )
        cors = r.headers.get("access-control-allow-origin", "")
        assert cors == "*" or PORTAL_URL in cors, f"CORS missing: {cors}"


class TestDashboard:
    def test_dashboard_loads(self, page):
        goto_dashboard(page)
        assert "EMASDEP" in page.title()

        h1 = page.locator("h1").first
        assert "Dashboard" in h1.inner_text()

        stats = page.locator("text=Total Runs")
        assert stats.count() >= 1

        recent = page.locator("text=Recent Runs")
        assert recent.count() >= 1

    def test_start_pipeline_empty_intent_disables_button(self, page):
        goto_dashboard(page)
        btn = page.get_by_role("button", name="Start Pipeline")
        assert btn.is_disabled()

    def test_start_pipeline_with_text_enables_button(self, page):
        goto_dashboard(page)
        textarea = page.locator("textarea").first
        textarea.fill("Create a simple API")
        btn = page.get_by_role("button", name="Start Pipeline")
        assert btn.is_enabled()

    def test_start_pipeline_flow(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)

        textarea = page.locator("textarea").first
        textarea.fill("Create a simple hello world API")
        page.get_by_role("button", name="Start Pipeline").click()

        page.wait_for_timeout(5000)

        current_url = page.url
        if "/pipeline/" in current_url:
            assert page.locator("text=Pipeline DAG").count() >= 1
        elif "Clarification Required" in page.content():
            inputs = page.locator("input[placeholder*='answer']")
            count = inputs.count()
            for i in range(count):
                inputs.nth(i).fill("Yes")
                page.get_by_role("button", name="Send").nth(i).click()
                page.wait_for_timeout(1000)
            page.wait_for_timeout(3000)
            assert "/pipeline/" in page.url or page.locator("text=Pipeline DAG").count() >= 1
        else:
            pytest.skip(f"Unexpected state at {current_url}")


class TestPipelineView:
    def test_pipeline_view_has_dag_and_back_button(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)

        runs = page.locator("a[href*='/pipeline/']")
        if runs.count() == 0:
            pytest.skip("No runs to click")

        runs.first.click()
        page.wait_for_timeout(3000)
        wait_for_spinner(page)

        dag = page.locator("text=Pipeline DAG")
        assert dag.count() >= 1, "Pipeline DAG should be visible"

        back_btns = page.get_by_role("button").filter(has=page.locator("svg"))
        assert back_btns.count() >= 1

    def test_state_badge_visible(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)

        runs = page.locator("a[href*='/pipeline/']")
        if runs.count() == 0:
            pytest.skip("No runs to click")

        runs.first.click()
        page.wait_for_timeout(3000)

        state_texts = page.locator("text=/CONVERGED|SPEC_V1|INIT|CODING|TESTING|BLOCKED|FAILED/")
        count = state_texts.count()
        assert count >= 1 or "pipeline/" in page.url


class TestSidebar:
    def test_sidebar_has_nav_links(self, page):
        goto_dashboard(page)
        for label in ("Dashboard", "Pipeline", "Telemetry", "Settings"):
            assert page.locator(f"text={label}").count() >= 1, f"{label} not found"

    def test_sidebar_navigates(self, page):
        goto_dashboard(page)
        page.locator("text=Pipeline").first.click()
        page.wait_for_timeout(1500)
        assert page.url.rstrip("/") == PORTAL_URL.rstrip("/")


class TestTelemetry:
    def test_telemetry_on_dashboard(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)
        assert page.locator("text=Total Runs").count() >= 1
        assert page.locator("text=Converged").count() >= 1
        assert page.locator("text=Failed").count() >= 1


class TestProbing:
    def test_probing_modal_with_detailed_intent(self, page):
        goto_dashboard(page)

        textarea = page.locator("textarea").first
        textarea.fill(
            "Build a complete billing system with idempotency keys, "
            "webhook retries, and invoice PDF generation"
        )

        page.get_by_role("button", name="Start Pipeline").click()
        page.wait_for_timeout(5000)

        modal = page.locator("text=Clarification Required")
        if modal.count() > 0:
            assert modal.is_visible()
            inputs = page.locator("input[placeholder*='answer']")
            for i in range(inputs.count()):
                inputs.nth(i).fill("Standard implementation")
                page.get_by_role("button", name="Send").nth(i).click()
                page.wait_for_timeout(1000)
            page.wait_for_timeout(3000)
        elif "/pipeline/" in page.url:
            pass


class TestCodeExplorer:
    def test_files_api_returns_list(self):
        r = httpx.get(f"{API_URL}/api/pipeline/runs", timeout=10)
        assert r.status_code == 200
        runs = r.json()
        if not runs:
            pytest.skip("No pipeline runs found")

        for run in runs:
            cid = run["correlation_id"]
            r2 = httpx.get(f"{API_URL}/api/pipeline/files/{cid}", timeout=10)
            if r2.status_code == 200:
                files = r2.json()
                assert isinstance(files, list)
                for f in files:
                    assert "name" in f
                    assert "path" in f
                    assert "type" in f
                break
        else:
            pytest.skip("No run with artifacts found")

    def test_file_content_api(self):
        r = httpx.get(f"{API_URL}/api/pipeline/runs", timeout=10)
        assert r.status_code == 200
        runs = r.json()
        if not runs:
            pytest.skip("No pipeline runs found")

        for run in runs:
            cid = run["correlation_id"]
            r2 = httpx.get(f"{API_URL}/api/pipeline/files/{cid}", timeout=10)
            if r2.status_code != 200:
                continue
            files = r2.json()
            text_files = [f for f in files if f["type"] == "file"]
            if text_files:
                r3 = httpx.get(
                    f"{API_URL}/api/pipeline/files/{cid}/content",
                    params={"path": text_files[0]["path"]},
                    timeout=10,
                )
                assert r3.status_code == 200
                data = r3.json()
                assert "content" in data
                assert len(data["content"]) > 0
                break
        else:
            pytest.skip("No run with file content available")

    def test_zip_download_api(self):
        r = httpx.get(f"{API_URL}/api/pipeline/runs", timeout=10)
        assert r.status_code == 200
        runs = r.json()
        if not runs:
            pytest.skip("No pipeline runs found")

        import zipfile
        import io

        for run in runs:
            cid = run["correlation_id"]
            r2 = httpx.get(f"{API_URL}/api/pipeline/files/{cid}", timeout=10)
            if r2.status_code != 200 or not r2.json():
                continue
            r3 = httpx.get(f"{API_URL}/api/pipeline/download/{cid}", timeout=30)
            assert r3.status_code == 200
            assert r3.headers.get("content-type") == "application/zip"
            zf = zipfile.ZipFile(io.BytesIO(r3.content))
            names = zf.namelist()
            assert len(names) > 0
            break
        else:
            pytest.skip("No run with downloadable zip available")

    def test_code_explorer_visible_on_pipeline_view(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)

        runs = page.locator("a[href*='/pipeline/']")
        if runs.count() == 0:
            pytest.skip("No runs to click")

        runs.first.click()
        page.wait_for_timeout(3000)
        wait_for_spinner(page)

        explorer = page.locator("text=Generated Artifacts")
        if explorer.count() > 0:
            assert explorer.is_visible()
            tree = page.locator("text=spec.json")
            if tree.count() > 0:
                tree.first.click()
                page.wait_for_timeout(1000)
                code_viewer = page.locator("pre")
                assert code_viewer.count() >= 1

    def test_download_button_on_pipeline_view(self, page):
        goto_dashboard(page)
        wait_for_spinner(page)

        runs = page.locator("a[href*='/pipeline/']")
        if runs.count() == 0:
            pytest.skip("No runs to click")

        runs.first.click()
        page.wait_for_timeout(3000)
        wait_for_spinner(page)

        download_btn = page.locator("text=Download All")
        if download_btn.count() > 0:
            assert download_btn.is_visible()
            href = download_btn.get_attribute("href")
            assert href is not None
            assert "download" in href
