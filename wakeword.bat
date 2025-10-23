@echo off
taskkill /im pythonw.exe /f
cd /d "C:\Users\User\Desktop\ANA"
start "" "C:\Users\User\Desktop\ANA\.venv\Scripts\pythonw.exe" "C:\Users\User\Desktop\ANA\wake_service.py"
exit
