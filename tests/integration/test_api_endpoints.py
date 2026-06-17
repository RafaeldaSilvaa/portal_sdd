"""Comprehensive API endpoint tests - verifies every route."""

import pytest
from fastapi.testclient import TestClient

from emasdep.api.main import app
from emasdep.api.db.base import Base, ensure_engine
from emasdep.api.models.pipeline import PipelineRun, ProbingQuestion


@pytest.fixture(autouse=True)
def _setup_db():
    eng = ensure_engine()
    from emasdep.api.db.base import SessionLocal
    Base.metadata.create_all(bind=eng)
    yield
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_correct_json(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "3.0.0"
        assert data["platform"] == "EMASDEP"


class TestPipelineEndpoints:
    def test_start_pipeline_returns_correlation_id(self, client):
        response = client.post(
            "/api/pipeline/start",
            json={"raw_intent": "Create a billing engine", "project_name": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "correlation_id" in data
        assert data["correlation_id"].startswith("tx-")

    def test_start_pipeline_returns_probing_if_needed(self, client):
        response = client.post(
            "/api/pipeline/start",
            json={"raw_intent": "vague", "project_name": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "probing" in data

    def test_list_runs_returns_array(self, client):
        response = client.get("/api/pipeline/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_includes_started_pipeline(self, client):
        client.post(
            "/api/pipeline/start",
            json={"raw_intent": "test", "project_name": "test"},
        )
        response = client.get("/api/pipeline/runs")
        assert len(response.json()) >= 1

    def test_get_status_returns_404_for_unknown(self, client):
        response = client.get("/api/pipeline/status/tx-nonexistent")
        assert response.status_code == 404

    def test_get_status_returns_pipeline_data(self, client):
        start_resp = client.post(
            "/api/pipeline/start",
            json={"raw_intent": "Create billing", "project_name": "test"},
        )
        corr_id = start_resp.json()["correlation_id"]

        response = client.get(f"/api/pipeline/status/{corr_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == corr_id
        assert "current_state" in data
        assert "current_gate" in data
        assert "is_converged" in data


class TestProbingFlow:
    def test_answer_question_returns_200(self, client):
        start_resp = client.post(
            "/api/pipeline/start",
            json={"raw_intent": "vague intent here", "project_name": "test"},
        )
        questions = (
            start_resp.json()
            .get("probing", {})
            .get("questionnaire", [])
        )
        if not questions:
            pytest.skip("No probing questions generated")

        response = client.post(
            "/api/pipeline/answer",
            json={"question_id": questions[0]["id"], "answer": "Test answer"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "answered"

    def test_answer_unknown_question_returns_404(self, client):
        response = client.post(
            "/api/pipeline/answer",
            json={"question_id": "q_nonexistent", "answer": "test"},
        )
        assert response.status_code == 404


class TestSpecEndpoints:
    def test_get_spec_returns_404_for_unknown(self, client):
        response = client.get("/api/spec/tx-nonexistent")
        assert response.status_code == 404

    def test_put_spec_updates_spec(self, client):
        start_resp = client.post(
            "/api/pipeline/start",
            json={"raw_intent": "test", "project_name": "test"},
        )
        corr_id = start_resp.json()["correlation_id"]

        response = client.put(
            f"/api/spec/{corr_id}",
            json={"spec_json": {"test": "data"}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "updated"


class TestTelemetryEndpoints:
    def test_telemetry_stats_returns_defaults(self, client):
        response = client.get("/api/telemetry/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_runs" in data
        assert "converged_runs" in data
        assert "avg_mutation_score" in data
        assert "avg_coverage" in data

    def test_telemetry_reflects_pipeline_runs(self, client):
        client.post(
            "/api/pipeline/start",
            json={"raw_intent": "test", "project_name": "test"},
        )
        response = client.get("/api/telemetry/stats")
        assert response.json()["total_runs"] >= 1


class TestCORS:
    def test_cors_headers_present(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


class TestWebSocket:
    def test_websocket_connects(self, client):
        with client.websocket_connect("/ws/pipeline") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"


class TestErrorHandling:
    def test_invalid_json_returns_422(self, client):
        response = client.post(
            "/api/pipeline/start",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_fields_returns_422(self, client):
        response = client.post(
            "/api/pipeline/start",
            json={},
        )
        assert response.status_code == 422
