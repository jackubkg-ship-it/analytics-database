@echo off
title Contractor Analytics - Stop (Docker)
cd /d "%~dp0"

echo Stopping Contractor Analytics...
docker compose down

echo.
echo Stopped. Your data is not deleted - next time you run "start-docker.bat"
echo everything will be exactly as you left it.
pause
