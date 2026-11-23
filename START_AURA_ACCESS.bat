@echo off
title AuraAccess Hands-Free Accessibility System
cd /d "%~dp0"
echo ==============================================================
echo   AuraAccess - Starting Hands-Free Controller & Web App
echo ==============================================================
start "AuraAccess Backend" python run_app.py
timeout /t 2 >nul
start "AuraAccess Dock" python ui/assistive_dock.py
echo.
echo Both Controller and Floating Dock are now running!
echo Dashboard: http://127.0.0.1:8000
echo.
pause
