"""Anthropic API key storage and validation (plan §5.1 step 0, §10).

The key is entered in the GUI, validated with a cheap test call, and stored in
the Windows Credential Manager via ``keyring`` — never written to config.json
and never re-displayed in plaintext (only a masked form).
"""
from __future__ import annotations

import config


class ApiKeyError(Exception):
    pass


def _keyring():
    try:
        import keyring
    except ImportError as exc:  # pragma: no cover
        raise ApiKeyError(
            "keyring 패키지가 설치되지 않았습니다. requirements.txt를 설치하세요."
        ) from exc
    return keyring


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def load_key() -> str | None:
    kr = _keyring()
    try:
        return kr.get_password(config.KEYRING_SERVICE, config.KEYRING_USERNAME)
    except Exception:  # pragma: no cover - backend issues
        return None


def save_key(key: str) -> None:
    key = (key or "").strip()
    if not key:
        raise ApiKeyError("빈 키는 저장할 수 없습니다.")
    _keyring().set_password(config.KEYRING_SERVICE, config.KEYRING_USERNAME, key)


def delete_key() -> None:
    kr = _keyring()
    try:
        kr.delete_password(config.KEYRING_SERVICE, config.KEYRING_USERNAME)
    except Exception:  # pragma: no cover - not present is fine
        pass


def has_key() -> bool:
    return bool(load_key())


def masked(key: str | None) -> str:
    """Return a masked form, e.g. 'sk-ant-...AB12', for status display."""
    if not key:
        return "(설정되지 않음)"
    key = key.strip()
    if len(key) <= 10:
        return "설정됨 (****)"
    return f"{key[:7]}…{key[-4:]}"


# --------------------------------------------------------------------------- #
# Validation ("connection test")
# --------------------------------------------------------------------------- #
def validate_key(key: str) -> tuple[bool, str]:
    """Send a tiny request to confirm the key works.

    Returns (ok, message_key). ``message_key`` is an i18n key the UI localizes
    (``apikey.fail`` may carry a ``|detail`` suffix). Never raises for ordinary
    auth/network failures.
    """
    key = (key or "").strip()
    if not key:
        return False, "apikey.empty"
    try:
        import anthropic
    except ImportError:
        return False, "apikey.no_sdk"

    client = anthropic.Anthropic(api_key=key)
    try:
        client.messages.create(
            model=config.MODEL_VALIDATION,
            max_tokens=8,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "apikey.ok"
    except anthropic.AuthenticationError:
        return False, "apikey.auth_fail"
    except anthropic.PermissionDeniedError:
        return False, "apikey.perm"
    except anthropic.APIConnectionError:
        return False, "apikey.net"
    except anthropic.RateLimitError:
        # Reaching the rate limit still proves the key authenticates.
        return True, "apikey.rate_ok"
    except Exception as exc:  # pragma: no cover - unexpected
        return False, f"apikey.fail|{exc}"
