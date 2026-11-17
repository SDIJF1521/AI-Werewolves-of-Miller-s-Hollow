from __future__ import annotations

from typing import Optional

from ...application.ports.ai import AIConfig


class MemoryCredentialVault:
    """进程内凭据保险箱。

    重启即清空；生产环境应替换为 KMS / Vault / Redis 加密存储。
    """

    def __init__(self) -> None:
        self._items: dict[tuple[str, int], AIConfig] = {}

    def put(self, room_code: str, seat: int, config: AIConfig) -> None:
        self._items[(room_code.upper(), seat)] = config

    def get(self, room_code: str, seat: int) -> Optional[AIConfig]:
        return self._items.get((room_code.upper(), seat))

    def delete(self, room_code: str, seat: int) -> None:
        self._items.pop((room_code.upper(), seat), None)

    def configs_for(self, room_code: str) -> dict[int, AIConfig]:
        code = room_code.upper()
        return {seat: cfg for (c, seat), cfg in self._items.items() if c == code}

    def clear_room(self, room_code: str) -> None:
        code = room_code.upper()
        for key in [k for k in self._items if k[0] == code]:
            self._items.pop(key, None)
