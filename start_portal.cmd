@echo off
title EMASDEP v3.0 Portal
color 0B

echo =================================================================
echo            EMASDEP v3.0 - Portal Launcher
echo    Enterprise Multi-Agent Spec-Driven Engineering Platform
echo =================================================================
echo.

cd /d "%~dp0"

:: 1. Check Docker
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker not found. Install Docker Desktop.
    pause
    exit /b 1
)
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Docker Desktop not running. Starting it...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    :wait_docker
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if %ERRORLEVEL% NEQ 0 goto wait_docker
)
echo [OK] Docker ready.

:: 2. Auto-create .env if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env from .env.example
    )
)

:: 3. Detect LLM provider
setlocal enabledelayedexpansion
for /f "tokens=2 delims==" %%a in ('findstr /b "EMASDEP_LLM_PROVIDER" .env 2^>nul') do set "PROVIDER=%%a"
if "!PROVIDER!"=="" set "PROVIDER=mock"
for /f "tokens=2 delims==" %%a in ('findstr /b "EMASDEP_LLM_MODEL" .env 2^>nul') do set "MODEL=%%a"
if "!MODEL!"=="" set "MODEL=llama3.2:1b"
echo [INFO] LLM: !PROVIDER! / !MODEL!
endlocal

:: 4. Build images
echo.
echo [1/3] Building Docker images...
call docker compose build --parallel
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)
echo [OK] Build complete.

:: 5. Start all services
echo.
echo [2/3] Starting all services (Ollama + Backend + Frontend)...
call docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start.
    pause
    exit /b 1
)
echo [OK] Services started.

:: 6. Wait for backend health
echo.
echo [3/3] Waiting for services to be ready...
:wait_health
timeout /t 3 /nobreak >nul
docker compose exec backend python -c "import httpx; httpx.get('http://localhost:8000/api/health').raise_for_status()" >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto wait_health
echo [OK] Backend is healthy!

echo.
echo =================================================================
echo              EMASDEP Portal is RUNNING!
echo =================================================================
echo.
echo    Frontend:  http://localhost:5173
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo    Ollama:    http://localhost:11436
echo.
echo    Stop:      double-click stop_portal.cmd
echo    Tests:     python -m pytest tests/e2e/test_portal_e2e.py -v --tb=short
echo =================================================================

:: Open browser
start http://localhost:5173

:: Live logs
echo.
echo Live logs (Ctrl+C to stop, then run stop_portal.cmd):
echo.
docker compose logs -f
