"""狼人杀对局状态机（纯逻辑，不依赖网络与 LLM）。

设计成同步、可单测的引擎；异步编排放在 runner.py。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from ..shared.time import now_ms
from .personas import Persona, persona_for_seat
from .roles import ROLES
from .variants import Variant, get_variant


@dataclass
class CheckResult:
    day: int
    target: int
    result: str  # wolf / good

    def to_public(self) -> dict:
        return {"day": self.day, "target": self.target, "result": self.result}


@dataclass
class GamePlayer:
    seat: int
    persona: Persona
    role: str
    alive: bool = True
    idiot_revealed: bool = False
    can_vote: bool = True
    death_day: Optional[int] = None
    death_phase: Optional[str] = None
    death_reason: Optional[str] = None
    checks: list[CheckResult] = field(default_factory=list)
    antidote: bool = True
    poison: bool = True
    guard_last: Optional[int] = None
    shot_used: bool = False
    duel_used: bool = False
    exploded: bool = False
    claim: Optional[str] = None
    trust: float = 0.5
    key_holder: bool = False

    @property
    def role_def(self):
        return ROLES[self.role]

    @property
    def camp(self) -> str:
        return self.role_def.camp

    @property
    def team(self) -> str:
        return self.role_def.team

    def public(self, reveal: bool = False) -> dict:
        return {
            "seat": self.seat,
            "name": self.persona.name,
            "avatar": self.persona.avatar,
            "title": self.persona.title,
            "color": self.persona.color,
            "alive": self.alive,
            "claim": self.claim,
            "idiotRevealed": self.idiot_revealed,
            "canVote": self.can_vote,
            "deathDay": self.death_day,
            "deathPhase": self.death_phase,
            "role": self.role if reveal else None,
            "roleName": ROLES[self.role].name if reveal else None,
            "camp": self.role_def.camp if reveal else None,
        }

    def private(self) -> dict:
        return {
            "seat": self.seat,
            "alive": self.alive,
            "role": self.role,
            "roleName": self.role_def.name,
            "camp": self.camp,
            "team": self.team,
            "summary": self.role_def.summary,
            "ability": self.role_def.ability,
            "checks": [c.to_public() for c in self.checks],
            "antidote": self.antidote,
            "poison": self.poison,
            "shotUsed": self.shot_used,
            "duelUsed": self.duel_used,
            "exploded": self.exploded,
            "trust": round(self.trust, 2),
        }


@dataclass
class NightActions:
    guard_target: Optional[int] = None
    wolf_target: Optional[int] = None
    seer_target: Optional[int] = None
    witch_save: bool = False
    witch_poison: Optional[int] = None


@dataclass
class NightResult:
    day: int
    wolf_target: Optional[int]
    saved: bool = False
    guarded: bool = False
    poisoned: Optional[int] = None
    deaths: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ExileResult:
    kind: str  # exiled / idiot / immune / tie / none
    seat: Optional[int] = None
    target: Optional[int] = None
    tie: bool = False


@dataclass
class SpeechRecord:
    day: int
    seat: int
    text: str
    claim: Optional[str] = None
    feedback: dict = field(default_factory=dict)
    inner: str = ""
    vote_intent: Optional[int] = None
    suspects: list[int] = field(default_factory=list)
    trusts: list[int] = field(default_factory=list)
    strategy: dict = field(default_factory=dict)
    created_at: int = field(default_factory=now_ms)


@dataclass
class VoteRecord:
    day: int
    votes: dict[int, Optional[int]] = field(default_factory=dict)
    exile: Optional[int] = None
    tie: bool = False
    kind: str = "normal"

    def to_public(self) -> dict:
        return {
            "day": self.day,
            "votes": [{"from": k, "to": v} for k, v in self.votes.items()],
            "exile": self.exile,
            "tie": self.tie,
            "kind": self.kind,
        }


@dataclass
class GameState:
    variant: Variant
    players: list[GamePlayer]
    day: int = 0
    phase: str = "idle"
    phase_ends_at: Optional[int] = None
    current_speaker: Optional[int] = None
    winner: Optional[str] = None
    win_reason: str = ""
    logs: list[dict] = field(default_factory=list)
    speeches: list[SpeechRecord] = field(default_factory=list)
    votes: list[VoteRecord] = field(default_factory=list)
    deaths: list[dict] = field(default_factory=list)
    last_words: list[dict] = field(default_factory=list)
    council_rounds: list[dict] = field(default_factory=list)
    night_directives: dict[int, str] = field(default_factory=dict)
    started_at: int = field(default_factory=now_ms)
    finished_at: Optional[int] = None
    trace: list[dict] = field(default_factory=list)

    # ---- 查询 ----
    def by_seat(self, seat: Optional[int]) -> Optional[GamePlayer]:
        if seat is None:
            return None
        for p in self.players:
            if p.seat == seat:
                return p
        return None

    @property
    def alive(self) -> list[GamePlayer]:
        return [p for p in self.players if p.alive]

    @property
    def wolves(self) -> list[GamePlayer]:
        return [p for p in self.players if p.camp == "wolf"]

    @property
    def alive_wolves(self) -> list[GamePlayer]:
        return [p for p in self.players if p.alive and p.camp == "wolf"]

    @property
    def alive_gods(self) -> list[GamePlayer]:
        return [p for p in self.players if p.alive and p.team == "god"]

    @property
    def alive_villagers(self) -> list[GamePlayer]:
        return [p for p in self.players if p.alive and p.team == "villager"]

    def seats(self, *, alive_only: bool = True) -> list[int]:
        return [p.seat for p in self.players if p.alive or not alive_only]

    # ---- 记录 ----
    def log(self, kind: str, text: str, **data) -> dict:
        event = {
            "id": f"ev-{len(self.logs) + 1}",
            "day": self.day,
            "phase": self.phase,
            "kind": kind,
            "text": text,
            "at": now_ms(),
            **data,
        }
        self.logs.append(event)
        return event

    def trace_event(self, **payload) -> None:
        self.trace.append({"at": now_ms(), **payload})

    # ---- 胜负 ----
    def check_winner(self) -> bool:
        if self.winner:
            return True
        wolves = len(self.alive_wolves)
        gods = len(self.alive_gods)
        villagers = len(self.alive_villagers)
        if wolves == 0:
            self.winner = "good"
            self.win_reason = "所有狼人已出局，好人阵营获胜。"
            self.finished_at = now_ms()
            self.log("system", self.win_reason)
            return True
        if gods == 0 or villagers == 0:
            self.winner = "wolf"
            self.win_reason = "狼人已完成屠边（神职或平民全部出局），狼人阵营获胜。"
            self.finished_at = now_ms()
            self.log("system", self.win_reason)
            return True
        return False

    # ---- 死亡 ----
    def kill(self, seat: int, reason: str, phase: str = "day") -> Optional[GamePlayer]:
        p = self.by_seat(seat)
        if not p or not p.alive:
            return None
        p.alive = False
        p.death_day = self.day
        p.death_phase = phase
        p.death_reason = reason
        p.can_vote = False
        self.deaths.append(
            {
                "seat": seat,
                "name": p.persona.name,
                "day": self.day,
                "phase": phase,
                "reason": reason,
            }
        )
        return p

    def reveal_death(self, seat: int) -> None:
        p = self.by_seat(seat)
        if not p:
            return
        self.log("death", f"{seat} 号 {p.persona.name} 倒牌。", seat=seat)

    # ---- 夜晚 ----
    def begin_night(self) -> None:
        self.day += 1
        self.phase = "night"

    def resolve_night(self, actions: NightActions) -> NightResult:
        """结算一晚。调用方负责在此之前询问 AI 行动。

        女巫一晚上只允许用一瓶药；如果同时给了救和毒，以救为准。
        """
        result = NightResult(day=self.day, wolf_target=actions.wolf_target)
        wolves = self.alive_wolves
        if not wolves:
            return result

        guard_player = next((p for p in self.players if p.alive and p.role == "guard"), None)
        if not guard_player or not self.variant.rules.get("guard"):
            actions.guard_target = None
        elif actions.guard_target:
            protected_target = self.by_seat(actions.guard_target)
            if not protected_target or not protected_target.alive:
                actions.guard_target = None
            elif guard_player.guard_last == actions.guard_target:
                actions.guard_target = None
                result.notes.append("守卫不能连续两晚守护同一人。")

        wolf_target = actions.wolf_target if self.by_seat(actions.wolf_target) and self.by_seat(actions.wolf_target).alive else None
        if wolf_target and self.by_seat(wolf_target).camp == "wolf":
            wolf_target = None
        result.wolf_target = wolf_target

        # 女巫救人
        witch = next((p for p in self.players if p.role == "witch" and p.alive), None)
        saved = False
        if actions.witch_save and witch and witch.antidote and wolf_target:
            saved = True
            witch.antidote = False
            result.saved = True
            result.notes.append("女巫使用了解药。")

        poison_target = actions.witch_poison if self.by_seat(actions.witch_poison) and self.by_seat(actions.witch_poison).alive else None
        if poison_target and poison_target == wolf_target and saved:
            # 救与毒同一个人没有意义，且一晚只能一瓶
            poison_target = None
        if actions.witch_save and actions.witch_poison:
            poison_target = None
            result.notes.append("女巫一晚只能使用一瓶药，毒药未生效。")
        if poison_target and witch and witch.poison:
            witch.poison = False
            result.poisoned = poison_target
            result.notes.append("女巫使用了毒药。")
        elif poison_target and (not witch or not witch.poison):
            poison_target = None

        # 守卫记录
        guard_player = next((p for p in self.players if p.role == "guard" and p.alive), None)
        if guard_player and actions.guard_target:
            guard_player.guard_last = actions.guard_target

        protected = bool(actions.guard_target) and actions.guard_target == wolf_target
        if protected:
            result.guarded = True

        if wolf_target:
            if protected and saved and self.variant.rules.get("double_save_death"):
                self.kill(wolf_target, "同守同救", "night")
                result.deaths.append({"seat": wolf_target, "reason": "同守同救", "can_revenge": True})
                result.notes.append("同守同救，目标仍然死亡。")
            elif protected:
                result.notes.append("守卫守中了刀口。")
            elif saved:
                result.notes.append("女巫救回了刀口。")
            else:
                self.kill(wolf_target, "被狼人击杀", "night")
                result.deaths.append({"seat": wolf_target, "reason": "被狼人击杀", "can_revenge": True})

        if poison_target and poison_target != wolf_target:
            self.kill(poison_target, "被女巫毒杀", "night")
            result.deaths.append({"seat": poison_target, "reason": "被女巫毒杀", "can_revenge": False})

        self.trace_event(type="night", actions=actions.__dict__, result={
            "deaths": result.deaths,
            "saved": result.saved,
            "guarded": result.guarded,
        })
        return result

    # ---- 白天 ----
    def exile(self, seat: Optional[int]) -> ExileResult:
        if not seat:
            self.log("vote", "平票，本轮无人出局。")
            return ExileResult(kind="none")
        p = self.by_seat(seat)
        if not p or not p.alive:
            return ExileResult(kind="none")
        if p.role == "idiot" and not p.idiot_revealed:
            p.idiot_revealed = True
            p.can_vote = False
            self.log("skill", f"{seat} 号 {p.persona.name} 翻开白痴牌，免于放逐，但失去投票权。", seat=seat)
            return ExileResult(kind="idiot", seat=seat)
        if p.role == "idiot" and p.idiot_revealed:
            self.log("vote", f"{seat} 号是已翻牌的白痴，本轮无人出局。", seat=seat)
            return ExileResult(kind="immune", seat=seat)
        self.kill(seat, "被放逐", "day")
        self.log("vote", f"{seat} 号 {p.persona.name} 被放逐。", seat=seat)
        return ExileResult(kind="exiled", seat=seat)

    def white_wolf_explode(self, seat: int, target: int) -> dict:
        p = self.by_seat(seat)
        t = self.by_seat(target)
        if not p or not t or not p.alive or not t.alive or p.role != "white_wolf_king" or p.exploded:
            return {"ok": False}
        p.exploded = True
        self.kill(seat, "白狼王自爆", "day")
        self.kill(target, "被白狼王带走", "day")
        self.log(
            "skill",
            f"{seat} 号 {p.persona.name} 自爆白狼王，带走了 {target} 号 {t.persona.name}！",
            seat=seat,
            target=target,
        )
        return {"ok": True, "seat": seat, "target": target}

    def knight_duel(self, seat: int, target: int) -> dict:
        p = self.by_seat(seat)
        t = self.by_seat(target)
        if not p or not t or not p.alive or not t.alive or p.role != "knight" or p.duel_used:
            return {"ok": False}
        p.duel_used = True
        if t.camp == "wolf":
            self.kill(target, "被骑士决斗", "day")
            self.log(
                "skill",
                f"{seat} 号骑士决斗 {target} 号 {t.persona.name}，命中狼人！{target} 号出局。",
                seat=seat,
                target=target,
                hit=True,
            )
            return {"ok": True, "hit": True, "seat": seat, "target": target}
        self.kill(seat, "骑士决斗失败", "day")
        self.log(
            "skill",
            f"{seat} 号骑士决斗 {target} 号 {t.persona.name}，对方是好人。骑士出局。",
            seat=seat,
            target=target,
            hit=False,
        )
        return {"ok": True, "hit": False, "seat": seat, "target": target}

    def mark_revealed(self, seat: int, claim: Optional[str]) -> None:
        p = self.by_seat(seat)
        if p and claim and claim != "none":
            p.claim = claim

    # ---- 序列化 ----
    def public_board(self) -> dict:
        claims = [
            {"seat": p.seat, "name": p.persona.name, "role": p.claim, "roleName": ROLES[p.claim].name if p.claim in ROLES else p.claim}
            for p in self.players
            if p.claim
        ]
        return {
            "day": self.day,
            "deaths": [
                {"seat": d["seat"], "name": d["name"], "day": d["day"], "phase": d["phase"]}
                for d in self.deaths
            ],
            "claims": claims,
            "votes": [v.to_public() for v in self.votes],
            "lastWords": self.last_words,
        }

    def public_state(self, reveal: bool = False, viewer_team: Optional[int] = None) -> dict:
        speeches = []
        for s in self.speeches:
            own = bool(reveal or (viewer_team is not None and s.seat == viewer_team))
            if own:
                feedback = s.feedback
            else:
                feedback = {"kind": s.feedback.get("kind"), "label": s.feedback.get("label")}
            speeches.append(
                {
                    "day": s.day,
                    "seat": s.seat,
                    "text": s.text,
                    "claim": s.claim,
                    "feedback": feedback,
                    "inner": s.inner if reveal else "",
                    "voteIntent": s.vote_intent if own else None,
                    "at": s.created_at,
                }
            )
        return {
            "day": self.day,
            "phase": self.phase,
            "phaseEndsAt": self.phase_ends_at,
            "currentSpeaker": self.current_speaker,
            "winner": self.winner,
            "winReason": self.win_reason,
            "players": [p.public(reveal=reveal) for p in self.players],
            "board": self.public_board(),
            "logs": self.logs[-80:],
            "speeches": speeches,
            "councilRounds": self.council_rounds,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
        }

    def private_for(self, seat: int) -> dict:
        p = self.by_seat(seat)
        if not p:
            return {}
        data = {"you": p.private()}
        if p.camp == "wolf":
            mates = [q for q in self.players if q.camp == "wolf" and q.seat != p.seat]
            data["wolfMates"] = [
                {"seat": q.seat, "name": q.persona.name, "alive": q.alive, "roleName": q.role_def.name}
                for q in mates
            ]
            data["wolfPlan"] = getattr(self, "wolf_plan", None)
        return data

    def review(self) -> dict:
        adoptions = [s.feedback for s in self.speeches if s.feedback]
        counts = {"full": 0, "partial": 0, "misunderstood": 0, "defy": 0, "auto": 0}
        for f in adoptions:
            k = f.get("kind", "auto")
            counts[k] = counts.get(k, 0) + 1
        total = sum(counts.values()) or 1
        agents = []
        for p in self.players:
            mine = [s for s in self.speeches if s.seat == p.seat]
            agents.append(
                {
                    "seat": p.seat,
                    "name": p.persona.name,
                    "avatar": p.persona.avatar,
                    "color": p.persona.color,
                    "title": p.persona.title,
                    "role": p.role,
                    "roleName": p.role_def.name,
                    "camp": p.camp,
                    "alive": p.alive,
                    "deathReason": p.death_reason,
                    "speechCount": len(mine),
                    "adoptions": [s.feedback for s in mine if s.feedback],
                    "inner": [s.inner for s in mine if s.inner],
                    "trust": round(p.trust, 2),
                }
            )
        return {
            "winner": self.winner,
            "winReason": self.win_reason,
            "days": self.day,
            "agents": agents,
            "adoptionCounts": counts,
            "adoptionRate": round((counts["full"] + counts["partial"]) / total, 2),
            "deaths": self.deaths,
            "votes": [v.to_public() for v in self.votes],
        }


def create_game(variant_key: str) -> GameState:
    variant = get_variant(variant_key)
    roles = list(variant.roles)
    rng = random.SystemRandom()
    rng.shuffle(roles)
    players = [
        GamePlayer(seat=i + 1, persona=persona_for_seat(i + 1), role=roles[i])
        for i in range(variant.player_count)
    ]
    state = GameState(variant=variant, players=players)
    wolves = [p.seat for p in players if p.camp == "wolf"]
    gods = [p.seat for p in players if p.team == "god"]
    state.log("system", f"对局开始：{variant.name}。{len(wolves)} 狼、{len(gods)} 神。")
    state.trace_event(type="roles", roles={p.seat: p.role for p in players})
    return state
