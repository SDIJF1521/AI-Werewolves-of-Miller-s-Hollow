"""领域层共享的时间与 ID 工具。

领域层不依赖 FastAPI / WebSocket / httpx。
"""

from __future__ import annotations

import secrets
import time


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def new_token() -> str:
    return secrets.token_urlsafe(24)


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_room_code(length: int = 5) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))
