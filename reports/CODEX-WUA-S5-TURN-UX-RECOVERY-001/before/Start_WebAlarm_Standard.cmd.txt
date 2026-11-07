@echo off
setlocal
title Web Alarm Ultra - STANDARD
set "WA_EXIT=1"
pushd "%~dp0"
if errorlevel 1 goto root_error
if not exist "%~dp0.venv\Scripts\python.exe" goto python_error
echo [STANDARD] Web Alarm Ultra - normal persistent user data.
echo This entry always uses the built-in standard launch.
echo.
"%~dp0.venv\Scripts\python.exe" -B -u -X utf8 -m web_alarm.launcher --standard
set "WA_EXIT=%ERRORLEVEL%"
popd
if not "%WA_EXIT%"=="0" goto failed
endlocal & exit /b 0

:python_error
echo [ERROR] Project Python is missing: "%~dp0.venv\Scripts\python.exe"
echo Restore the project virtual environment before launching.
popd
goto failed

:root_error
echo [ERROR] Cannot open the project folder: "%~dp0"

:failed
echo.
echo [ERROR] STANDARD launch failed with code %WA_EXIT%. Read the details above.
echo This window will stay open until you press a key.
pause
endlocal & exit /b %WA_EXIT%
