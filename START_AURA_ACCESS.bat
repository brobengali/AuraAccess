@echo off
title AuraAccess Silent Launcher
cd /d "%~dp0"
if exist "%~dp0AuraAccess.vbs" (
    start "" wscript.exe "%~dp0AuraAccess.vbs"
    exit
)
start "" pythonw run_app.py
exit
