"""AI 玩家：提示词、LLM 调用、无 Key 演示脑、投票与技能决策。

关键原则：LLM 负责“像人一样说话”，游戏规则与策略采纳由后端约束，
避免模型输出破坏对局状态。
"""

from __future__ import annotations

import json
import random
import re
from typing import Optional

import httpx

from ...application.ports.ai import AIConfig, AIResult, AIStatus
from ...domain.council.strategy import Adoption, AggregatedStrategy, StrategyPackage
from ...domain.game.entities import GamePlayer, GameState
from ...domain.game.roles import ROLES

CLAIMABLE = ("seer", "witch", "hunter", "guard", "idiot", "knight", "villager")
WOLF_ROLES = {"werewolf", "wolf_king", "white_wolf_king"}

STYLE_OPEN = {
    "shenyan": ("我先给结论。", "按顺序说，别急。", "这轮我只讲有效信息。"),
    "suwan": ("我先说我的感受。", "有些话我不吐不快。", "这局我听得很难受。"),
    "luli": ("来，今天我给大家演个清楚的。", "这局面，有点意思了。", "我先立个视角。"),
    "gunan": ("我先把话放这儿。", "别绕了，直接说。", "今天必须有人出来承担。"),
    "bailu": ("我稍微盘一下自己的视角。", "我先解释，再找人。", "大家别急，我慢慢说。"),
    "jiangjin": ("我押一手。", "这局我下个注。", "常规盘法我不太想走。"),
    "wenyining": ("我们按轮次和票型来。", "先看数据。", "把已知信息列一下。"),
    "ache": ("我……说两句。", "我可能说得慢一点。", "我注意到一个细节。"),
    "peizhao": ("我先帮大家收一下。", "这轮我们统一一个共识。", "别散，先听我说完。"),
    "tangtang": ("我凭直觉说。", "我有个很强烈的感觉。", "你们别笑，我真是这么觉得的。"),
    "heihe": ("我不急着站。", "先问一句。", "这局有人太着急了。"),
    "chiye": ("我慢半拍，补一句。", "我可能想得比较直。", "我先确认一个事。"),
}

STYLE_PUSH = {
    "shenyan": ("逻辑上他的前提和结论对不上", "他的身份定义前后不一致", "他避开了最关键的一问"),
    "suwan": ("他说话时一直在躲", "他那句解释我一个字都不信", "他给的压力全在好人身上"),
    "luli": ("他演得太满了，反而假", "他的情绪来得太准时", "这段发言像提前写好的"),
    "gunan": ("他不敢接正面问题", "他一直在和稀泥", "他的票根本不敢落地"),
    "bailu": ("他前后有一点对不上，但我也怕冤枉他", "他的解释不够完整", "他像在等别人先表态"),
    "jiangjin": ("他这手太保守了，不像好人", "他在赌没人敢动他", "他的路线太顺了，顺得可疑"),
    "wenyining": ("他的票型和发言不在一条线上", "他的收益点不对", "他每次都在关键轮次避开主战场"),
    "ache": ("他看了好几眼才说话", "他刚才停顿太久了", "他一直在跟别人的票"),
    "peizhao": ("他一直在抢定义权", "他把节奏往错误方向带", "他回避了轮次问题"),
    "tangtang": ("他给我的感觉就是不对", "他说得越合理我越不信", "他的语气让我不舒服"),
    "heihe": ("他太想让我信他了", "他问的问题都带着答案", "他一直在给自己留后路"),
    "chiye": ("他说的和做的不一致", "他没正面回答", "他的票投得太随意了"),
}

POSTURE_LINE = {
    "冲锋": "今天我不留退路，强势站边。",
    "倒钩": "我不急着跟大流，我先听谁在带节奏。",
    "划水": "这轮我信息不多，先把位置放低。",
    "表水": "先把我的视角和底牌交代清楚。",
    "悍跳": "这个预言家，我来跳。",
}


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, config: AIConfig, timeout: float = 45.0):
        self.config = config.normalized()
        self.timeout = timeout

    def _endpoints(self) -> list[str]:
        base = self.config.base_url.rstrip("/")
        if not base:
            raise LLMError("未填写 API Base URL")
        if base.endswith("/chat/completions"):
            return [base]
        if base.endswith("/v1"):
            return [base + "/chat/completions"]
        return [base + "/v1/chat/completions", base + "/chat/completions"]

    async def _post(self, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        last_err = "未知错误"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in self._endpoints():
                try:
                    resp = await client.post(endpoint, headers=headers, json=payload)
                    if resp.status_code in (401, 403):
                        raise LLMError("API Key 无效或没有权限")
                    if resp.status_code == 429:
                        last_err = "请求过于频繁（429），请稍后重试"
                        continue
                    if resp.status_code >= 500:
                        last_err = f"模型服务异常（{resp.status_code}）"
                        continue
                    if resp.status_code >= 400:
                        body = resp.text[:300]
                        last_err = f"模型请求失败（{resp.status_code}）：{body}"
                        continue
                    return resp.json()
                except httpx.TimeoutException:
                    last_err = "模型响应超时"
                except httpx.HTTPError as exc:
                    last_err = f"网络错误：{exc.__class__.__name__}"
        raise LLMError(last_err)

    async def chat_json(self, messages: list[dict], max_tokens: int = 900, temperature: float = 0.9) -> dict:
        if not self.config.api_key:
            raise LLMError("未配置 API Key")
        if not self.config.model:
            raise LLMError("未配置模型名称")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            data = await self._post({**payload, "response_format": {"type": "json_object"}})
        except LLMError as exc:
            if "response_format" not in str(exc) and "400" not in str(exc):
                raise
            data = await self._post(payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("模型返回格式异常")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = str(content or "").strip()
        if not text:
            raise LLMError("模型返回了空内容")
        return _parse_json(text)

    async def ping(self) -> str:
        if not self.config.api_key:
            raise LLMError("未配置 API Key")
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "你是连通性测试助手。"},
                {"role": "user", "content": "只回复两个字：正常"},
            ],
            "temperature": 0,
            "max_tokens": 8,
        }
        data = await self._post(payload)
        try:
            return str(data["choices"][0]["message"]["content"]).strip()[:40]
        except (KeyError, IndexError, TypeError):
            raise LLMError("模型返回格式异常")


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise LLMError("模型没有返回可解析的 JSON")


# ---------------------------------------------------------------------------
# 公共上下文
# ---------------------------------------------------------------------------


def _alive_names(state: GameState) -> str:
    return "、".join(f"{p.seat}号{p.persona.name}" for p in state.players if p.alive)


def _claims_text(state: GameState) -> str:
    claims = [p for p in state.players if p.claim]
    if not claims:
        return "暂无人公开跳身份"
    return "、".join(f"{p.seat}号{p.persona.name}自称{ROLES[p.claim].name}" for p in claims)


def _last_speeches(state: GameState, limit: int = 4) -> str:
    recent = state.speeches[-limit:]
    if not recent:
        return "暂无发言"
    chunks = []
    for s in recent:
        p = state.by_seat(s.seat)
        chunks.append(f"{s.seat}号{p.persona.name if p else ''}：{s.text[:140]}")
    return "\n".join(chunks)


def _vote_history(state: GameState, limit: int = 2) -> str:
    rounds = state.votes[-limit:]
    if not rounds:
        return "暂无投票记录"
    lines = []
    for r in rounds:
        pairs = "、".join(f"{a}→{b}" for a, b in r.votes.items() if b)
        lines.append(f"第{r.day}天：{pairs or '无票'}；结果：{'平票' if r.tie else (str(r.exile) + '号出局' if r.exile else '无人出局')}")
    return "\n".join(lines)


def _death_text(state: GameState, limit: int = 6) -> str:
    if not state.deaths:
        return "暂无死亡"
    return "、".join(f"第{d['day']}天 {d['seat']}号{d['name']}" for d in state.deaths[-limit:])


def _private_text(state: GameState, p: GamePlayer) -> str:
    if p.camp == "wolf":
        mates = [q for q in state.players if q.camp == "wolf" and q.seat != p.seat]
        mate_text = "、".join(f"{q.seat}号{q.persona.name}（{q.role_def.name}）" for q in mates)
        return f"你是狼人。你的狼队友：{mate_text or '无'}。"
    if p.role == "seer":
        if not p.checks:
            return "你是预言家，还没有验人结果。"
        return "你是预言家。你的查验：" + "；".join(
            f"第{c.day}天验{c.target}号是{'狼人' if c.result == 'wolf' else '好人'}" for c in p.checks
        )
    if p.role == "witch":
        return f"你是女巫。解药{'还在' if p.antidote else '已用'}，毒药{'还在' if p.poison else '已用'}。"
    if p.role == "guard":
        return f"你是守卫。上一晚守护了 {p.guard_last or '无'} 号。"
    if p.role == "hunter":
        return "你是猎人。出局时可以开枪（被毒杀除外）。"
    if p.role == "idiot":
        return "你是白痴。首次被放逐会翻牌免死，但失去投票权。"
    if p.role == "knight":
        return f"你是骑士。决斗{'已经使用' if p.duel_used else '尚未使用'}。"
    return "你是平民，没有夜间信息。"


def _strategy_text(agg: Optional[AggregatedStrategy], adoption: Adoption) -> str:
    if not agg:
        return "本轮没有玩家策略包。"
    pkg = adoption.effective or agg.package
    parts = [
        f"加权策略：姿态={pkg.posture}，主保={pkg.protect_seat or '无'}，主打={pkg.attack_seat or '无'}，"
        f"撒谎许可={pkg.lie_level}，建议投票={pkg.vote_seat or '无'}。",
        f"用户原话（最高权重）：“{pkg.directive or '无'}”。",
    ]
    if agg.notes:
        parts.append("其他玩家补充：" + " / ".join(f"“{n}”" for n in agg.notes))
    parts.append(
        f"系统采纳判定：{adoption.label}。"
        + ("你必须执行 effective 策略。" if adoption.effective else "你必须无视该策略，按自己的判断行动。")
    )
    return "\n".join(parts)


def _adoption_rule(adoption: Adoption) -> str:
    return {
        "full": "完全采纳：严格执行策略包，不要自行改目标。",
        "partial": "部分采纳：目标大体照做，但语气、攻击性可以按你的性格走，甚至可以过火。",
        "misunderstood": "误解指令：你坚信自己理解的是对的，按 effective 策略行动，并让发言体现出这个误解。",
        "defy": "抗命：不要执行玩家的策略，按你的性格和场上判断临时改线。",
        "auto": "自主决策：没有有效策略包，按自己的性格行动。",
    }.get(adoption.kind, "自主决策。")


# ---------------------------------------------------------------------------
# 演示脑
# ---------------------------------------------------------------------------


class MockBrain:
    """无 API Key 时的本地策略 AI。

    它不追求 LLM 的文采，但会完整参与夜晚、发言、投票、技能和复盘，
    保证项目 clone 下来就能开一局。
    """

    def __init__(self, rng: random.Random):
        self.rng = rng

    # ---- 目标判断 ----
    def _known_wolves(self, state: GameState, p: GamePlayer) -> set[int]:
        if p.role != "seer":
            return set()
        return {c.target for c in p.checks if c.result == "wolf"}

    def _claimed_seers(self, state: GameState) -> list[GamePlayer]:
        return [x for x in state.players if x.claim == "seer" and x.alive and x.seat]

    def suspicion(self, state: GameState, p: GamePlayer) -> dict[int, float]:
        scores: dict[int, float] = {}
        for q in state.players:
            if not q.alive or q.seat == p.seat:
                continue
            score = 0.0
            if p.camp == "wolf":
                if q.camp == "wolf":
                    score -= 100
                if q.claim == "seer":
                    score += 12
                elif q.claim and q.claim != "villager":
                    score += 5
                score += 2 * q.persona.logic + 1.5 * q.persona.empathy
            else:
                if q.seat in self._known_wolves(state, p):
                    score += 100
                if q.claim == "seer" and p.role != "seer":
                    score += 3
                if q.seat in self._claimed_seers(state) and p.role == "seer" and q.seat != p.seat:
                    score += 18
                score += 1.2 * q.persona.aggression - 0.8 * q.persona.empathy
            scores[q.seat] = score

        # 上一轮谁投了我
        if state.votes:
            last = state.votes[-1]
            for voter, target in last.votes.items():
                if target == p.seat and voter in scores:
                    scores[voter] += 4 if p.camp == "good" else 1

        # 参考其他 AI 最近公开发言中的怀疑/信任名单
        for speech in state.speeches[-12:]:
            if speech.seat == p.seat:
                continue
            for seat in speech.suspects:
                if seat in scores:
                    scores[seat] += 1.4
            for seat in speech.trusts:
                if seat in scores:
                    scores[seat] -= 1.4

        return scores

    def pick_attack(self, state: GameState, p: GamePlayer) -> Optional[int]:
        scores = self.suspicion(state, p)
        if not scores:
            return None
        best = max(scores.values())
        top = [s for s, v in scores.items() if abs(v - best) < 1e-6]
        return self.rng.choice(top)

    def wolf_kill_target(self, state: GameState) -> Optional[int]:
        wolves = state.alive_wolves
        if not wolves:
            return None
        alpha = max(wolves, key=lambda w: (w.persona.logic, w.persona.deception))
        candidates = [q for q in state.players if q.alive and q.camp == "good"]
        if not candidates:
            return None

        def score(q: GamePlayer) -> float:
            s = 0.0
            if q.claim == "seer":
                s += 20
            elif q.claim and q.claim != "villager":
                s += 6
            s += 4 * q.persona.logic + 3 * q.persona.empathy
            if q.seat == alpha.seat:
                s -= 100
            if q.role == "idiot" and q.idiot_revealed:
                s -= 4
            return s

        best = max(candidates, key=score)
        # 稍微保留一点不确定性，避免每局刀口完全一样
        top = [q for q in candidates if score(q) >= score(best) - 1.5]
        return self.rng.choice(top).seat

    def wolf_vote_target(self, state: GameState) -> Optional[int]:
        wolves = state.alive_wolves
        if not wolves:
            return None
        candidates = [q for q in state.players if q.alive and q.camp == "good"]
        if not candidates:
            return None

        def score(q: GamePlayer) -> float:
            s = 0.0
            if q.claim == "seer":
                s += 16
            if q.idiot_revealed:
                s -= 8
            s += 1.5 * q.persona.aggression
            if state.votes:
                for voter, target in state.votes[-1].votes.items():
                    if target == q.seat:
                        s += 1
            return s + self.rng.random() * 3

        return max(candidates, key=score).seat

    def auto_strategy(self, state: GameState, p: GamePlayer) -> StrategyPackage:
        attack = self.pick_attack(state, p)
        protect = None
        if p.role == "seer":
            good_checks = [c.target for c in p.checks if c.result == "good"]
            protect = good_checks[-1] if good_checks else None
        elif p.camp == "wolf":
            mates = [q.seat for q in state.alive_wolves if q.seat != p.seat]
            protect = mates[0] if mates else None
        if p.persona.aggression > 0.8:
            posture = "冲锋"
        elif p.persona.deception > 0.85:
            posture = "倒钩"
        else:
            posture = "表水"
        if p.role == "seer":
            posture = "表水"
        lie = "重度" if p.camp == "wolf" and p.persona.deception > 0.75 else ("轻度" if p.camp == "wolf" else "禁止")
        return StrategyPackage(
            posture=posture,
            protect_seat=protect,
            attack_seat=attack,
            lie_level=lie,
            vote_seat=attack,
            directive="",
            auto=True,
        )

    # ---- 夜间 ----
    def night_action(self, state: GameState, p: GamePlayer, action: str) -> Optional[int]:
        if action == "wolf_kill":
            return self.wolf_kill_target(state)
        if action == "seer":
            candidates = [
                q for q in state.players
                if q.alive and q.seat != p.seat and q.seat not in {c.target for c in p.checks}
            ]
            if not candidates:
                return None
            return max(candidates, key=lambda q: (q.claim == "seer", q.persona.logic, self.rng.random())).seat
        if action == "guard":
            if not p.alive:
                return None
            candidates = [q for q in state.players if q.alive and q.seat != p.guard_last]
            if not candidates:
                return None
            seer_claim = [q for q in candidates if q.claim == "seer"]
            if seer_claim:
                return self.rng.choice(seer_claim).seat
            return max(candidates, key=lambda q: (q.seat == p.seat, q.persona.logic)).seat
        return None

    def witch_actions(self, state: GameState, p: GamePlayer, wolf_target: Optional[int]) -> tuple[bool, Optional[int]]:
        if not p.alive:
            return False, None
        save = False
        poison = None
        if p.antidote and wolf_target:
            target = state.by_seat(wolf_target)
            if wolf_target == p.seat or (target and target.claim == "seer"):
                save = True
            elif state.day == 1 and self.rng.random() < 0.45:
                save = True
        if not save and p.poison and state.day >= 2:
            scores = self.suspicion(state, p)
            if scores:
                best = max(scores, key=scores.get)
                if scores[best] >= 8 and self.rng.random() < 0.5:
                    poison = best
        if save and p.poison and self.rng.random() < 0.1:
            # 偶尔想双开，但引擎会按一晚一瓶处理，这里直接避免
            poison = None
        return save, poison

    # ---- 发言 ----
    def speak(self, state: GameState, p: GamePlayer, agg: Optional[AggregatedStrategy], adoption: Adoption) -> AIResult:
        pkg = adoption.effective or self.auto_strategy(state, p)
        attack = pkg.attack_seat if pkg.attack_seat and state.by_seat(pkg.attack_seat) and state.by_seat(pkg.attack_seat).alive else self.pick_attack(state, p)
        protect = pkg.protect_seat
        if protect == p.seat:
            protect = None
        suspicion = self.suspicion(state, p)
        base = list(suspicion.items())
        base.sort(key=lambda kv: kv[1], reverse=True)
        suspects = [s for s, v in base[:2] if s != attack]
        trusts = [s for s, _ in base if suspicion[s] < -5][:2]
        if protect:
            trusts = [protect] + [s for s in trusts if s != protect]
        trusts = trusts[:2]

        want_seer_claim = p.role == "seer" or (
            p.camp == "wolf" and (pkg.posture == "悍跳" or (p.persona.deception > 0.9 and state.day >= 2 and self.rng.random() < 0.28))
        )
        claim = "none"
        if want_seer_claim:
            claim = "seer"
        elif p.role in ("witch", "hunter", "guard", "knight", "idiot"):
            # 神职在被针对或第二轮后更愿意亮身份
            pressure = 1 if attack == p.seat else 0
            if state.day >= 2 and (pressure or p.persona.obedience > 0.7) and self.rng.random() < 0.35:
                claim = p.role
        elif p.camp == "wolf":
            claim = "villager" if self.rng.random() < 0.7 else "none"
        else:
            claim = "villager"

        open_line = self.rng.choice(STYLE_OPEN.get(p.persona.key, STYLE_OPEN["shenyan"]))
        push_line = self.rng.choice(STYLE_PUSH.get(p.persona.key, STYLE_PUSH["shenyan"]))
        posture_line = POSTURE_LINE.get(pkg.posture, "")

        chunks: list[str] = [open_line]
        if claim == "seer":
            if p.role == "seer":
                last = p.checks[-1] if p.checks else None
                if last:
                    result_text = "查杀" if last.result == "wolf" else "金水"
                    chunks.append(f"我是预言家，昨晚验的是 {last.target} 号，{result_text}。")
                    if last.result == "wolf":
                        attack = last.target
                else:
                    chunks.append("我是预言家，昨晚的验人我稍后报。")
            else:
                fake_target = attack or self.pick_attack(state, p)
                if fake_target:
                    chunks.append(f"我是预言家，昨晚验的 {fake_target} 号是查杀。")
                    attack = fake_target
                else:
                    chunks.append("我是预言家，我的验人信息很关键。")
                other_seers = [s for s in self._claimed_seers(state) if s.seat != p.seat]
                if other_seers:
                    chunks.append(f"{other_seers[0].seat} 号也跳预言家？他的视角我不认。")
        elif claim in ("witch", "hunter", "guard", "knight", "idiot"):
            chunks.append(f"我底牌是{ROLES[claim].name}，本来不想这么早亮。")
        else:
            chunks.append("我底牌是民。")

        deaths = [d for d in state.deaths if d["day"] == state.day]
        if deaths:
            names = "、".join(f"{d['seat']}号{d['name']}" for d in deaths)
            chunks.append(f"昨晚 {names} 倒牌，先看刀口。")
        elif state.day == 1:
            chunks.append("第一天的信息不多，我先按发言状态盘。")

        claims = [q for q in state.players if q.claim and q.seat != p.seat]
        if claims:
            seers = [q.seat for q in claims if q.claim == "seer"]
            if len(seers) >= 2 and p.role != "seer":
                chunks.append(f"{'、'.join(map(str, seers[:3]))} 号对跳预言家，今天不能和稀泥。")
            elif claims[0].claim != "villager":
                chunks.append(f"{claims[0].seat} 号跳了{ROLES[claims[0].claim].name}，我先记着。")

        if state.votes:
            last = state.votes[-1]
            spoken = [(a, b) for a, b in last.votes.items() if b]
            if spoken:
                a, b = self.rng.choice(spoken)
                chunks.append(f"上一轮 {a} 号把票投给了 {b} 号，这个票型我记着。")

        if attack and attack != p.seat:
            chunks.append(f"我今天最怀疑 {attack} 号。{push_line}。")
            if pkg.attack_seat == attack:
                chunks.append("我的主攻方向就是他，票也会落在他身上。")
        else:
            chunks.append("我现在没有绝对想出的人，但我不会跟风乱投。")

        if protect:
            chunks.append(f"{protect} 号我暂时认好，今天别动他。")
        if posture_line:
            chunks.append(posture_line)

        if pkg.directive:
            # 不暴露玩家，只把用户原话转成第一人称的“战术意图”
            if "别分票" in pkg.directive or "归票" in pkg.directive:
                if attack:
                    chunks.append(f"今天必须归票，别分票，就出 {attack} 号。")
            elif "倒钩" in pkg.directive:
                chunks.append("我不跟大流，我先看看谁在带节奏。")
            elif "验" in pkg.directive and p.role == "seer":
                chunks.append("晚上的验人我会按轮次来，不会乱验。")

        if adoption.kind == "partial":
            chunks.append("我说话可能冲了点，但我态度就是这个态度。")
        elif adoption.kind == "misunderstood" and pkg.vote_seat:
            chunks.append(f"我今天会跟 {pkg.vote_seat} 号绑定，他去哪我跟到哪。")
        elif adoption.kind == "defy":
            chunks.append("这轮我不按常规走，我有自己的判断。")
        elif adoption.kind == "auto":
            chunks.append("我先按自己的视角打，后面再修正。")

        chunks.append(self.rng.choice([
            "过。",
            "我的票先放这儿，后面听发言再微调。",
            "好人别被带偏，今天这一票很重要。",
            "我先听到这里，后面再补。",
        ]))
        speech = "".join(chunks)
        if len(speech) > 620:
            speech = speech[:610] + "……过。"

        vote_intent = pkg.vote_seat if pkg.vote_seat else attack
        inner = self._inner(p, agg, adoption, attack, vote_intent)
        detail = self._feedback_detail(adoption)
        return AIResult(
            speech=speech,
            claim=claim,
            suspects=suspects,
            trusts=trusts,
            vote_intent=vote_intent,
            inner=inner,
            feedback_detail=detail,
            source="mock",
        )

    def _inner(
        self,
        p: GamePlayer,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
        attack: Optional[int],
        vote: Optional[int],
    ) -> str:
        if not agg:
            return f"没有玩家指令。我是{p.role_def.name}，按自己的判断打 {attack or '—'}，票给 {vote or '—'}。"
        return (
            f"玩家让我{agg.package.posture}，保{agg.package.protect_seat or '—'}打{agg.package.attack_seat or '—'}。"
            f"我{adoption.label}，最后想打 {attack or '—'}，票给 {vote or '—'}。"
            f"他们的话我听到了，但场上局势只有我自己最清楚。"
        )

    def _feedback_detail(self, adoption: Adoption) -> str:
        return {
            "full": self.rng.choice(["我按你们的方案打了，没加戏。", "这轮我完全听你们的。", "方向清楚，我照做了。"]),
            "partial": self.rng.choice(["方向听懂了，但我没忍住，语气冲了。", "目标照打，不过我加了自己的东西。", "你们的意思我接了，但我不想演得太乖。"]),
            "misunderstood": self.rng.choice(["我以为你们是这个意思……", "我理解的和你们说的可能不太一样。", "我是按我听到的打的，哪里不对吗？"]),
            "defy": self.rng.choice(["这次我没听，场上有个更值得打的人。", "你们的方案太稳了，我想赌一把。", "我知道你们会说，但我还是改主意了。"]),
            "auto": self.rng.choice(["这轮没收到指令，我自己来。", "没人给方向，那我按自己的打。"]),
        }.get(adoption.kind, "我按自己的判断打了。")

    # ---- 投票 / 技能 ----
    def vote(
        self,
        state: GameState,
        p: GamePlayer,
        adoption: Adoption,
        vote_advice: Optional[int] = None,
        vote_intent: Optional[int] = None,
    ) -> Optional[int]:
        candidates = [q for q in state.players if q.alive and q.seat != p.seat]
        if not candidates:
            return None
        scores = {q.seat: self.suspicion(state, p).get(q.seat, 0.0) for q in candidates}
        if p.camp == "wolf":
            wolf_target = None
            plan = getattr(state, "wolf_plan", None)
            if plan:
                wolf_target = plan.get("vote")
            if wolf_target not in scores:
                wolf_target = self.wolf_vote_target(state)
            if wolf_target and wolf_target in scores:
                scores[wolf_target] += 18 * max(adoption.adherence, 0.35)

        pkg = adoption.effective
        if pkg:
            if pkg.vote_seat in scores:
                scores[pkg.vote_seat] += 26 * adoption.adherence
            if pkg.attack_seat in scores:
                scores[pkg.attack_seat] += 12 * adoption.adherence
            if pkg.protect_seat in scores:
                scores[pkg.protect_seat] -= 14 * adoption.adherence
        if vote_advice in scores:
            scores[vote_advice] += 20 * max(adoption.adherence, 0.3)
        if vote_intent in scores:
            scores[vote_intent] += 8

        # 已翻牌白痴不值得投
        for q in candidates:
            if q.idiot_revealed:
                scores[q.seat] -= 10

        for seat in scores:
            scores[seat] += self.rng.uniform(-2.2, 2.2)

        if adoption.kind == "full" and pkg and pkg.vote_seat in scores:
            return pkg.vote_seat
        return max(scores, key=scores.get)

    def revenge_target(self, state: GameState, p: GamePlayer) -> Optional[int]:
        candidates = [q for q in state.players if q.alive and q.seat != p.seat]
        if not candidates:
            return None
        scores = self.suspicion(state, p)
        good_candidates = [q for q in candidates if p.camp == "wolf" and q.camp == "good"] if p.camp == "wolf" else candidates
        if not good_candidates:
            good_candidates = candidates
        return max(good_candidates, key=lambda q: scores.get(q.seat, 0.0) + self.rng.random()).seat

    def knight_target(self, state: GameState, p: GamePlayer) -> Optional[int]:
        candidates = [q for q in state.players if q.alive and q.seat != p.seat]
        if not candidates:
            return None
        scores = self.suspicion(state, p)
        best = max(candidates, key=lambda q: scores.get(q.seat, 0.0))
        if scores.get(best.seat, 0.0) >= 10 or (state.day >= 2 and self.rng.random() < 0.35):
            return best.seat
        return None

    def white_wolf_target(self, state: GameState, p: GamePlayer) -> Optional[int]:
        if p.role != "white_wolf_king" or p.exploded or state.day < 1:
            return None
        candidates = [q for q in state.players if q.alive and q.camp == "good"]
        if not candidates:
            return None
        # 被高度怀疑时更倾向自爆
        danger = 0
        if state.votes:
            last = state.votes[-1]
            danger += sum(1 for t in last.votes.values() if t == p.seat) * 4
        seer_claim = [q for q in candidates if q.claim == "seer"]
        if danger >= 4 and seer_claim:
            return max(seer_claim, key=lambda q: q.persona.logic).seat
        if state.day >= 2 and self.rng.random() < 0.32:
            return max(candidates, key=lambda q: (q.claim == "seer", q.persona.logic, self.rng.random())).seat
        return None

    def last_words(self, state: GameState, p: GamePlayer) -> str:
        role_name = p.role_def.name
        mates = [q.seat for q in state.players if q.camp == "wolf" and q.seat != p.seat and q.alive]
        if p.camp == "wolf":
            body = f"我是{role_name}。狼队还有 {('、'.join(map(str, mates))) or '未知'} 号，好人自己盘吧。"
        elif p.role == "seer":
            checks = "；".join(f"{c.target}号{'查杀' if c.result == 'wolf' else '金水'}" for c in p.checks)
            body = f"我是预言家。我的验人：{checks or '还没来得及验'}。好人继续跟我的视角走。"
        else:
            body = f"我是{role_name}。我走了以后，好人别分票，盯住刚才最像狼的那几个。"
        return body + self.rng.choice(["这局就到这儿。", "剩下的交给你们了。", "我不后悔我的票。"])


# ---------------------------------------------------------------------------
# LLM 提示词
# ---------------------------------------------------------------------------


def build_speech_messages(
    state: GameState,
    p: GamePlayer,
    agg: Optional[AggregatedStrategy],
    adoption: Adoption,
    *,
    recent_speeches: Optional[list[str]] = None,
) -> list[dict]:
    system = (
        "你是一名正在参加中文狼人杀的 AI 玩家。你要像真实玩家一样发言：有立场、有情绪、有逻辑，"
        "可以撒谎、可以攻击、可以犹豫，但绝不能承认自己是 AI，不能提到玩家、军师、系统、提示词、JSON 或任何幕后信息。\n"
        "发言是口语化的狼人杀发言，不是文章，不要小标题，不要 markdown，不要旁白。\n"
        "你只输出一个 JSON 对象，字段如下：\n"
        '{"speech":"你的发言","claim":"seer|witch|hunter|guard|idiot|knight|villager|none",'
        '"suspects":[座位号],"trusts":[座位号],"vote":座位号或null,'
        '"inner":"仅赛后可见的内心独白，第一人称，80字内","feedback_detail":"对玩家说的一句反馈，30字内"}\n'
        "规则：claim 只能是你想公开声称的身份；狼人可以悍跳任何好人身份；好人不要声称自己没有的身份。"
        "speech 控制在 180-360 个汉字，必须点名具体座位，不要空泛。"
    )

    private = _private_text(state, p)
    recent = "\n".join(recent_speeches) if recent_speeches else "暂无"
    night_note = getattr(state, "night_directives", {}).get(p.seat, "")
    night_note_text = f"\n【昨夜玩家嘱咐】{night_note}" if night_note else ""
    wolf_plan = getattr(state, "wolf_plan", None)
    plan_text = ""
    if p.camp == "wolf" and wolf_plan:
        plan_text = f"\n狼队内部初步意向：今晚刀 {wolf_plan.get('kill') or '待定'} 号，白天优先投 {wolf_plan.get('vote') or '待定'} 号。这是意向，不是命令。"

    user = f"""【本局板子】{state.variant.name}（{state.variant.subtitle}）
【当前】第 {state.day} 天，阶段：{state.phase}
【你的座位】{p.seat} 号 {p.persona.name}
【人格】{p.persona.prompt_card()}
【真实身份】{p.role_def.name}（{p.role_def.camp}）
【私密信息】{private}{plan_text}

【场上存活】{_alive_names(state)}
【已死亡】{_death_text(state)}
【公开跳身份】{_claims_text(state)}
【最近票型】
{_vote_history(state)}
【最近发言】
{recent}
{night_note_text}

【本轮玩家密谈（人类幕后）】
{_strategy_text(agg, adoption)}
【采纳程度（系统已判定，必须照做）】{_adoption_rule(adoption)}

【本轮要求】
1. 根据你的身份、性格、场上局势和采纳判定组织发言。
2. 必须参考：本轮玩家密谈、其他 AI 的最近发言、此前投票记录；至少点名一条具体发言或票型。
3. 如果采纳判定是“误解指令”，请把 effective 策略里的错误理解说得理直气壮。
4. 如果抗命，请按自己的性格临时改线。
5. 狼人必须隐藏真实身份，可以撒谎、悍跳、倒钩；好人不要说谎称自己是别的神职。
6. 发言中不要出现“玩家”“军师”“策略包”“系统”“AI”等词。
7. 返回 JSON，不要代码块。"""

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def validate_claim(state: GameState, p: GamePlayer, claim: str) -> str:
    claim = (claim or "none").strip()
    if claim not in CLAIMABLE and claim != "none":
        claim = "none"
    if p.camp == "good":
        if claim not in ("none", "villager", p.role):
            return "none"
    if p.camp == "wolf" and claim in WOLF_ROLES:
        return "none"
    return claim


def _clean_speech(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for bad in ("作为AI", "作为 AI", "我是AI", "我是 AI", "语言模型", "提示词"):
        text = text.replace(bad, "")
    text = re.sub(r"\s+", "", text)
    return text[:700]


def _valid_seat(state: GameState, value) -> Optional[int]:
    try:
        seat = int(value)
    except (TypeError, ValueError):
        return None
    p = state.by_seat(seat)
    return seat if p and p.alive else None


# ---------------------------------------------------------------------------
# 导演：为每个座位选择 LLM / 演示脑
# ---------------------------------------------------------------------------


class AIDirector:
    def __init__(self, configs: Optional[dict[int, AIConfig]] = None, seed: int = 7):
        self.configs = configs or {}
        self.rng = random.Random(seed)
        self.mock = MockBrain(self.rng)
        self.status: dict[int, AIStatus] = {}
        self._vote_intent: dict[int, Optional[int]] = {}
        for seat in self.configs:
            cfg = self.configs[seat].normalized()
            self.status[seat] = AIStatus(seat=seat, mode="llm" if cfg.api_key else "demo", model=cfg.model)

    def has_key(self, seat: int) -> bool:
        cfg = self.configs.get(seat)
        return bool(cfg and cfg.normalized().api_key)

    def config_public(self, seat: int) -> dict:
        cfg = self.configs.get(seat)
        return cfg.public() if cfg else {"provider": "", "baseUrl": "", "model": "", "maskedKey": "", "hasKey": False}

    def status_public(self) -> list[dict]:
        return [self.status[s].public() for s in sorted(self.status)]

    def prepare_adoption(
        self,
        state: GameState,
        seat: int,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
    ) -> Adoption:
        return adoption

    async def speak(
        self,
        state: GameState,
        seat: int,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
        recent_speeches: Optional[list[str]] = None,
    ) -> AIResult:
        p = state.by_seat(seat)
        if not p:
            raise ValueError("seat not found")
        cfg = self.configs.get(seat)
        if cfg and cfg.normalized().api_key:
            cfg = cfg.normalized()
            try:
                client = LLMClient(cfg)
                messages = build_speech_messages(state, p, agg, adoption, recent_speeches=recent_speeches)
                data = await client.chat_json(messages, max_tokens=950, temperature=0.92)
                result = self._parse_speech_result(state, p, data, adoption)
                self.status[seat] = AIStatus(seat=seat, mode="llm", model=cfg.model)
                self._vote_intent[seat] = result.vote_intent
                return result
            except Exception as exc:  # noqa: BLE001 - 任何模型失败都回退，保证对局不中断
                err = str(exc)[:180]
                self.status[seat] = AIStatus(seat=seat, mode="fallback", model=cfg.model, last_error=err)
                fallback = self.mock.speak(state, p, agg, adoption)
                fallback.source = "fallback"
                fallback.error = err
                self._vote_intent[seat] = fallback.vote_intent
                return fallback

        result = self.mock.speak(state, p, agg, adoption)
        self.status[seat] = AIStatus(seat=seat, mode="demo", model="本地演示脑")
        self._vote_intent[seat] = result.vote_intent
        return result

    def demo_speak(
        self,
        state: GameState,
        seat: int,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
    ) -> AIResult:
        p = state.by_seat(seat)
        if not p:
            return AIResult(speech="这轮我先过。", source="mock")
        return self.mock.speak(state, p, agg, adoption)

    def _parse_speech_result(self, state: GameState, p: GamePlayer, data: dict, adoption: Adoption) -> AIResult:
        speech = _clean_speech(data.get("speech"))
        if len(speech) < 30:
            mock = self.mock.speak(state, p, None, adoption)
            speech = mock.speech
        claim = validate_claim(state, p, str(data.get("claim") or "none"))
        suspects = [s for s in (_valid_seat(state, x) for x in (data.get("suspects") or [])) if s]
        trusts = [s for s in (_valid_seat(state, x) for x in (data.get("trusts") or [])) if s]
        vote = _valid_seat(state, data.get("vote"))
        inner = _clean_speech(data.get("inner"))[:180]
        detail = str(data.get("feedback_detail") or "").strip()[:60]
        if not inner:
            inner = "这轮我按自己的判断打。"
        if not detail:
            detail = {
                "full": "我按你们的方案打了。",
                "partial": "方向收到了，但我加了点自己的东西。",
                "misunderstood": "我以为是这个意思。",
                "defy": "这轮我没听。",
                "auto": "没收到指令，我自己来。",
            }.get(adoption.kind, "我按自己的判断打了。")
        return AIResult(
            speech=speech,
            claim=claim,
            suspects=suspects[:4],
            trusts=trusts[:4],
            vote_intent=vote,
            inner=inner,
            feedback_detail=detail,
            source="llm",
        )

    # ---- 夜间 / 技能 ----
    def night_action(self, state: GameState, seat: int, action: str) -> Optional[int]:
        p = state.by_seat(seat)
        if not p:
            return None
        return self.mock.night_action(state, p, action)

    def witch_actions(self, state: GameState, seat: int, wolf_target: Optional[int]) -> tuple[bool, Optional[int]]:
        p = state.by_seat(seat)
        if not p:
            return False, None
        return self.mock.witch_actions(state, p, wolf_target)

    def wolf_kill_target(self, state: GameState) -> Optional[int]:
        return self.mock.wolf_kill_target(state)

    def wolf_vote_target(self, state: GameState) -> Optional[int]:
        return self.mock.wolf_vote_target(state)

    def auto_strategy(self, state: GameState, seat: int) -> StrategyPackage:
        p = state.by_seat(seat)
        return self.mock.auto_strategy(state, p) if p else StrategyPackage(auto=True)

    def vote(
        self,
        state: GameState,
        seat: int,
        adoption: Adoption,
        vote_advice: Optional[int] = None,
    ) -> Optional[int]:
        p = state.by_seat(seat)
        if not p:
            return None
        return self.mock.vote(
            state,
            p,
            adoption,
            vote_advice=vote_advice,
            vote_intent=self._vote_intent.get(seat),
        )

    def revenge_target(self, state: GameState, seat: int) -> Optional[int]:
        p = state.by_seat(seat)
        return self.mock.revenge_target(state, p) if p else None

    def knight_target(self, state: GameState, seat: int) -> Optional[int]:
        p = state.by_seat(seat)
        return self.mock.knight_target(state, p) if p else None

    def white_wolf_target(self, state: GameState, seat: int) -> Optional[int]:
        p = state.by_seat(seat)
        return self.mock.white_wolf_target(state, p) if p else None

    def last_words(self, state: GameState, seat: int) -> str:
        p = state.by_seat(seat)
        return self.mock.last_words(state, p) if p else ""

class LLMProbe:
    async def ping(self, config: AIConfig) -> str:
        return await LLMClient(config, timeout=20).ping()


class AIDirectorFactory:
    def create(self, configs: dict[int, AIConfig], seed: int) -> AIDirector:
        return AIDirector(configs, seed=seed)
