"""夜间行动指令：AI 在刀/验/救/毒/守之前，先和自己的玩家密谈。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

NIGHT_ACTIONS = ("auto", "kill", "check", "save", "poison", "protect", "none")

KIND_LABELS = {
    "full": "完全执行",
    "partial": "部分执行",
    "misunderstood": "理解偏差",
    "defy": "自行行动",
    "auto": "自主判断",
}


@dataclass
class NightOrder:
    action: str = "auto"
    target: Optional[int] = None
    directive: str = ""
    auto: bool = True

    def normalized(self) -> NightOrder:
        action = self.action if self.action in NIGHT_ACTIONS else "auto"
        return NightOrder(
            action=action,
            target=self.target,
            directive=(self.directive or "").strip()[:140],
            auto=action == "auto",
        )

    def to_public(self) -> dict:
        return {
            "action": self.action,
            "target": self.target,
            "directive": self.directive,
            "auto": self.auto,
        }


@dataclass
class NightDecision:
    kind: str
    action: str
    target: Optional[int]
    summary: str
    label: str = ""
    directive: str = ""

    def to_public(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label or KIND_LABELS.get(self.kind, "自主判断"),
            "action": self.action,
            "target": self.target,
            "summary": self.summary,
            "directive": self.directive,
        }


def decide_night_order(
    order: Optional[NightOrder],
    *,
    obedience: float,
    logic: float,
    has_key: bool,
    role: str,
    alive_targets: list[int],
    rng: random.Random,
) -> NightDecision:
    """把玩家指令转成 AI 的夜间决定。

    和白天策略包一样，AI 可能完全执行、部分执行、理解偏差或抗命。
    夜间误解的落点会变成另一个合法目标（或直接交给 AI）。
    """
    if order is None or order.auto or order.action == "auto":
        return NightDecision(
            kind="auto",
            action="auto",
            target=None,
            summary="本夜没有玩家指令，AI 按自己的判断行动。",
        )

    if order.action == "none":
        return NightDecision(
            kind="full",
            action="none",
            target=None,
            summary="按玩家安排，本夜不使用主动技能。",
            label="按兵不动",
            directive=order.directive,
        )

    score = 0.58 * obedience + 0.2 * (1.0 if has_key else 0.0) + 0.12 + rng.uniform(-0.08, 0.08)
    target = order.target
    valid_targets = [seat for seat in alive_targets if seat != target]

    if score >= 0.68:
        return NightDecision(
            kind="full",
            action=order.action,
            target=target,
            summary=f"完全执行你的夜间指令：{_action_label(order.action)}{f' {target} 号' if target else ''}。",
            label="完全执行",
            directive=order.directive,
        )

    if score >= 0.55:
        return NightDecision(
            kind="partial",
            action=order.action,
            target=target,
            summary=f"执行了你的方向，但按自己的习惯收了收手：{_action_label(order.action)}{f' {target} 号' if target else ''}。",
            label="部分执行",
            directive=order.directive,
        )

    if score >= 0.42 and target and valid_targets:
        shifted = rng.choice(valid_targets)
        return NightDecision(
            kind="misunderstood",
            action=order.action,
            target=shifted,
            summary=f"把你的夜间安排理解偏了：本来指 {target} 号，最后改成了 {shifted} 号。",
            label="理解偏差",
            directive=order.directive,
        )

    return NightDecision(
        kind="defy",
        action="auto",
        target=None,
        summary="这次没按玩家的夜间安排走，AI 按自己的判断行动。",
        label="自行行动",
        directive=order.directive,
    )


def _action_label(action: str) -> str:
    return {
        "kill": "刀",
        "check": "验",
        "save": "救",
        "poison": "毒",
        "protect": "守",
    }.get(action, action)
