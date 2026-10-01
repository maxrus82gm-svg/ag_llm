@echo off
setlocal
cd /d "%~dp0"
title Desktop Commander Watchdog
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0watchdog.ps1"
endlocal
