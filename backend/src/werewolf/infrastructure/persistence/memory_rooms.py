from __future__ import annotations

from typing import Optional

from ...domain.rooms.entities import Room


class InMemoryRoomRepository:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def add(self, room: Room) -> None:
        self._rooms[room.code] = room

    def get(self, code: str) -> Optional[Room]:
        return self._rooms.get((code or "").upper().strip())

    def remove(self, code: str) -> None:
        self._rooms.pop((code or "").upper().strip(), None)

    def list(self) -> list[Room]:
        return list(self._rooms.values())

    def exists(self, code: str) -> bool:
        return (code or "").upper().strip() in self._rooms
