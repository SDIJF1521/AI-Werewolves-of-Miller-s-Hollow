"""房间应用服务：编排领域对象、凭据、AI 工厂与实时推送。

接口层（FastAPI / WebSocket）只调用这里的用例，不直接改领域状态。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ...domain.game.entities import create_game
from ...domain.rooms.entities import Member, ModelProfile, Room, create_room
from ...domain.shared.time import new_room_code
from ..ports.ai import AIAgent, AIAgentFactory, AIConfig
from ..ports.realtime import RealtimePort
from ..ports.repositories import RoomRepository
from ..ports.security import CredentialVault
from ..presenters import room_public, snapshot, team_private
from .game_runner import GameRunner
from .notifier import RoomNotifier


@dataclass
class GameSession:
    runner: GameRunner
    director: AIAgent
    notifier: RoomNotifier
    task: Optional[asyncio.Task] = None


class RoomService:
    def __init__(
        self,
        rooms: RoomRepository,
        realtime: RealtimePort,
        vault: CredentialVault,
        ai_factory: AIAgentFactory,
    ):
        self.rooms = rooms
        self.realtime = realtime
        self.vault = vault
        self.ai_factory = ai_factory
        self.sessions: dict[str, GameSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_or_raise(self, code: str) -> Room:
        room = self.rooms.get(code)
        if not room:
            raise LookupError("房间不存在或已解散")
        return room

    def create(self, *, host_name: str, room_name: str, variant_key: str, timing: str, mode: str = "multiplayer") -> Room:
        for _ in range(32):
            code = new_room_code()
            if not self.rooms.exists(code):
                room = create_room(
                    code=code,
                    name=room_name,
                    host_name=host_name,
                    variant_key=variant_key,
                    timing=timing,
                    mode=mode,
                )
                self.rooms.add(room)
                return room
        raise RuntimeError("无法生成房间号，请重试")

    def statuses(self, room: Room) -> list[dict]:
        session = self.sessions.get(room.code)
        return session.director.status_public() if session else []

    def snapshot(self, room: Room, member: Member) -> dict:
        return snapshot(room, member, self.statuses(room))

    def room_public(self, room: Room) -> dict:
        return room_public(room)

    # ------------------------------------------------------------------
    # 实时
    # ------------------------------------------------------------------
    def notifier_for(self, room: Room) -> RoomNotifier:
        session = self.sessions.get(room.code)
        statuses = (lambda: session.director.status_public()) if session else (lambda: [])
        return RoomNotifier(room, self.realtime, statuses)

    async def broadcast_snapshot(self, room: Room) -> None:
        await self.notifier_for(room).snapshot()

    async def presence(self, room: Room, member: Member, connected: bool) -> None:
        member.connected = connected
        await self.realtime.broadcast(
            room.code,
            {
                "type": "presence",
                "data": {"memberId": member.id, "name": member.name, "connected": connected},
            },
        )
        await self.broadcast_snapshot(room)

    # ------------------------------------------------------------------
    # 大厅用例
    # ------------------------------------------------------------------
    async def join(self, room: Room, name: str, team_seat: Optional[int], spectator: bool) -> Member:
        member = room.join(name, team_seat, spectator)
        await self.broadcast_snapshot(room)
        return member

    async def assign_team(self, room: Room, member: Member, seat: Optional[int]) -> None:
        old = member.team_seat
        room.assign_team(member, seat)
        if old and old != seat:
            self.vault.delete(room.code, old)
        await self.broadcast_snapshot(room)

    async def set_captain(self, room: Room, actor: Member, team_seat: int, captain_id: Optional[str]) -> None:
        if actor.id != room.host_id:
            raise PermissionError("只有房主可以指定队长")
        room.set_captain(team_seat, captain_id)
        await self.broadcast_snapshot(room)

    async def set_key(self, room: Room, member: Member, config: AIConfig) -> None:
        cfg = config.normalized()
        if not member.team_seat:
            raise ValueError("请先选择一个 AI 智囊团")
        if not cfg.api_key:
            old = self.vault.get(room.code, member.team_seat)
            if old and old.api_key:
                cfg.api_key = old.api_key
        if not cfg.api_key:
            raise ValueError("API Key 不能为空")
        if not cfg.model:
            raise ValueError("请填写模型名称")
        if not cfg.base_url:
            raise ValueError("请填写 API Base URL")
        profile = ModelProfile(
            provider=cfg.provider,
            base_url=cfg.base_url,
            model=cfg.model,
            masked_key=cfg.masked_key,
        )
        room.bind_model(member, profile)
        self.vault.put(room.code, member.team_seat, cfg)
        await self.broadcast_snapshot(room)

    async def clear_key(self, room: Room, member: Member, seat: int) -> None:
        room.unbind_model(member, seat)
        self.vault.delete(room.code, seat)
        await self.broadcast_snapshot(room)

    async def start_game(self, room: Room, actor: Member) -> None:
        if actor.id != room.host_id:
            raise PermissionError("只有房主可以开始对局")
        lock = self._locks.setdefault(room.code, asyncio.Lock())
        async with lock:
            if room.status != "lobby":
                raise ValueError("对局已经开始了")
            configs = {
                seat: cfg
                for seat, cfg in self.vault.configs_for(room.code).items()
                if room.teams.get(seat) and room.teams[seat].has_key
            }
            game = create_game(room.variant_key)
            room.start_game(game)
            director = self.ai_factory.create(configs, seed=abs(hash(room.code)) % 100000)
            notifier = RoomNotifier(room, self.realtime, lambda: director.status_public())
            runner = GameRunner(room, game, director, notifier)
            session = GameSession(runner=runner, director=director, notifier=notifier)
            self.sessions[room.code] = session
            room.close_all_voice("对局开始，语音已收起；密聊阶段再开。")
            await self.realtime.broadcast(
                room.code,
                {"type": "voice_closed", "reason": "对局开始，语音已切换为各 AI 的队内频道"},
            )
            await notifier.snapshot()
            session.task = asyncio.create_task(runner.run(), name=f"game-{room.code}")
            if session.task:
                session.task.add_done_callback(lambda _task: self.vault.clear_room(room.code))

    # ------------------------------------------------------------------
    # 密聊 / 策略 / 锁票
    # ------------------------------------------------------------------
    async def chat(self, room: Room, member: Member, text: str) -> dict:
        msg = room.add_chat(member, text)
        await self.notifier_for(room).team_event(member.team_seat, "chat", msg)  # type: ignore[arg-type]
        return msg

    async def lobby_chat(self, room: Room, member: Member, text: str) -> dict:
        msg = room.add_lobby_chat(member, text)
        await self.realtime.broadcast(room.code, {"type": "lobby_chat", "data": msg})
        return msg

    async def submit_package(self, room: Room, member: Member, raw: dict) -> None:
        room.submit_package(member, raw)
        notifier = self.notifier_for(room)
        await notifier.team_event(member.team_seat, "team_update", team_private(room, member))  # type: ignore[arg-type]
        await notifier.snapshot()
        if room.all_staffed_teams_locked() and room.code in self.sessions:
            self.sessions[room.code].runner.advance()

    async def submit_night_order(self, room: Room, member: Member, raw: dict) -> None:
        room.submit_night_order(member, raw)
        notifier = self.notifier_for(room)
        await notifier.team_event(member.team_seat, "team_update", team_private(room, member))  # type: ignore[arg-type]
        await notifier.snapshot()
        if room.all_staffed_teams_ordered() and room.code in self.sessions:
            self.sessions[room.code].runner.advance()

    async def lock_team(self, room: Room, member: Member) -> None:
        room.lock_team(member)
        notifier = self.notifier_for(room)
        await notifier.team_event(member.team_seat, "team_update", team_private(room, member))  # type: ignore[arg-type]
        await notifier.snapshot()
        if room.all_staffed_teams_locked() and room.code in self.sessions:
            self.sessions[room.code].runner.advance()

    async def reset_lock(self, room: Room, member: Member) -> None:
        room.reset_lock(member)
        await self.notifier_for(room).team_event(
            member.team_seat, "team_update", team_private(room, member)  # type: ignore[arg-type]
        )

    async def vote_advice(self, room: Room, member: Member, seat: Optional[int]) -> None:
        room.submit_vote_advice(member, seat)
        notifier = self.notifier_for(room)
        await notifier.team_event(member.team_seat, "team_update", team_private(room, member))  # type: ignore[arg-type]
        await notifier.snapshot()
        if room.all_staffed_teams_advised() and room.code in self.sessions:
            self.sessions[room.code].runner.advance()

    def advance(self, room: Room, actor: Member) -> None:
        if actor.id != room.host_id:
            raise PermissionError("只有房主可以推进阶段")
        session = self.sessions.get(room.code)
        if session:
            session.runner.advance()

    # ------------------------------------------------------------------
    # 语音信令
    # ------------------------------------------------------------------
    async def _voice_event(self, room: Room, member: Member, event: str, data: dict) -> None:
        channel = room.voice_channel_members(member)
        if room.status == "lobby":
            member_ids = channel | {member.id}
        else:
            member_ids = channel
        await self.realtime.broadcast_members(room.code, member_ids, {"type": event, "data": data})

    async def voice_join(self, room: Room, member: Member) -> list[dict]:
        peers = room.voice_join(member)
        notifier = self.notifier_for(room)
        await notifier.send(member.id, {"type": "voice_peers", "data": {"peers": peers, "selfId": member.id}})
        await self._voice_event(room, member, "voice_peer_joined", {"memberId": member.id, "name": member.name})
        await notifier.snapshot()
        return peers

    async def voice_leave(self, room: Room, member: Member) -> None:
        room.voice_leave(member)
        await self._voice_event(room, member, "voice_peer_left", {"memberId": member.id})
        await self.broadcast_snapshot(room)

    async def voice_signal(self, room: Room, member: Member, target: str, signal: dict) -> None:
        channel = room.voice_channel_members(member)
        if member.id not in channel or target not in channel:
            return
        await self.realtime.send(
            room.code,
            target,
            {
                "type": "voice_signal",
                "from": member.id,
                "fromName": member.name,
                "signal": signal,
            },
        )

    async def voice_state(self, room: Room, member: Member, muted: bool, speaking: bool) -> None:
        channel = room.voice_channel_members(member)
        if member.id not in channel:
            return
        member.voice_muted = muted
        member.voice_speaking = speaking
        await self._voice_event(room, member, "voice_state", {"memberId": member.id, "muted": muted, "speaking": speaking})
