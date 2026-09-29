@echo off
setlocal
cd /d "%~dp0"
python RUN_CONTINUITY_MVP.py
if errorlevel 1 (
  echo.
  echo The demo did not run successfully.
  pause
  exit /b 1
)
echo.
pause
