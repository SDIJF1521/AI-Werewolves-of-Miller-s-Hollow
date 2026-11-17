"""房间聚合根。

这里只有“房间/成员/队伍/策略/语音状态”的业务规则：
不出现 FastAPI、WebSocket、asyncio、httpx，也不负责序列化。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..council.night import NightOrder
from ..council.strategy import (
    Adoption,
    AggregatedStrategy,
    Contributor,
    StrategyPackage,
    aggregate_packages,
)
from ..game.entities import GameState
from ..game.personas import persona_for_seat
from ..game.variants import LIE_LEVELS, POSTURES, TIMINGS, get_variant
from ..shared.time import new_id, new_room_code, new_token, now_ms

MAX_LOBBY_VOICE = 8
MIN_PLAYERS = 9
MAX_PLAYERS_PER_AI = 3


@dataclass(frozen=True)
class ModelProfile:
    """AI 模型绑定元数据。

    API Key 明文不进入领域层，由 application 的 CredentialVault 保管。
    masked_key 只用于 UI 展示。
    """

    provider: str
    base_url: str
    model: str
    masked_key: str = ""

    def public(self) -> dict:
        return {
            "hasKey": True,
            "provider": self.provider,
            "baseUrl": self.base_url,
            "model": self.model,
            "maskedKey": self.masked_key,
        }


@dataclass
class Member:
    id: str
    name: str
    token: str
    team_seat: Optional[int] = None
    is_host: bool = False
    joined_at: int = field(default_factory=now_ms)
    connected: bool = False
    disconnected_at: Optional[int] = None
    reconnect_deadline: Optional[int] = None
    voice_muted: bool = False
    voice_speaking: bool = False
    last_chat_at: float = 0.0

    @property
    def is_spectator(self) -> bool:
        return self.team_seat is None


@dataclass
class TeamState:
    seat: int
    captain_id: Optional[str] = None
    key_profile: Optional[ModelProfile] = None
    key_holder_id: Optional[str] = None
    packages: dict[str, StrategyPackage] = field(default_factory=dict)
    locked: bool = False
    advice: dict[str, int] = field(default_factory=dict)
    night_order: Optional[NightOrder] = None
    night_locked: bool = False
    night_feedback: Optional[dict] = None
    chat: list[dict] = field(default_factory=list)
    voice: set[str] = field(default_factory=set)
    final_aggregate: Optional[AggregatedStrategy] = None
    public_adoption: Optional[Adoption] = None
    managed: bool = False

    @property
    def has_key(self) -> bool:
        return self.key_profile is not None

    def key_public(self) -> dict:
        if not self.key_profile:
            return {"hasKey": False, "provider": "", "model": "", "maskedKey": "", "baseUrl": ""}
        return self.key_profile.public()


class Room:
    def __init__(
        self,
        *,
        code: str,
        name: str,
        host_name: str,
        variant_key: str,
        timing: str = "standard",
        mode: str = "multiplayer",
    ):
        self.code = code
        self.name = (name or "").strip()[:24] or f"{code} 的牌局"
        self.variant_key = variant_key
        self.timing = timing if timing in TIMINGS else "standard"
        self.mode = mode if mode in ("multiplayer", "practice") else "multiplayer"
        self._timings = dict(TIMINGS[self.timing])
        self.host_id: Optional[str] = None
        self.members: dict[str, Member] = {}
        self.teams: dict[int, TeamState] = {}
        self.status = "lobby"  # lobby / playing / finished
        self.created_at = now_ms()
        self.game: Optional[GameState] = None
        self.lobby_voice: set[str] = set()
        self.wolf_voice: set[str] = set()
        self.lobby_chat: list[dict] = []
        self.offline_ai: set[int] = set()

        variant = get_variant(variant_key)
        for seat in range(1, variant.player_count + 1):
            self.teams[seat] = TeamState(seat=seat)

        host = Member(
            id=new_id("host"),
            name=(host_name or "房主").strip()[:16] or "房主",
            token=new_token(),
            is_host=True,
        )
        self.members[host.id] = host
        self.host_id = host.id
        self.lobby_chat.append(
            {
                "id": "sys_lobby",
                "memberId": "system",
                "name": "系统",
                "text": "候场区已开放。先和桌上的人聊聊，再选你要辅佐的 AI。",
                "at": now_ms(),
                "day": 0,
                "system": True,
            }
        )

    # ------------------------------------------------------------------
    # 基础查询
    # ------------------------------------------------------------------
    @property
    def variant(self):
        return get_variant(self.variant_key)

    @property
    def timings(self) -> dict:
        return self._timings

    def member(self, member_id: Optional[str]) -> Optional[Member]:
        return self.members.get(member_id) if member_id else None

    def team_members(self, seat: int) -> list[Member]:
        return sorted(
            [m for m in self.members.values() if m.team_seat == seat],
            key=lambda m: (not m.is_host, m.joined_at),
        )

    def team_member_ids(self, seat: int) -> set[str]:
        return {m.id for m in self.team_members(seat)}

    def is_ai_offline(self, seat: int) -> bool:
        return seat in self.offline_ai

    def mark_ai_offline(self, seat: int) -> None:
        if seat in self.teams:
            self.offline_ai.add(seat)
            team = self.teams[seat]
            team.night_locked = True
            team.advice.clear()
            team.locked = True

    def mark_disconnected(self, member: Member, *, grace_ms: int, now: Optional[int] = None) -> None:
        current = now if now is not None else now_ms()
        member.connected = False
        member.disconnected_at = current
        member.reconnect_deadline = current + grace_ms

    def mark_reconnected(self, member: Member) -> None:
        member.connected = True
        member.disconnected_at = None
        member.reconnect_deadline = None

    def remove_member(self, member_id: str) -> dict:
        """超时移除玩家。

        返回 seat / keyCleared / offline，供 application 清理 Key 与广播。
        """
        member = self.members.get(member_id)
        if not member:
            return {"removed": False, "seat": None, "keyCleared": False, "offline": False}
        seat = member.team_seat
        was_host = member.is_host
        key_cleared = False
        offline = False

        if seat is not None and seat in self.teams:
            team = self.teams[seat]
            team.packages.pop(member.id, None)
            team.advice.pop(member.id, None)
            team.voice.discard(member.id)
            if team.key_holder_id == member.id:
                team.key_profile = None
                team.key_holder_id = None
                key_cleared = True
            if team.captain_id == member.id:
                team.captain_id = None

        self.lobby_voice.discard(member.id)
        self.wolf_voice.discard(member.id)
        del self.members[member_id]

        if seat is not None and seat in self.teams:
            team = self.teams[seat]
            self.auto_captain(team)
            if not self.team_members(seat) and team.managed and self.status == "playing":
                self.mark_ai_offline(seat)
                offline = True

        if was_host:
            remaining = sorted(self.members.values(), key=lambda m: m.joined_at)
            if remaining:
                self.host_id = remaining[0].id
                remaining[0].is_host = True
            else:
                self.host_id = None
        return {
            "removed": True,
            "member": member,
            "seat": seat,
            "keyCleared": key_cleared,
            "offline": offline,
        }

    def member_weight(self, member: Member) -> float:
        weight = 1.0
        team = self.teams.get(member.team_seat or 0)
        if team:
            if team.captain_id == member.id:
                weight += 0.3
            if team.key_holder_id == member.id and team.has_key:
                weight += 1.0
        return round(weight, 2)

    def auto_captain(self, team: TeamState) -> None:
        ids = [m.id for m in self.team_members(team.seat)]
        if team.captain_id in ids:
            return
        if team.key_holder_id in ids:
            team.captain_id = team.key_holder_id
        elif self.host_id in ids:
            team.captain_id = self.host_id
        else:
            team.captain_id = ids[0] if ids else None

    def ai_persona(self, seat: int):
        if self.game:
            p = self.game.by_seat(seat)
            if p:
                return p.persona
        return persona_for_seat(seat)

    # ------------------------------------------------------------------
    # 加入 / 换队 / 队长 / 模型绑定
    # ------------------------------------------------------------------
    def check_name(self, name: str, exclude: Optional[str] = None) -> str:
        clean = (name or "").strip()[:16]
        if not clean:
            raise ValueError("请填写昵称")
        for m in self.members.values():
            if m.id != exclude and m.name.lower() == clean.lower():
                raise ValueError("这个昵称已被占用，换一个吧")
        return clean

    def _validate_team_assignment(self, seat: int) -> None:
        if self.status != "lobby":
            raise ValueError("对局已经开始，只能观战")
        if seat not in self.teams:
            raise ValueError("无效的 AI 座位")
        if len(self.team_members(seat)) >= MAX_PLAYERS_PER_AI:
            raise ValueError(f"{seat} 号 AI 的智囊团已满（最多 {MAX_PLAYERS_PER_AI} 人）")

    def join(self, name: str, team_seat: Optional[int] = None, spectator: bool = False) -> Member:
        if len(self.members) >= 48:
            raise ValueError("房间人数已满")
        clean = self.check_name(name)
        if self.status != "lobby":
            spectator = True
            team_seat = None
        if not spectator and team_seat is not None:
            self._validate_team_assignment(team_seat)
        member = Member(
            id=new_id("p"),
            name=clean,
            token=new_token(),
            team_seat=None if spectator else team_seat,
        )
        self.members[member.id] = member
        if member.team_seat:
            self.auto_captain(self.teams[member.team_seat])
        return member

    def assign_team(self, member: Member, seat: Optional[int]) -> None:
        if self.status != "lobby":
            raise ValueError("对局开始后不能更换队伍")
        old = member.team_seat
        if seat is not None:
            self._validate_team_assignment(seat)
        if old and old in self.teams:
            old_team = self.teams[old]
            old_team.packages.pop(member.id, None)
            old_team.advice.pop(member.id, None)
            old_team.voice.discard(member.id)
            if old_team.key_holder_id == member.id:
                old_team.key_profile = None
                old_team.key_holder_id = None
            if old_team.captain_id == member.id:
                old_team.captain_id = None
            self.auto_captain(old_team)
        member.team_seat = seat
        member.voice_muted = False
        member.voice_speaking = False
        if seat is not None:
            self.auto_captain(self.teams[seat])

    def set_captain(self, team_seat: int, member_id: Optional[str]) -> None:
        if self.status != "lobby":
            raise ValueError("对局开始后不能更换队长")
        team = self.teams.get(team_seat)
        if not team:
            raise ValueError("无效的 AI 座位")
        if member_id is None:
            team.captain_id = None
            self.auto_captain(team)
            return
        member = self.members.get(member_id)
        if not member or member.team_seat != team_seat:
            raise ValueError("队长必须是该 AI 的智囊团成员")
        team.captain_id = member_id

    def bind_model(self, member: Member, profile: ModelProfile) -> None:
        if self.status != "lobby":
            raise ValueError("请在开局前配置 API Key")
        if not member.team_seat:
            raise ValueError("请先选择一个 AI 智囊团")
        if not profile.provider or not profile.model:
            raise ValueError("模型配置不完整")
        team = self.teams[member.team_seat]
        team.key_profile = profile
        team.key_holder_id = member.id
        self.auto_captain(team)

    def unbind_model(self, member: Member, team_seat: int) -> None:
        if self.status != "lobby":
            raise ValueError("对局开始后不能修改 API Key")
        team = self.teams.get(team_seat)
        if not team:
            raise ValueError("无效的 AI 座位")
        if member.id != self.host_id and team.key_holder_id != member.id:
            raise ValueError("只有房主或 Key 提供者可以移除 Key")
        team.key_profile = None
        team.key_holder_id = None
        self.auto_captain(team)

    # ------------------------------------------------------------------
    # 开局 / 结束
    # ------------------------------------------------------------------
    def start_game(self, game: GameState) -> None:
        if self.status != "lobby":
            raise ValueError("对局已经开始了")
        players = sum(1 for seat in self.teams if self.team_members(seat))
        if self.mode == "practice":
            if players < 1:
                raise ValueError("训练局至少需要 1 名玩家才能开局")
            if players > self.variant.player_count:
                raise ValueError("训练局玩家数超过 AI 座位数")
        else:
            if players < MIN_PLAYERS:
                raise ValueError(f"至少需要 {MIN_PLAYERS} 名玩家才能开局，当前 {players} 人")
            empty_seats = [seat for seat in self.teams if not self.team_members(seat)]
            if empty_seats:
                seats = "、".join(f"{seat}号" for seat in empty_seats[:4])
                raise ValueError(f"标准局要求每个 AI 至少有 1 名玩家；{seats} AI 还没有玩家")
            missing_keys = [seat for seat, team in self.teams.items() if not team.has_key]
            if missing_keys:
                seats = "、".join(f"{seat}号" for seat in missing_keys[:4])
                raise ValueError(f"标准局要求每个 AI 至少有 1 名玩家配置 API Key；{seats} AI 还没有配置")
        if any(len(self.team_members(seat)) > MAX_PLAYERS_PER_AI for seat in self.teams):
            raise ValueError(f"每个 AI 最多绑定 {MAX_PLAYERS_PER_AI} 名玩家")
        if game.variant.key != self.variant_key:
            raise ValueError("板子不匹配")
        if len(game.players) != self.variant.player_count:
            raise ValueError("玩家人数不匹配")
        self.game = game
        self.status = "playing"
        self.offline_ai.clear()
        for seat, team in self.teams.items():
            team.managed = bool(self.team_members(seat))
            p = game.by_seat(seat)
            if p:
                p.key_holder = team.key_holder_id in self.team_member_ids(seat)

    def finish(self) -> None:
        self.status = "finished"

    # ------------------------------------------------------------------
    # 对局中的实时操作
    # ------------------------------------------------------------------
    def can_use_council(self, member: Member) -> bool:
        return bool(self.game and member.team_seat and self.game.phase == "council")

    def can_use_vote_advice(self, member: Member) -> bool:
        return bool(self.game and member.team_seat and self.game.phase == "vote_advice")

    def chat_allowed(self, member: Member) -> bool:
        if not member.team_seat:
            return False
        if self.status == "lobby":
            return True
        if not self.game:
            return False
        return self.game.phase in ("night_council", "council", "vote_advice")

    def voice_allowed(self, member: Member) -> bool:
        if self.status == "lobby":
            return True
        return bool(member.team_seat and self.game)

    def _voice_channel(self, member: Member) -> set[str]:
        if self.status == "lobby":
            return self.lobby_voice
        if not member.team_seat or member.team_seat not in self.teams:
            return set()
        return self.teams[member.team_seat].voice

    def _valid_target(self, seat: Optional[int], *, allow_self: Optional[int] = None) -> Optional[int]:
        if seat is None:
            return None
        if not self.game:
            raise ValueError("对局尚未开始")
        try:
            seat = int(seat)
        except (TypeError, ValueError):
            raise ValueError("目标座位不合法")
        p = self.game.by_seat(seat)
        if not p or not p.alive:
            raise ValueError("目标座位不在场上")
        if allow_self is not None and seat == allow_self:
            raise ValueError("不能选择自己")
        return seat

    def submit_package(self, member: Member, raw: dict) -> None:
        if not self.can_use_council(member):
            raise ValueError("当前不在 80 秒密聊阶段")
        team = self.teams[member.team_seat]
        if team.locked:
            raise ValueError("队长已锁定策略包，本轮不能再改")
        seat = member.team_seat
        pkg = StrategyPackage(
            posture=str(raw.get("posture") or "表水"),
            protect_seat=raw.get("protectSeat"),
            attack_seat=raw.get("attackSeat"),
            lie_level=str(raw.get("lieLevel") or "轻度"),
            vote_seat=raw.get("voteSeat"),
            directive=str(raw.get("directive") or ""),
        ).normalized()
        if pkg.posture not in POSTURES:
            raise ValueError("姿态不合法")
        if pkg.lie_level not in LIE_LEVELS:
            raise ValueError("撒谎许可不合法")
        if not pkg.directive:
            raise ValueError("请写一句给 AI 的原话，最终策略必须由人类输入")
        for attr in ("protect_seat", "attack_seat", "vote_seat"):
            value = getattr(pkg, attr)
            if value is not None:
                setattr(pkg, attr, self._valid_target(value, allow_self=None if attr == "protect_seat" else seat))
        team.packages[member.id] = pkg
        if team.captain_id == member.id:
            team.locked = True

    def lock_team(self, member: Member) -> None:
        if not self.can_use_council(member):
            raise ValueError("当前不在 80 秒密聊阶段")
        team = self.teams[member.team_seat]
        if team.captain_id != member.id:
            raise ValueError("只有队长可以锁定全队策略包")
        team.locked = True

    def reset_lock(self, member: Member) -> None:
        if not self.can_use_council(member):
            raise ValueError("当前不在 80 秒密聊阶段")
        team = self.teams[member.team_seat]
        if team.captain_id != member.id:
            raise ValueError("只有队长可以重新打开")
        team.locked = False

    def submit_vote_advice(self, member: Member, seat: Optional[int]) -> None:
        if not self.can_use_vote_advice(member):
            raise ValueError("当前不在锁票阶段")
        target = self._valid_target(seat, allow_self=member.team_seat)
        if target is not None:
            self.teams[member.team_seat].advice[member.id] = target

    def advice_for(self, team_seat: int) -> Optional[int]:
        team = self.teams.get(team_seat)
        if not team or not team.advice:
            return None
        score: dict[int, float] = {}
        for mid, target in team.advice.items():
            member = self.members.get(mid)
            if not member:
                continue
            score[target] = score.get(target, 0.0) + self.member_weight(member)
        if not score:
            return None
        best = max(score.values())
        tied = [s for s, v in score.items() if abs(v - best) < 1e-9]
        cap = self.members.get(team.captain_id or "")
        if cap and cap.id in team.advice and team.advice[cap.id] in tied:
            return team.advice[cap.id]
        return sorted(tied)[0]

    def contributors_for(self, team: TeamState) -> dict[str, Contributor]:
        out: dict[str, Contributor] = {}
        for mid in team.packages:
            member = self.members.get(mid)
            if not member:
                continue
            out[mid] = Contributor(
                member_id=mid,
                name=member.name,
                weight=self.member_weight(member),
                is_captain=team.captain_id == mid,
                has_key=team.key_holder_id == mid and team.has_key,
            )
        return out

    def aggregate_for(self, team: TeamState) -> Optional[AggregatedStrategy]:
        if not team.packages:
            return None
        return aggregate_packages(team.packages, self.contributors_for(team), team.captain_id)

    # ------------------------------------------------------------------
    # 聊天
    # ------------------------------------------------------------------
    def add_chat(self, member: Member, text: str) -> dict:
        if not self.chat_allowed(member):
            raise ValueError("现在不是密聊时间")
        clean = (text or "").strip()
        if not clean:
            raise ValueError("消息为空")
        if len(clean) > 160:
            clean = clean[:160]
        now = time.time()
        if now - member.last_chat_at < 0.55:
            raise ValueError("说慢一点，密聊也会刷屏")
        member.last_chat_at = now
        team = self.teams[member.team_seat]
        msg = {
            "id": f"c_{int(now * 1000)}_{member.id[-4:]}",
            "memberId": member.id,
            "name": member.name,
            "text": clean,
            "at": now_ms(),
            "day": self.game.day if self.game else 0,
            "system": False,
        }
        team.chat.append(msg)
        if len(team.chat) > 120:
            team.chat = team.chat[-120:]
        return msg

    def add_lobby_chat(self, member: Member, text: str) -> dict:
        """候场大厅公共频道：所有人（含观战者）都能发言。"""
        if self.status != "lobby":
            raise ValueError("对局已开始，大厅聊天已关闭")
        clean = (text or "").strip()
        if not clean:
            raise ValueError("消息为空")
        if len(clean) > 160:
            clean = clean[:160]
        now = time.time()
        if now - member.last_chat_at < 0.55:
            raise ValueError("说慢一点，大厅也会刷屏")
        member.last_chat_at = now
        msg = {
            "id": f"l_{int(now * 1000)}_{member.id[-4:]}",
            "memberId": member.id,
            "name": member.name,
            "text": clean,
            "at": now_ms(),
            "day": 0,
            "system": False,
        }
        self.lobby_chat.append(msg)
        if len(self.lobby_chat) > 160:
            self.lobby_chat = self.lobby_chat[-160:]
        return msg

    def council_begin(self) -> None:
        for team in self.teams.values():
            team.packages.clear()
            team.locked = False
            team.advice.clear()
            team.final_aggregate = None
            team.public_adoption = None
            team.chat = [
                {
                    "id": f"sys_{int(time.time() * 1000)}",
                    "memberId": "system",
                    "name": "系统",
                    "text": "80 秒密聊开始。先读板，再提方案，填写策略包后锁定。",
                    "at": now_ms(),
                    "day": self.game.day if self.game else 0,
                    "system": True,
                }
            ]

    def begin_night_council(self) -> None:
        for team in self.teams.values():
            team.night_order = None
            team.night_locked = False
            team.night_feedback = None
            team.chat = [
                {
                    "id": f"night_{int(time.time() * 1000)}",
                    "memberId": "system",
                    "name": "系统",
                    "text": "夜间行动密谈开始。告诉 AI 你希望它今夜怎么做；它会参考你的指令、场上发言和此前票型。",
                    "at": now_ms(),
                    "day": self.game.day if self.game else 0,
                    "system": True,
                }
            ]

    def submit_night_order(self, member: Member, raw: dict) -> None:
        if not self.game or self.game.phase != "night_council":
            raise ValueError("当前不在夜间密谈阶段")
        seat = member.team_seat
        if not seat:
            raise ValueError("请先控制一个 AI")
        player = self.game.by_seat(seat)
        if not player or not player.alive:
            raise ValueError("你的 AI 已经出局")
        team = self.teams[seat]
        if team.night_locked:
            raise ValueError("本夜指令已锁定")
        action = str(raw.get("action") or "auto")
        allowed = {
            "wolf": {"auto", "kill"},
            "seer": {"auto", "check"},
            "witch": {"auto", "save", "poison", "none"},
            "guard": {"auto", "protect"},
        }.get("wolf" if player.camp == "wolf" else player.role, {"auto", "none"})
        if action not in allowed:
            raise ValueError("这个夜间行动与你的 AI 身份不匹配")
        target = raw.get("target")
        if action in ("auto", "none", "save"):
            target = None
        if target is not None:
            target = self._valid_target(int(target), allow_self=seat if action != "protect" else None)
            if action == "kill" and self.game.by_seat(target) and self.game.by_seat(target).camp == "wolf":
                raise ValueError("不能建议狼队刀自己的队友")
        order = NightOrder(
            action=action,
            target=target,
            directive=str(raw.get("directive") or ""),
        ).normalized()
        team.night_order = order
        team.night_locked = True

    def night_finalize(self) -> None:
        for team in self.teams.values():
            team.night_locked = True

    def all_staffed_teams_ordered(self) -> bool:
        for seat, team in self.teams.items():
            if not self.team_members(seat):
                continue
            if self.game and not self.game.by_seat(seat).alive:
                continue
            if not team.night_locked:
                return False
        return True

    def council_finalize(self) -> None:
        for team in self.teams.values():
            team.locked = True
            team.final_aggregate = self.aggregate_for(team)

    def all_staffed_teams_locked(self) -> bool:
        for seat, team in self.teams.items():
            if not self.team_members(seat):
                continue
            if self.game and not self.game.by_seat(seat).alive:
                continue
            if not team.locked:
                return False
        return True

    def all_staffed_teams_advised(self) -> bool:
        for seat, team in self.teams.items():
            if not self.team_members(seat):
                continue
            if self.game and not self.game.by_seat(seat).alive:
                continue
            if not team.advice:
                return False
        return True

    # ------------------------------------------------------------------
    # 语音房间状态（信令由基础设施处理）
    # ------------------------------------------------------------------
    def voice_join(self, member: Member) -> list[dict]:
        if not self.voice_allowed(member):
            raise ValueError("当前阶段语音未开放")
        if self.status == "lobby":
            if member.id not in self.lobby_voice and len(self.lobby_voice) >= MAX_LOBBY_VOICE:
                raise ValueError(f"大厅语音最多 {MAX_LOBBY_VOICE} 人，请先用文字交流")
            peers = [
                {
                    "memberId": mid,
                    "name": self.members[mid].name if mid in self.members else "",
                    "muted": self.members[mid].voice_muted if mid in self.members else False,
                }
                for mid in self.lobby_voice
                if mid != member.id and mid in self.members
            ]
            self.lobby_voice.add(member.id)
            member.voice_muted = False
            return peers

        peers = [
            {
                "memberId": mid,
                "name": self.members[mid].name if mid in self.members else "",
                "muted": self.members[mid].voice_muted if mid in self.members else False,
            }
            for mid in self.teams[member.team_seat].voice
            if mid != member.id and mid in self.members
        ]
        self.teams[member.team_seat].voice.add(member.id)
        member.voice_muted = False
        return peers

    def voice_leave(self, member: Member) -> None:
        self.lobby_voice.discard(member.id)
        self.wolf_voice.discard(member.id)
        if member.team_seat and member.team_seat in self.teams:
            self.teams[member.team_seat].voice.discard(member.id)
        member.voice_speaking = False

    def voice_channel_members(self, member: Member) -> set[str]:
        return self._voice_channel(member)

    def lobby_voice_members(self) -> list[dict]:
        out = []
        for mid in self.lobby_voice:
            m = self.members.get(mid)
            if m:
                out.append({"memberId": mid, "name": m.name, "muted": m.voice_muted, "speaking": m.voice_speaking})
        return out

    def team_voice_members(self, seat: int) -> list[dict]:
        team = self.teams.get(seat)
        if not team:
            return []
        out = []
        for mid in team.voice:
            m = self.members.get(mid)
            if m:
                out.append({"memberId": mid, "name": m.name, "muted": m.voice_muted, "speaking": m.voice_speaking})
        return out

    def close_all_voice(self, reason: str = "") -> None:
        for team in self.teams.values():
            team.voice.clear()
        self.lobby_voice.clear()
        self.wolf_voice.clear()
        for m in self.members.values():
            m.voice_speaking = False
        if reason:
            for team in self.teams.values():
                team.chat.append(
                    {
                        "id": f"voice_{int(time.time() * 1000)}",
                        "memberId": "system",
                        "name": "系统",
                        "text": reason,
                        "at": now_ms(),
                        "day": self.game.day if self.game else 0,
                        "system": True,
                    }
                )

    def phase_voice_cleanup(self) -> bool:
        # 同一 AI 的军师语音不受阶段限制，只有开局时的大厅语音会关闭。
        return False


def create_room(
    *,
    name: str,
    host_name: str,
    variant_key: str,
    timing: str,
    mode: str = "multiplayer",
    code: Optional[str] = None,
) -> Room:
    return Room(
        code=code or new_room_code(),
        name=name,
        host_name=host_name,
        variant_key=variant_key,
        timing=timing,
        mode=mode,
    )
