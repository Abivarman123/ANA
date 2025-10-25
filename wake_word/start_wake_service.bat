@echo off
REM Start ANA Wake Word Detection Service
REM This script starts the wake word service in the background

cd /d "%~dp0"
taskkill /im pythonw.exe /f 2>nul
start "" "..\\.venv\\Scripts\\pythonw.exe" "wake_service.py"
exit

