@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo [!] 가상환경이 없습니다. 먼저 install.bat 을 실행하세요.
  echo     Virtual environment not found. Run install.bat first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" run.py
