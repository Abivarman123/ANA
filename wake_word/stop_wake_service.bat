@echo off
REM Stop ANA Wake Word Detection Service
REM This script stops all pythonw.exe processes (wake word service)

echo Stopping ANA Wake Word Service...
taskkill /im pythonw.exe /f
echo Done.
exit
