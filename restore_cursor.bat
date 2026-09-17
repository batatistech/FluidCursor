@echo off
cd /d "%~dp0"
echo Restoring standard Windows cursor...
python main.py --restore
echo Done!
pause
