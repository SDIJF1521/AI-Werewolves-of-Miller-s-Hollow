"""智囊团策略包：加权聚合与 AI 采纳判定。

设计原则：
1. 人类只给“策略”，不给逐字稿；
2. 同一 AI 的玩家指令按权重聚合；当前版本一名玩家控制一个 AI；
3. 聚合结果不是命令，AI 会按性格与服从度决定采纳程度；
4. 所有“误解/抗命”都落在实际行为上，而不只是文案。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Optional

from ..game.variants import LIE_LEVELS, POSTURES


@dataclass
class StrategyPackage:
    posture: str = "表水"
    protect_seat: Optional[int] = None
    attack_seat: Optional[int] = None
    lie_level: str = "轻度"
    vote_seat: Optional[int] = None
    directive: str = ""
    auto: bool = False

    def normalized(self) -> StrategyPackage:
        posture = self.posture if self.posture in POSTURES else "表水"
        lie = self.lie_level if self.lie_level in LIE_LEVELS else "轻度"
        return StrategyPackage(
            posture=posture,
            protect_seat=self.protect_seat,
            attack_seat=self.attack_seat,
            lie_level=lie,
            vote_seat=self.vote_seat,
            directive=(self.directive or "").strip()[:140],
            auto=self.auto,
        )

    def to_public(self) -> dict:
        return {
            "posture": self.posture,
            "protectSeat": self.protect_seat,
            "attackSeat": self.attack_seat,
            "lieLevel": self.lie_level,
            "voteSeat": self.vote_seat,
            "directive": self.directive,
            "auto": self.auto,
        }

    def key_points(self) -> list[str]:
        points = [f"姿态：{self.posture}", f"撒谎许可：{self.lie_level}"]
        if self.protect_seat:
            points.append(f"主保 {self.protect_seat} 号")
        if self.attack_seat:
            points.append(f"主打 {self.attack_seat} 号")
        if self.vote_seat:
            points.append(f"建议投 {self.vote_seat} 号")
        return points


@dataclass
class Contributor:
    member_id: str
    name: str
    weight: float
    is_captain: bool = False
    has_key: bool = False


@dataclass
class AggregatedStrategy:
    package: StrategyPackage
    contributors: list[Contributor] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    total_weight: float = 0.0
    clarity: float = 0.0

    @property
    def influence(self) -> float:
        return min(self.total_weight / 4.2, 1.0)

    def public_summary(self) -> dict:
        return {
            "package": self.package.to_public(),
            "contributors": [
                {
                    "memberId": c.member_id,
                    "name": c.name,
                    "weight": round(c.weight, 2),
                    "isCaptain": c.is_captain,
                    "hasKey": c.has_key,
                }
                for c in self.contributors
            ],
            "notes": self.notes,
            "totalWeight": round(self.total_weight, 2),
            "clarity": round(self.clarity, 2),
        }


ADOPTION_LABELS = {
    "full": "完全采纳",
    "partial": "部分采纳",
    "misunderstood": "误解指令",
    "defy": "抗命",
    "auto": "自主决策",
}


@dataclass
class Adoption:
    kind: str
    effective: Optional[StrategyPackage]
    summary: str
    adopted: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    misunderstood_as: str = ""
    tone: str = "正常"
    adherence: float = 0.0

    @property
    def label(self) -> str:
        return ADOPTION_LABELS.get(self.kind, "自主决策")

    def to_public(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "summary": self.summary,
            "adopted": self.adopted,
            "ignored": self.ignored,
            "misunderstoodAs": self.misunderstood_as,
            "tone": self.tone,
            "adherence": round(self.adherence, 2),
        }


def _tally(values: list[tuple[Optional[int], float]], captain_choice: Optional[int] = None):
    score: dict[int, float] = {}
    count: dict[int, int] = {}
    for value, weight in values:
        if value is None:
            continue
        score[value] = score.get(value, 0.0) + weight
        count[value] = count.get(value, 0) + 1
    if not score:
        return None
    best = max(score.values())
    tied = [seat for seat, sc in score.items() if abs(sc - best) < 1e-6]
    if captain_choice in tied:
        return captain_choice
    return sorted(tied, key=lambda s: (-count[s], s))[0]


def _tally_text(values: list[tuple[str, float]], captain_choice: str, allowed: tuple[str, ...]):
    score: dict[str, float] = {}
    for value, weight in values:
        if value:
            score[value] = score.get(value, 0.0) + weight
    if not score:
        return captain_choice
    best = max(score.values())
    tied = [v for v, sc in score.items() if abs(sc - best) < 1e-6]
    if captain_choice in tied:
        return captain_choice
    for value in allowed:
        if value in tied:
            return value
    return captain_choice


def aggregate_packages(
    packages: dict[str, StrategyPackage],
    contributors: dict[str, Contributor],
    captain_id: Optional[str] = None,
) -> Optional[AggregatedStrategy]:
    """按权重聚合玩家的策略包。

    指导语（directive）是“最终汇报给 AI 的用户输入”：
    优先取该 AI 玩家的原话；兼容多份提交时取权重最高者，其他内容作为补充备注。
    """
    if not packages:
        return None

    contributors = {k: v for k, v in contributors.items() if k in packages}
    ordered = sorted(
        packages.items(),
        key=lambda kv: (kv[0] == captain_id, contributors.get(kv[0], Contributor(kv[0], "", 0)).weight),
        reverse=True,
    )
    cap = next((p for mid, p in ordered if mid == captain_id), None)
    weights = {mid: contributors.get(mid, Contributor(mid, "", 1.0)).weight for mid in packages}

    posture = _tally_text(
        [(p.posture, weights[mid]) for mid, p in packages.items()],
        cap.posture if cap else "表水",
        POSTURES,
    )
    lie = _tally_text(
        [(p.lie_level, weights[mid]) for mid, p in packages.items()],
        cap.lie_level if cap else "轻度",
        LIE_LEVELS,
    )
    protect = _tally(
        [(p.protect_seat, weights[mid]) for mid, p in packages.items()],
        cap.protect_seat if cap else None,
    )
    attack = _tally(
        [(p.attack_seat, weights[mid]) for mid, p in packages.items()],
        cap.attack_seat if cap else None,
    )
    vote = _tally(
        [(p.vote_seat, weights[mid]) for mid, p in packages.items()],
        cap.vote_seat if cap else None,
    )

    leader = cap or ordered[0][1]
    leader_id = captain_id if cap else ordered[0][0]
    leader_weight = weights.get(leader_id, 1.0)
    directive = (leader.directive or "").strip()
    if not directive:
        directive = next(((p.directive or "").strip() for _, p in ordered if (p.directive or "").strip()), "")
    notes: list[str] = []
    for mid, p in ordered:
        if mid == leader_id:
            continue
        text = (p.directive or "").strip()
        if text and text not in notes:
            notes.append(text)
        if len(notes) >= 2:
            break

    final = StrategyPackage(
        posture=posture,
        protect_seat=protect,
        attack_seat=attack,
        lie_level=lie,
        vote_seat=vote,
        directive=directive,
    ).normalized()

    filled = sum(
        [
            1.0,
            1.0,
            1.0 if protect else 0.0,
            1.0 if attack else 0.0,
            1.0 if vote else 0.0,
            min(len(directive) / 40.0, 1.0),
        ]
    )
    clarity = round(min(filled / 6.0 + leader_weight * 0.02, 1.0), 3)
    total = round(sum(weights.values()), 2)

    return AggregatedStrategy(
        package=final,
        contributors=[contributors[mid] for mid in packages],
        notes=notes,
        total_weight=total,
        clarity=clarity,
    )


def _describe_adopted(pkg: StrategyPackage) -> list[str]:
    out = [f"姿态 {pkg.posture}"]
    if pkg.protect_seat:
        out.append(f"主保 {pkg.protect_seat} 号")
    if pkg.attack_seat:
        out.append(f"主打 {pkg.attack_seat} 号")
    if pkg.vote_seat:
        out.append(f"投 {pkg.vote_seat} 号")
    out.append(f"撒谎许可 {pkg.lie_level}")
    return out


def _misread(pkg: StrategyPackage, rng: random.Random) -> tuple[StrategyPackage, str]:
    rolled = rng.random()
    if pkg.protect_seat and pkg.attack_seat and rolled < 0.34:
        swapped = replace(pkg, protect_seat=pkg.attack_seat, attack_seat=pkg.protect_seat)
        return (
            swapped,
            f"把“保 {pkg.protect_seat}、打 {pkg.attack_seat}”听反了，变成了保 {pkg.attack_seat}、打 {pkg.protect_seat}。",
        )
    if pkg.protect_seat and rolled < 0.68:
        bound = replace(pkg, vote_seat=pkg.protect_seat)
        return (
            bound,
            f"把“保 {pkg.protect_seat} 号”理解成了“和 {pkg.protect_seat} 号绑定”，连票都想跟着他走。",
        )
    if pkg.vote_seat and rolled < 0.85:
        moved = replace(pkg, attack_seat=pkg.vote_seat, vote_seat=None)
        return (
            moved,
            f"把“建议投 {pkg.vote_seat} 号”当成了“必须死打 {pkg.vote_seat} 号”，投票反而没了准头。",
        )
    tone = "把“冲锋”做成了不计后果的贴脸输出" if pkg.posture == "冲锋" else "把策略执行得过于字面"
    return replace(pkg, posture="冲锋" if pkg.posture == "冲锋" else pkg.posture), f"{tone}，意图对了但方式跑偏。"


def decide_adoption(
    strategy: Optional[AggregatedStrategy],
    *,
    obedience: float,
    logic: float,
    rng: random.Random,
    has_key: bool,
) -> Adoption:
    """决定 AI 本轮对玩家指令的采纳程度。

    权重高、指令清晰、AI 服从度高 → 更容易完全采纳；
    性格强势/多疑的 AI 更容易抗命。
    """
    if strategy is None:
        return Adoption(
            kind="auto",
            effective=None,
            summary="本轮没有收到有效策略包，AI 按自己的判断行动。",
            adherence=0.0,
        )

    influence = strategy.influence
    score = (
        0.55 * obedience
        + 0.21 * influence
        + 0.16 * strategy.clarity
        + 0.08 * (1.0 - logic) * 0.4
        + (0.035 if has_key else 0.0)
        + rng.uniform(-0.07, 0.07)
    )
    pkg = strategy.package

    if score >= 0.68:
        return Adoption(
            kind="full",
            effective=pkg,
            summary=f"完全按玩家方案执行：{pkg.posture}，主保 {pkg.protect_seat or '—'}、主打 {pkg.attack_seat or '—'}。",
            adopted=_describe_adopted(pkg),
            adherence=1.0,
            tone="克制、准确",
        )
    if score >= 0.56:
        tone = rng.choice(["语气比玩家要求更冲", "执行时加了太多个人情绪", "关键处留了半手"])
        return Adoption(
            kind="partial",
            effective=pkg,
            summary=f"大方向采纳，但{tone}。",
            adopted=_describe_adopted(pkg),
            ignored=[f"“{pkg.directive}”里的分寸感"] if pkg.directive else [],
            adherence=0.62,
            tone=tone,
        )
    if score >= 0.44:
        effective, note = _misread(pkg, rng)
        return Adoption(
            kind="misunderstood",
            effective=effective,
            summary=f"误解了指令：{note}",
            adopted=_describe_adopted(pkg)[:2],
            ignored=[pkg.directive] if pkg.directive else [],
            misunderstood_as=note,
            adherence=0.34,
            tone="笃定但方向跑偏",
        )

    return Adoption(
        kind="defy",
        effective=None,
        summary="没有采纳玩家方案，AI 按自己的判断临时改线。",
        adopted=[],
        ignored=_describe_adopted(pkg),
        adherence=0.0,
        tone="我行我素",
    )
