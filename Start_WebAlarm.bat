@echo off
rem Web Alarm Ultra - the one permanent launcher. Double-click it or start it from a desktop shortcut.
rem It works from any current folder: everything is found next to this file, no user path is written here.
rem Standard launch: the main application with its usual persistent storage (green banner).
rem Test configurations are chosen in web_alarm\launch_config.json, never by editing this file (red banner).
setlocal
pushd "%~dp0" || (echo [ERROR] Cannot open the folder of this file. & pause & exit /b 1)
set "WA_EXE="
set "WA_PRE="
if exist "%~dp0.venv\Scripts\python.exe" set "WA_EXE=%~dp0.venv\Scripts\python.exe"
if not defined WA_EXE for %%P in (py.exe) do if not "%%~$PATH:P"=="" set "WA_EXE=%%~$PATH:P" & set "WA_PRE=-3"
if not defined WA_EXE for %%P in (python.exe) do if not "%%~$PATH:P"=="" set "WA_EXE=%%~$PATH:P"
if not defined WA_EXE (
  echo [ERROR] Python 3 was not found: no .venv\Scripts\python.exe next to this file and no py or python on PATH.
  echo Install Python 3.12 or restore the project environment, then start again.
  popd
  pause
  exit /b 1
)
if not exist "%~dp0.venv\Scripts\python.exe" echo [INFO] Project .venv not found - using Python from this computer: %WA_EXE% %WA_PRE%
"%WA_EXE%" %WA_PRE% -B -X utf8 -m web_alarm.launcher %*
set "WA_CODE=%ERRORLEVEL%"
popd
if not "%WA_CODE%"=="0" (
  echo.
  echo Web Alarm finished with code %WA_CODE%. Read the message above.
  pause
)
endlocal & exit /b %WA_CODE%
