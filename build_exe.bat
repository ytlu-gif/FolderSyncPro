@echo off
setlocal
cd /d "%~dp0"
REM Install requirements.txt in an activated Python environment first.
python build_release.py %*
if errorlevel 1 exit /b 1
endlocal
