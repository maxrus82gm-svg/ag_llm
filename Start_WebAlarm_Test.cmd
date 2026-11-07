@echo off
setlocal
title Web Alarm Ultra - OFFLINE TEST
set "WA_EXIT=1"
pushd "%~dp0"
if errorlevel 1 goto root_error
if not exist "%~dp0.venv\Scripts\python.exe" goto python_error
echo [TEST] Web Alarm Ultra - disposable TEST data only.
echo The current test profile is selected in web_alarm\launch_test_config.json.
echo The selected TEST profile opens below. The default interface is Web.
echo Allow five seconds for the existing TEST warning.
echo In Web mode press Enter here to stop and remove temporary TEST chats.
echo.
"%~dp0.venv\Scripts\python.exe" -B -u -X utf8 -m web_alarm.launcher --config "%~dp0web_alarm\launch_test_config.json" --require-test
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
echo [ERROR] TEST launch failed with code %WA_EXIT%. Read the details above.
echo This window will stay open until you press a key.
pause
endlocal & exit /b %WA_EXIT%
