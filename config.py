"""Central configuration: paths, model names, defaults.

All user data lives under ``%APPDATA%/ai-contract-analyzer``. Nothing here is
hard-coded into the UI or core modules — they import from this file so that
paths and the model string can be changed in one place (see plan §8, §11).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Application identity
# --------------------------------------------------------------------------- #
APP_NAME = "MasterClause - Music Contract Analyzer"
APP_SLUG = "ai-contract-analyzer"   # internal slug kept stable (data dir / keyring)
APP_VERSION = "2.0.0"

# Encoding: Windows consoles default to cp949 for Korean locales; force UTF-8.
os.environ.setdefault("PYTHONUTF8", "1")

# --------------------------------------------------------------------------- #
# Filesystem locations (never hard-code these elsewhere)
# --------------------------------------------------------------------------- #
def _appdata_root() -> Path:
    """Return the per-user data directory for this app (per-OS convention).

    Windows: ``%APPDATA%/ai-contract-analyzer``
    macOS:   ``~/Library/Application Support/ai-contract-analyzer``
    Linux:   ``$XDG_CONFIG_HOME`` (or ``~/.config``)/ai-contract-analyzer
    """
    base = os.environ.get("APPDATA")
    if base:  # Windows
        root = Path(base) / APP_SLUG
    elif sys.platform == "darwin":  # macOS
        root = Path.home() / "Library" / "Application Support" / APP_SLUG
    else:  # Linux / other
        xdg = os.environ.get("XDG_CONFIG_HOME")
        root = (Path(xdg) if xdg else Path.home() / ".config") / APP_SLUG
    root.mkdir(parents=True, exist_ok=True)
    return root


DATA_DIR: Path = _appdata_root()
CONFIG_PATH: Path = DATA_DIR / "config.json"        # user settings (no key)
HISTORY_DB_PATH: Path = DATA_DIR / "contracts.db"   # optional SQLite history

# Bundled reference data (ships with the app, not under APPDATA).
# When frozen by PyInstaller, data lives under the extraction root (_MEIPASS).
if getattr(sys, "frozen", False):
    PACKAGE_ROOT: Path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    PACKAGE_ROOT = Path(__file__).resolve().parent
BENCHMARK_DATA_DIR: Path = PACKAGE_ROOT / "data" / "benchmarks"
JURISDICTION_DATA_DIR: Path = PACKAGE_ROOT / "data" / "jurisdiction"

# --------------------------------------------------------------------------- #
# Anthropic API key storage (keyring → Windows Credential Manager)
# --------------------------------------------------------------------------- #
KEYRING_SERVICE = "ai-contract-analyzer"
KEYRING_USERNAME = "anthropic-api-key"

# --------------------------------------------------------------------------- #
# Claude model configuration
# --------------------------------------------------------------------------- #
# Default: strongest reasoning model. Switch to a lighter model for cost.
# IDs verified against the Anthropic model catalog (claude-api reference).
MODEL_PRIMARY = "claude-opus-4-8"
MODEL_LIGHT = "claude-haiku-4-5"
MODEL_VALIDATION = "claude-haiku-4-5"   # cheap call for the "connection test"

# Effort for the heavy analysis call (low | medium | high | max).
ANALYSIS_EFFORT = "high"

# Output token ceilings.
ANALYSIS_MAX_TOKENS = 32_000     # streamed (large structured result)
CONCERN_MAX_TOKENS = 8_000

# Retry budget for schema-validation failures in analyzer.py.
SCHEMA_MAX_RETRIES = 2

# Rough public pricing (USD / 1M tokens) for the optional cost estimate only.
MODEL_PRICING = {
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
}

# --------------------------------------------------------------------------- #
# Defaults for the options screen (overridable via config.json)
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "perspective": "lawyer",
    "output_language": "ko",
    "jurisdiction": "KR",
    "us_state": None,
    "output_format": "docx",
    "anonymize_before_analysis": False,
    "zero_retention": False,
    "model": MODEL_PRIMARY,
}

USER_CONCERN_MAX_LEN = 300
