@echo off
title Contractor Analytics - Start (Docker)
cd /d "%~dp0"

echo ============================================
echo   Starting Contractor Analytics (Docker)...
echo ============================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker Desktop was not found.
    echo.
    echo Please install Docker Desktop first:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    echo Once installed, open Docker Desktop and run this file again.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker Desktop is installed but not running.
    echo Open Docker Desktop, wait until it fully starts, then run this file again.
    pause
    exit /b 1
)

echo Building and starting containers, this may take a few minutes on first run...
echo.

docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong while starting the containers ^(see above^).
    pause
    exit /b 1
)

echo.
echo Server started. Opening the browser...
timeout /t 3 /nobreak >nul
start "" http://localhost:8000

echo.
echo ============================================
echo   Ready! Dashboard: http://localhost:8000
echo   Closing this window does NOT stop the app.
echo   To stop it, run "stop-docker.bat".
echo ============================================
pause
