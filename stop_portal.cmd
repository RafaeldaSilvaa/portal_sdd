@echo off
title EMASDEP v3.0 - Stopping
color 0C

echo =================================================================
echo              EMASDEP v3.0 - Shutdown
echo =================================================================
echo.

cd /d "%~dp0"

echo [1/2] Stopping all containers...
call docker compose down --remove-orphans
if %ERRORLEVEL% EQU 0 (
    echo [OK] Containers stopped.
) else (
    echo [WARN] No running containers found.
)

echo.
echo [2/2] Cleaning up local files...
if exist ".emasdep_portal.db" del /f /q ".emasdep_portal.db" >nul 2>&1
echo [OK] Done.

echo.
echo =================================================================
echo              Portal stopped successfully.
echo =================================================================
echo.
echo    Ollama model cached in Docker volume.
echo    Next start is instant (no re-download).
echo    To restart: double-click start_portal.cmd
echo =================================================================

pause
