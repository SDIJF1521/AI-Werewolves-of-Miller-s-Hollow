from __future__ import annotations

from collections.abc import Callable

from ...domain.rooms.entities import Room
from ..ports.realtime import RealtimePort
from ..presenters import snapshot


class RoomNotifier:
    """把一个房间的领域状态翻译成实时推送。"""

    def __init__(
        self,
        room: Room,
        realtime: RealtimePort,
        status_provider: Callable[[], list[dict]],
    ):
        self.room = room
        self.realtime = realtime
        self.status_provider = status_provider

    async def broadcast(self, payload: dict) -> None:
        await self.realtime.broadcast(self.room.code, payload)

    async def send(self, member_id: str, payload: dict) -> None:
        await self.realtime.send(self.room.code, member_id, payload)

    async def error(self, member_id: str, message: str) -> None:
        await self.send(member_id, {"type": "error", "message": message})

    async def snapshot(self) -> None:
        statuses = self.status_provider()
        for member in list(self.room.members.values()):
            await self.realtime.send(
                self.room.code,
                member.id,
                {"type": "snapshot", "data": snapshot(self.room, member, statuses)},
            )

    async def team_event(self, seat: int, event: str, data: dict) -> None:
        member_ids = self.room.team_member_ids(seat)
        await self.realtime.broadcast_members(
            self.room.code,
            member_ids,
            {"type": event, "data": data},
        )
