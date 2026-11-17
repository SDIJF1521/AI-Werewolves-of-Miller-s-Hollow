from __future__ import annotations

import asyncio
from collections.abc import Iterable

from fastapi import WebSocket


class Connection:
    def __init__(self, ws: WebSocket, member_id: str):
        self.ws = ws
        self.member_id = member_id
        self._lock = asyncio.Lock()
        self.closed = False

    async def send(self, payload: dict) -> bool:
        if self.closed:
            return False
        try:
            async with self._lock:
                await self.ws.send_json(payload)
            return True
        except Exception:
            self.closed = True
            return False


class WebSocketHub:
    """room_code -> member_id -> Connection。"""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, Connection]] = {}

    async def register(self, room_code: str, member_id: str, ws: WebSocket) -> Connection:
        room = self._rooms.setdefault(room_code, {})
        old = room.get(member_id)
        if old:
            old.closed = True
            try:
                await old.ws.close(code=4000, reason="new connection")
            except Exception:
                pass
        conn = Connection(ws, member_id)
        room[member_id] = conn
        return conn

    async def unregister(self, room_code: str, member_id: str, conn: Connection) -> None:
        room = self._rooms.get(room_code, {})
        if room.get(member_id) is conn:
            room.pop(member_id, None)
        if not room:
            self._rooms.pop(room_code, None)

    async def send(self, room_code: str, member_id: str, payload: dict) -> None:
        conn = self._rooms.get(room_code, {}).get(member_id)
        if conn:
            ok = await conn.send(payload)
            if not ok:
                self._rooms.get(room_code, {}).pop(member_id, None)

    async def broadcast(self, room_code: str, payload: dict) -> None:
        for member_id, conn in list(self._rooms.get(room_code, {}).items()):
            ok = await conn.send(payload)
            if not ok:
                self._rooms.get(room_code, {}).pop(member_id, None)

    async def broadcast_members(self, room_code: str, member_ids: Iterable[str], payload: dict) -> None:
        for member_id in list(member_ids):
            await self.send(room_code, member_id, payload)

    async def online(self, room_code: str) -> set[str]:
        return set(self._rooms.get(room_code, {}).keys())

    def room_count(self) -> int:
        return len(self._rooms)
