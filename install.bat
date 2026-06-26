@echo off
chcp 65001 >nul
title MasterClause - Setup
echo ============================================================
echo  MasterClause - Music Contract Analyzer : 설치 / Setup
echo  필요한 Python, 가상환경, 의존성을 자동으로 설치합니다.
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo [!] 설치 중 문제가 발생했습니다. 위 메시지를 확인하세요. / Setup failed - see messages above.
)
pause
