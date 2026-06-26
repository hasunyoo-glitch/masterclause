#!/bin/bash
# macOS one-shot setup. Double-click in Finder (run `chmod +x install.command` once),
# or run `bash install.command` from Terminal.
set -e
cd "$(dirname "$0")"

echo "=== MasterClause - Music Contract Analyzer : 설치 / Setup (macOS) ==="

PY_DOWNLOAD="https://www.python.org/downloads/macos/"
PY=""
for c in python3.12 python3.11 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  if command -v brew >/dev/null 2>&1; then
    echo "Homebrew 로 Python 설치 / Installing Python via Homebrew..."
    brew install python@3.12
    PY="$(brew --prefix)/bin/python3.12"
  else
    echo "Python 3.11+ 가 필요합니다. 아래에서 설치 후 다시 실행하세요:"
    echo "Python 3.11+ is required. Install it, then run again:"
    echo "  $PY_DOWNLOAD"
    exit 1
  fi
fi

echo "사용 Python / Using Python: $PY"
"$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "=== 설치 완료! run.command 로 실행하세요 / Done. Launch with run.command ==="
