@echo off
title Contractor Analytics
cd /d "%~dp0"

echo ============================================
echo   Starting Contractor Analytics...
echo ============================================
echo.

set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py -3"
if "%PYTHON%"=="" (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
)

if "%PYTHON%"=="" (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo Please install Python first:
    echo   https://www.python.org/downloads/
    echo During installation, make sure to check the box:
    echo   "Add python.exe to PATH"
    echo.
    echo Once installed, run this file again.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo First run detected - setting up the environment, this may take a few minutes...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Checking / installing required packages...
python -m pip install --quiet --disable-pip-version-check --upgrade pip
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong while installing packages ^(see above^).
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

if not exist "data" mkdir data

echo.
echo Setup complete. Data is stored in: data\contractors.db
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"

echo ============================================
echo   The dashboard will open at: http://localhost:8000
echo   From your phone (same Wi-Fi): check the address
echo   printed below by the server, then add /mobile
echo   e.g. http://192.168.X.X:8000/mobile
echo   Windows may ask for Firewall permission on first
echo   run - click "Allow access" so your phone can connect.
echo   DO NOT CLOSE THIS WINDOW - the server runs here.
echo   To stop the server, just close this window.
echo ============================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
