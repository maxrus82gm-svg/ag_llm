@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Не найден .venv\Scripts\pythonw.exe
    echo Папка запуска: %CD%
    pause
    exit /b 1
)

if not exist "ultra_ui.py" (
    echo [ERROR] Не найден ultra_ui.py
    echo Папка запуска: %CD%
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "ultra_ui.py"
exit /b 0
