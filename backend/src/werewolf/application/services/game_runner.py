"""异步对局编排：夜晚 → 天亮 → 80 秒密聊 → AI 发言 → 锁票 → 投票 → 复盘。

服务端是唯一权威计时器。人类只影响“策略包”，不能直接替 AI 发言。
"""

from __future__ import annotations

import asyncio
import random
import time
import traceback
from dataclasses import dataclass
from typing import Optional

from ...domain.council.night import NightDecision, decide_night_order
from ...domain.council.strategy import Adoption, AggregatedStrategy, StrategyPackage, decide_adoption
from ...domain.game.entities import (
    CheckResult,
    GameState,
    NightActions,
    SpeechRecord,
    VoteRecord,
)
from ...domain.rooms.entities import Room
from ...domain.shared.time import now_ms
from ..ports.ai import AIAgent, AIResult
from .notifier import RoomNotifier


@dataclass
class RoundDecision:
    seat: int
    adoption: Adoption
    aggregate: Optional[AggregatedStrategy] = None
    auto_package: Optional[StrategyPackage] = None


class GameRunner:
    def __init__(self, room: Room, state: GameState, director: AIAgent, notifier: RoomNotifier):
        self.room = room
        self.state = state
        self.director = director
        self.notifier = notifier
        self.gate = asyncio.Event()
        self.round: dict[int, RoundDecision] = {}
        self.night_decisions: dict[int, NightDecision] = {}
        self.rng = random.Random(17)
        self.skip_vote = False
        self.finished = False
        self._phase_started = time.monotonic()

    # ------------------------------------------------------------------
    # 阶段与计时
    # ------------------------------------------------------------------
    def t(self, key: str) -> float:
        return float(self.room.timings.get(key, 10))

    async def _begin_phase(
        self,
        phase: str,
        duration: float,
        speaker: Optional[int] = None,
    ) -> None:
        if self.room.phase_voice_cleanup():
            await self.notifier.broadcast({"type": "voice_closed", "reason": "当前阶段语音已关闭"})
        self.gate = asyncio.Event()
        self._phase_started = time.monotonic()
        self.state.phase = phase
        self.state.current_speaker = speaker
        self.state.phase_ends_at = now_ms() + int(duration * 1000) if duration > 0 else None
        await self.notifier.broadcast(
            {
                "type": "phase",
                "data": {
                    "phase": phase,
                    "day": self.state.day,
                    "endsAt": self.state.phase_ends_at,
                    "duration": duration,
                    "currentSpeaker": speaker,
                    "timings": self.room.timings,
                },
            }
        )
        await self.notifier.snapshot()

    def _reset_phase_timer(self, duration: float) -> None:
        self._phase_started = time.monotonic()
        self.state.phase_ends_at = now_ms() + int(duration * 1000)

    async def _wait_phase(self, duration: float) -> None:
        elapsed = time.monotonic() - self._phase_started
        await self._wait_remaining(max(0.0, duration - elapsed))

    async def _wait_remaining(self, timeout: float) -> None:
        if timeout <= 0:
            return
        try:
            await asyncio.wait_for(self.gate.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        self.state.phase_ends_at = None

    def advance(self) -> None:
        self.gate.set()

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    async def run(self) -> None:
        try:
            while not self.state.winner and not self.finished:
                await self._night_council()
                if self.state.winner:
                    break
                await self._night()
                if self.state.winner:
                    break
                await self._dawn()
                if self.state.winner:
                    break
                await self._council()
                await self._speeches()
                if self.state.winner:
                    break

                self.skip_vote = False
                await self._special_actions()
                if self.state.winner:
                    break
                if self.skip_vote:
                    continue

                await self._vote_advice()
                await self._vote()
                if self.state.winner:
                    break
        except asyncio.CancelledError:
            return
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.state.log("system", "对局出现异常，已结束本局。")
            self.state.winner = self.state.winner or "good"
            self.state.win_reason = self.state.win_reason or f"对局异常终止：{exc}"
        finally:
            await self._finish()

    # ------------------------------------------------------------------
    # 夜晚：先密谈，再行动
    # ------------------------------------------------------------------
    async def _night_council(self) -> None:
        self.state.begin_night()
        self.room.begin_night_council()
        self.state.phase = "night_council"
        self.state.log("night_council", "夜间行动密谈开始：先和你的 AI 对齐今夜目标。")
        await self._begin_phase("night_council", self.t("night_council"))
        if self.room.all_staffed_teams_ordered():
            self.gate.set()
        await self._wait_phase(self.t("night_council"))

        self.room.night_finalize()
        self.state.log("night_council", "夜间指令锁定，AI 开始行动。")
        self.night_decisions = {}
        self.state.night_directives = {
            team.seat: (team.night_order.directive if team.night_order else "")
            for team in self.room.teams.values()
        }

        for p in self.state.alive:
            team = self.room.teams[p.seat]
            order = team.night_order
            if p.camp == "wolf":
                targets = [q.seat for q in self.state.players if q.alive and q.camp == "good"]
            elif p.role == "seer":
                targets = [q.seat for q in self.state.players if q.alive and q.seat != p.seat]
            elif p.role == "witch":
                targets = [q.seat for q in self.state.players if q.alive and q.seat != p.seat]
            elif p.role == "guard":
                targets = [q.seat for q in self.state.players if q.alive]
            else:
                targets = []
            decision = decide_night_order(
                order,
                obedience=p.persona.obedience,
                logic=p.persona.logic,
                has_key=self.director.has_key(p.seat),
                role=p.role,
                alive_targets=targets,
                rng=self.rng,
            )
            self.night_decisions[p.seat] = decision
            team.night_feedback = None
        await self.notifier.broadcast({"type": "night_orders_locked", "data": {"day": self.state.day}})
        await self.notifier.snapshot()

    async def _night(self) -> None:
        await self._begin_phase("night", self.t("night"))
        self.state.log("night", "天黑请闭眼，AI 正在参考密谈与场上发言行动。")

        guard = next((p for p in self.state.players if p.alive and p.role == "guard" and not self._offline(p.seat)), None)
        guard_target = None
        if guard:
            decision = self.night_decisions.get(guard.seat)
            if decision and decision.action == "protect" and decision.target:
                guard_target = decision.target
            else:
                guard_target = self.director.night_action(self.state, guard.seat, "guard")
            if guard_target:
                target = self.state.by_seat(guard_target)
                if not target or not target.alive:
                    guard_target = None

        seer = next((p for p in self.state.players if p.alive and p.role == "seer" and not self._offline(p.seat)), None)
        seer_target = None
        if seer:
            decision = self.night_decisions.get(seer.seat)
            if decision and decision.action == "check" and decision.target:
                seer_target = decision.target
            else:
                seer_target = self.director.night_action(self.state, seer.seat, "seer")
            if seer_target:
                target = self.state.by_seat(seer_target)
                if target and target.alive and target.seat != seer.seat:
                    result = "wolf" if target.camp == "wolf" else "good"
                    seer.checks.append(CheckResult(day=self.state.day, target=seer_target, result=result))
                    self.state.trace_event(type="seer_check", seat=seer.seat, target=seer_target, result=result)
                else:
                    seer_target = None

        wolf_target = self._resolve_wolf_target()
        self.state.wolf_plan = {
            "kill": wolf_target,
            "vote": self.director.wolf_vote_target(self.state) if self._online_wolves() else None,
        }

        witch = next((p for p in self.state.players if p.alive and p.role == "witch" and not self._offline(p.seat)), None)
        witch_save, witch_poison = (False, None)
        if witch:
            decision = self.night_decisions.get(witch.seat)
            if decision and decision.action == "save" and decision.kind != "defy":
                witch_save = bool(wolf_target)
            elif decision and decision.action == "poison" and decision.kind != "defy":
                witch_poison = decision.target
                if witch_poison and (not self.state.by_seat(witch_poison) or not self.state.by_seat(witch_poison).alive):
                    witch_poison = None
            elif decision and decision.action == "none" and decision.kind != "defy":
                witch_save, witch_poison = False, None
            else:
                witch_save, witch_poison = self.director.witch_actions(self.state, witch.seat, wolf_target)

        await self.notifier.snapshot()
        await self._wait_phase(self.t("night"))

        actions = NightActions(
            guard_target=guard_target,
            wolf_target=wolf_target,
            seer_target=seer_target,
            witch_save=witch_save,
            witch_poison=witch_poison,
        )
        self.night_result = self.state.resolve_night(actions)
        self.state.log("night", "夜晚结算完成。")
        self._record_night_feedback(guard_target, seer_target, wolf_target, witch_save, witch_poison)

    def _offline(self, seat: int) -> bool:
        return self.room.is_ai_offline(seat)

    def _online_wolves(self):
        return [p for p in self.state.alive_wolves if not self._offline(p.seat)]

    def _resolve_wolf_target(self) -> Optional[int]:
        wolves = self._online_wolves()
        if not wolves:
            return None
        votes: dict[int, float] = {}
        for wolf in wolves:
            decision = self.night_decisions.get(wolf.seat)
            target = None
            if decision and decision.action == "kill" and decision.kind != "defy" and decision.target:
                candidate = self.state.by_seat(decision.target)
                if candidate and candidate.alive and candidate.camp == "good":
                    target = decision.target
            if target is None:
                target = self.director.night_action(self.state, wolf.seat, "wolf_kill")
            candidate = self.state.by_seat(target)
            if candidate and candidate.alive and candidate.camp == "good":
                votes[target] = votes.get(target, 0.0) + (1.0 + wolf.persona.logic)
        if not votes:
            return self.director.wolf_kill_target(self.state)
        top = max(votes.values())
        choices = [seat for seat, score in votes.items() if abs(score - top) < 1e-9]
        return self.rng.choice(choices)

    def _record_night_feedback(self, guard_target, seer_target, wolf_target, witch_save, witch_poison) -> None:
        for p in self.state.players:
            team = self.room.teams[p.seat]
            decision = self.night_decisions.get(p.seat)
            if not decision:
                continue
            actual = None
            action = decision.action
            if p.camp == "wolf":
                actual = wolf_target
                action = "kill"
            elif p.role == "seer":
                actual = seer_target
                action = "check"
            elif p.role == "guard":
                actual = guard_target
                action = "protect"
            elif p.role == "witch":
                if witch_save:
                    actual = wolf_target
                    action = "save"
                elif witch_poison:
                    actual = witch_poison
                    action = "poison"
                else:
                    actual = None
                    action = "none"
            else:
                action = "none"
            if p.camp != "wolf" and p.role not in ("seer", "witch", "guard"):
                team.night_feedback = {
                    "kind": "none",
                    "label": "无夜间技能",
                    "summary": "你的 AI 本夜没有主动技能；你的嘱咐已记录，AI 会带着它进入天亮后的发言与投票。",
                    "action": "none",
                    "target": None,
                }
                continue
            summary = decision.summary
            if actual and decision.target and actual != decision.target:
                summary += f" 最终行动目标：{actual} 号。"
            elif actual:
                summary += f" 最终行动目标：{actual} 号。"
            team.night_feedback = {
                "kind": decision.kind,
                "label": decision.label,
                "summary": summary,
                "action": action,
                "target": actual,
            }

    # ------------------------------------------------------------------
    # 天亮
    # ------------------------------------------------------------------
    async def _dawn(self) -> None:
        self.state.phase = "dawn"
        result = self.night_result
        self.state.log("dawn", f"第 {self.state.day} 天，天亮了。")
        if result.deaths:
            for death in result.deaths:
                self.state.reveal_death(death["seat"])
        else:
            self.state.log("dawn", "昨晚是平安夜。")

        await self._resolve_revenge(result.deaths)
        self.state.check_winner()
        await self._begin_phase("dawn", self.t("dawn"))
        await self._wait_phase(self.t("dawn"))

    # ------------------------------------------------------------------
    # 80 秒密聊
    # ------------------------------------------------------------------
    async def _council(self) -> None:
        self.room.council_begin()
        self.state.phase = "council"
        self.state.log("council", "80 秒智囊团密聊开始。")
        await self._begin_phase("council", self.t("council"))
        if self.room.all_staffed_teams_locked():
            self.gate.set()
        await self._wait_phase(self.t("council"))

        self.room.council_finalize()
        self.state.log("council", "密聊结束，策略包已锁定。")
        self.round = {}

        for p in self.state.alive:
            if self._offline(p.seat):
                continue
            team = self.room.teams[p.seat]
            agg = team.final_aggregate
            if agg is None:
                auto_pkg = self.director.auto_strategy(self.state, p.seat)
                adoption = Adoption(
                    kind="auto",
                    effective=None,
                    summary="没有人类策略包，AI 按自己的判断行动。",
                    adherence=0.0,
                    tone="自主",
                )
                self.round[p.seat] = RoundDecision(p.seat, adoption, None, auto_pkg)
                team.public_adoption = adoption
            else:
                adoption = decide_adoption(
                    agg,
                    obedience=p.persona.obedience,
                    logic=p.persona.logic,
                    rng=self.rng,
                    has_key=self.director.has_key(p.seat),
                )
                self.round[p.seat] = RoundDecision(p.seat, adoption, agg, None)
                team.public_adoption = adoption
                p.trust = max(0.0, min(1.0, p.trust + (0.03 if adoption.kind == "full" else (-0.03 if adoption.kind == "defy" else 0.0))))

        record = {
            "day": self.state.day,
            "teams": [
                {
                    "seat": d.seat,
                    "kind": d.adoption.kind,
                    "label": d.adoption.label,
                    "auto": d.aggregate is None,
                    "submitted": len(self.room.teams[d.seat].packages),
                }
                for d in self.round.values()
            ],
        }
        self.state.council_rounds.append(record)
        await self.notifier.broadcast({"type": "council_end", "data": record})
        await self.notifier.snapshot()

    # ------------------------------------------------------------------
    # AI 依次发言
    # ------------------------------------------------------------------
    def _speech_duration(self, text: str) -> float:
        if self.room.timing == "fast":
            return max(4.0, min(self.t("speech"), len(text) / 16.0 + 2.0))
        return max(14.0, min(self.t("speech"), len(text) / 4.2 + 4.0))

    async def _speeches(self) -> None:
        speakers = list(self.state.alive)
        for p in speakers:
            if self.state.winner:
                return
            if self._offline(p.seat):
                self.state.log("speech", f"{p.seat} 号 AI 已离线，跳过发言与 API 调用。", seat=p.seat)
                await self.notifier.broadcast(
                    {"type": "speech_skipped", "data": {"seat": p.seat, "name": p.persona.name}}
                )
                continue
            await self._begin_phase("speech", self.t("speech"), speaker=p.seat)
            await self.notifier.broadcast(
                {"type": "ai_thinking", "data": {"seat": p.seat, "name": p.persona.name}}
            )

            decision = self.round.get(p.seat)
            if decision is None:
                decision = RoundDecision(
                    p.seat,
                    Adoption(kind="auto", effective=None, summary="自主决策", adherence=0.0),
                    None,
                    self.director.auto_strategy(self.state, p.seat),
                )
                self.round[p.seat] = decision
            recent = [s.text for s in self.state.speeches[-4:]]
            try:
                result: AIResult = await self.director.speak(
                    self.state,
                    p.seat,
                    decision.aggregate,
                    decision.adoption,
                    recent_speeches=recent,
                )
            except Exception as exc:  # noqa: BLE001
                result = self.director.demo_speak(self.state, p.seat, decision.aggregate, decision.adoption)
                result.error = str(exc)[:160]

            if not result.speech:
                result.speech = "这轮我先过，后面听发言再补。"
            feedback = decision.adoption.to_public()
            feedback.update(
                {
                    "detail": result.feedback_detail,
                    "source": result.source,
                    "error": result.error,
                }
            )
            if result.source == "llm":
                p.trust = max(0.0, min(1.0, p.trust + 0.01))

            self.state.speeches.append(
                SpeechRecord(
                    day=self.state.day,
                    seat=p.seat,
                    text=result.speech,
                    claim=result.claim,
                    feedback=feedback,
                    inner=result.inner,
                    vote_intent=result.vote_intent,
                    suspects=result.suspects,
                    trusts=result.trusts,
                )
            )
            self.state.mark_revealed(p.seat, result.claim)
            self.state.log("speech", f"{p.seat} 号 {p.persona.name} 完成发言。", seat=p.seat)
            duration = self._speech_duration(result.speech)
            self._reset_phase_timer(duration)
            await self.notifier.broadcast(
                {
                    "type": "speech",
                    "data": {
                        "day": self.state.day,
                        "seat": p.seat,
                        "name": p.persona.name,
                        "avatar": p.persona.avatar,
                        "text": result.speech,
                        "claim": result.claim,
                        "claimName": None,
                        "feedback": feedback,
                        "duration": duration,
                        "endsAt": self.state.phase_ends_at,
                        "source": result.source,
                    },
                }
            )
            await self.notifier.snapshot()
            await self._wait_remaining(duration)

        self.state.current_speaker = None
        self.state.phase_ends_at = None

    # ------------------------------------------------------------------
    # 白天技能
    # ------------------------------------------------------------------
    async def _special_actions(self) -> None:
        knight = next((p for p in self.state.players if p.alive and p.role == "knight" and not p.duel_used and not self._offline(p.seat)), None)
        white = next((p for p in self.state.players if p.alive and p.role == "white_wolf_king" and not p.exploded and not self._offline(p.seat)), None)
        if not knight and not white:
            return

        skill_pause = 1.0 if self.room.timing == "fast" else max(3.0, self.t("vote_reveal") * 0.6)
        await self._begin_phase("special", skill_pause)
        if knight:
            target = self._council_target(knight.seat) or self.director.knight_target(self.state, knight.seat)
            if target and self.state.by_seat(target) and self.state.by_seat(target).alive:
                result = self.state.knight_duel(knight.seat, target)
                if result.get("ok"):
                    await self.notifier.broadcast({"type": "skill", "data": {**result, "skill": "knight_duel"}})
                    deaths = []
                    if result.get("hit"):
                        deaths.append({"seat": target, "can_revenge": True})
                    else:
                        deaths.append({"seat": knight.seat, "can_revenge": True})
                    await self._resolve_revenge(deaths)
                    self.state.check_winner()
                    if self.state.winner:
                        return
        if white and white.alive:
            target = self._council_target(white.seat) or self.director.white_wolf_target(self.state, white.seat)
            if target and self.state.by_seat(target) and self.state.by_seat(target).alive:
                result = self.state.white_wolf_explode(white.seat, target)
                if result.get("ok"):
                    self.skip_vote = True
                    await self.notifier.broadcast({"type": "skill", "data": {**result, "skill": "white_wolf_explode"}})
                    await self._resolve_revenge([{"seat": target, "can_revenge": True}])
                    self.state.check_winner()
                    if self.state.winner:
                        return

        await self._wait_phase(skill_pause)

    def _council_target(self, seat: int) -> Optional[int]:
        decision = self.round.get(seat)
        if not decision or not decision.adoption.effective:
            return None
        pkg = decision.adoption.effective
        for target in (pkg.vote_seat, pkg.attack_seat):
            player = self.state.by_seat(target)
            if player and player.alive:
                return target
        return None

    # ------------------------------------------------------------------
    # 锁票建议
    # ------------------------------------------------------------------
    async def _vote_advice(self) -> None:
        await self._begin_phase("vote_advice", self.t("vote_advice"))
        if self.room.all_staffed_teams_advised():
            self.gate.set()
        await self._wait_phase(self.t("vote_advice"))

    # ------------------------------------------------------------------
    # 投票
    # ------------------------------------------------------------------
    async def _vote(self) -> None:
        await self._begin_phase("vote_reveal", self.t("vote_reveal"))
        self.state.wolf_plan = {
            "kill": self.state.wolf_plan.get("kill") if getattr(self.state, "wolf_plan", None) else None,
            "vote": self.director.wolf_vote_target(self.state) if self._online_wolves() else None,
        }
        votes: dict[int, Optional[int]] = {}
        for p in self.state.alive:
            if not p.can_vote or self._offline(p.seat):
                continue
            decision = self.round.get(p.seat) or RoundDecision(
                p.seat,
                Adoption(kind="auto", effective=None, summary="", adherence=0.0),
            )
            advice = self.room.advice_for(p.seat)
            target = self.director.vote(self.state, p.seat, decision.adoption, advice)
            if target is None:
                candidates = [q.seat for q in self.state.players if q.alive and q.seat != p.seat]
                target = random.choice(candidates) if candidates else None
            if target is not None and (target == p.seat or not self.state.by_seat(target) or not self.state.by_seat(target).alive):
                target = None
            votes[p.seat] = target

        counts: dict[int, int] = {}
        for target in votes.values():
            if target is not None:
                counts[target] = counts.get(target, 0) + 1
        exile = None
        tie = False
        if counts:
            best = max(counts.values())
            top = [seat for seat, c in counts.items() if c == best]
            if len(top) == 1:
                exile = top[0]
            else:
                tie = True

        record = VoteRecord(
            day=self.state.day,
            votes=votes,
            exile=exile,
            tie=tie,
        )
        self.state.votes.append(record)
        await self.notifier.broadcast(
            {
                "type": "vote_result",
                "data": {
                    "day": self.state.day,
                    "votes": [{"from": k, "to": v} for k, v in votes.items()],
                    "exile": exile,
                    "tie": tie,
                    "counts": counts,
                },
            }
        )

        last_words_seat = None
        if tie:
            self.state.log("vote", "投票平票，本轮无人出局。")
        elif exile:
            result = self.state.exile(exile)
            if result.kind == "exiled":
                last_words_seat = exile
                await self._resolve_revenge([{"seat": exile, "can_revenge": True}])
                self.state.check_winner()
            elif result.kind == "idiot":
                await self.notifier.broadcast(
                    {"type": "skill", "data": {"skill": "idiot_reveal", "seat": exile}}
                )
        else:
            self.state.log("vote", "本轮无人被放逐。")

        await self.notifier.snapshot()
        await self._wait_phase(self.t("vote_reveal"))
        if last_words_seat is not None:
            await self._last_words(last_words_seat)

    async def _last_words(self, seat: int) -> None:
        p = self.state.by_seat(seat)
        if not p:
            return
        await self._begin_phase("last_words", self.t("last_words"), speaker=seat)
        text = self.director.last_words(self.state, seat)
        self.state.last_words.append(
            {
                "day": self.state.day,
                "seat": seat,
                "name": p.persona.name,
                "text": text,
            }
        )
        self.state.log("last_words", f"{seat} 号 {p.persona.name} 留下遗言。")
        self._reset_phase_timer(min(self.t("last_words"), max(5.0, len(text) / 5.0 + 2)))
        await self.notifier.broadcast(
            {
                "type": "last_words",
                "data": {"seat": seat, "name": p.persona.name, "text": text, "endsAt": self.state.phase_ends_at},
            }
        )
        await self.notifier.snapshot()
        await self._wait_remaining(min(self.t("last_words"), max(5.0, len(text) / 5.0 + 2)))
        self.state.current_speaker = None
        self.state.phase_ends_at = None

    # ------------------------------------------------------------------
    # 出局技能链
    # ------------------------------------------------------------------
    async def _resolve_revenge(self, deaths: list[dict]) -> None:
        queue = list(deaths)
        guard = 0
        while queue and guard < 6:
            guard += 1
            death = queue.pop(0)
            if not death.get("can_revenge"):
                continue
            p = self.state.by_seat(death["seat"])
            if not p or self._offline(p.seat) or p.shot_used or p.role not in ("hunter", "wolf_king"):
                continue
            target = self._council_target(p.seat) or self.director.revenge_target(self.state, p.seat)
            if not target:
                continue
            t = self.state.by_seat(target)
            if not t or not t.alive:
                continue
            p.shot_used = True
            skill = "hunter_shot" if p.role == "hunter" else "wolf_king_shot"
            reason = "被猎人开枪带走" if p.role == "hunter" else "被狼王开枪带走"
            self.state.kill(target, reason, "day")
            self.state.log(
                "skill",
                f"{p.seat} 号{p.role_def.name}开枪，带走了 {target} 号 {t.persona.name}！",
                seat=p.seat,
                target=target,
                skill=skill,
            )
            await self.notifier.broadcast(
                {
                    "type": "skill",
                    "data": {
                        "skill": skill,
                        "seat": p.seat,
                        "role": p.role,
                        "target": target,
                        "targetName": t.persona.name,
                    },
                }
            )
            queue.append({"seat": target, "can_revenge": True})

    # ------------------------------------------------------------------
    # 结束
    # ------------------------------------------------------------------
    async def _finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        if not self.state.winner:
            self.state.winner = "good"
            self.state.win_reason = self.state.win_reason or "对局提前结束。"
        self.state.phase = "finished"
        self.state.phase_ends_at = None
        self.state.current_speaker = None
        self.state.finished_at = self.state.finished_at or now_ms()
        self.room.finish()
        self.room.close_all_voice("本局结束，语音已关闭。")
        self.state.log("system", f"对局结束：{self.state.win_reason}")
        await self.notifier.broadcast(
            {
                "type": "game_over",
                "data": {
                    "winner": self.state.winner,
                    "winReason": self.state.win_reason,
                },
            }
        )
        await self.notifier.snapshot()
