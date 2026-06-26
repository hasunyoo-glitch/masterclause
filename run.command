#!/bin/bash
# macOS launcher.
# Recommended: run `bash run.command` from Terminal (bypasses the Gatekeeper
# "could not verify ... malware" block that appears on a downloaded script).
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "[!] 가상환경이 없습니다. 먼저 install.command 를 실행하세요."
  echo "    Virtual environment not found. Run install.command first."
  exit 1
fi
exec .venv/bin/python run.py
