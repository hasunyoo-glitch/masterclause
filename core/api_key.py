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

    Returns (ok, message). Never raises for ordinary auth/network failures.
    """
    key = (key or "").strip()
    if not key:
        return False, "키가 비어 있습니다."
    try:
        import anthropic
    except ImportError:
        return False, "anthropic 패키지가 설치되지 않았습니다."

    client = anthropic.Anthropic(api_key=key)
    try:
        client.messages.create(
            model=config.MODEL_VALIDATION,
            max_tokens=8,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "연결 성공: 키가 유효합니다."
    except anthropic.AuthenticationError:
        return False, "인증 실패: API 키가 올바르지 않습니다."
    except anthropic.PermissionDeniedError:
        return False, "권한 없음: 이 키로는 모델에 접근할 수 없습니다."
    except anthropic.APIConnectionError:
        return False, "네트워크 오류: 인터넷 연결을 확인하세요."
    except anthropic.RateLimitError:
        # Reaching the rate limit still proves the key authenticates.
        return True, "키는 유효합니다(현재 사용량 제한). 잠시 후 분석하세요."
    except Exception as exc:  # pragma: no cover - unexpected
        return False, f"검증 실패: {exc}"
