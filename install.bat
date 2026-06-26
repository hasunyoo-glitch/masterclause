@echo off
title MasterClause - Setup
echo ============================================================
echo  MasterClause - Music Contract Analyzer : Setup
echo  Installs Python (if needed) + virtual env + dependencies.
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo [!] Setup failed - see the messages above.
) else (
  echo Setup complete. Double-click run.bat to launch the app.
)
echo.
pause
