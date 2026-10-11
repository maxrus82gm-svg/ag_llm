@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment not found: .venv\Scripts\python.exe
  echo Create or restore the project virtual environment before launching.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B -u "wa4o_ui_launcher.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Web Alarm demo could not start. See the message above.
  pause
)
endlocal
