@echo off
title AuraAccess 1-Click Automated Setup
cd /d "%~dp0"
echo ==============================================================
echo   AuraAccess - Automated 1-Click Environment Setup
echo ==============================================================
echo.
echo [1/3] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during setup.
    pause
    exit /b 1
)
echo [OK] Python detected.
echo.
echo [2/3] Verifying and installing required packages...
python -m pip install -r requirements.txt --quiet
echo [OK] Dependencies ready.
echo.
echo [3/3] Launching AuraAccess in silent background mode...
if exist "%~dp0AuraAccess.vbs" (
    start "" wscript.exe "%~dp0AuraAccess.vbs"
) else (
    start "" pythonw run_app.py
)
echo.
echo [SUCCESS] AuraAccess is now running! Your browser will open shortly.
timeout /t 2 >nul
exit
