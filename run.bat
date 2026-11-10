@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (echo Python 3.11 or newer was not found on PATH.& pause& exit /b 1)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (echo Failed to create .venv.& pause& exit /b 1)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" launcher.py
exit /b 0
:error
echo Startup failed.& pause& exit /b 1
