"""板子目录与时间配置。"""

from __future__ import annotations

from dataclasses import dataclass

from .roles import ROLES

POSTURES = ("冲锋", "倒钩", "划水", "表水", "悍跳")
LIE_LEVELS = ("禁止", "轻度", "重度")


@dataclass(frozen=True)
class Variant:
    key: str
    name: str
    player_count: int
    subtitle: str
    description: str
    tags: tuple[str, ...]
    roles: tuple[str, ...]
    rules: dict
    difficulty: str


VARIANTS: dict[str, Variant] = {
    "classic9": Variant(
        key="classic9",
        name="9 人经典局",
        player_count=9,
        subtitle="3 狼 · 预女猎 · 3 民",
        description="最紧凑的标准板子，节奏快、信息密度高。适合第一次和 AI 一起上车。",
        tags=("入门", "快节奏", "标准板"),
        roles=(
            "werewolf", "werewolf", "werewolf",
            "seer", "witch", "hunter",
            "villager", "villager", "villager",
        ),
        rules={
            "guard": False,
            "idiot": False,
            "wolf_king": False,
            "white_wolf_king": False,
            "knight": False,
            "double_save_death": False,
            "witch_one_potion_per_night": True,
        },
        difficulty="入门",
    ),
    "classic12": Variant(
        key="classic12",
        name="12 人预女猎白",
        player_count=12,
        subtitle="4 狼 · 预女猎白 · 4 民",
        description="经典 12 人标准板。白痴翻牌免死但失去投票权，考验好人阵营的轮次计算。",
        tags=("经典", "标准板", "白痴"),
        roles=(
            "werewolf", "werewolf", "werewolf", "werewolf",
            "seer", "witch", "hunter", "idiot",
            "villager", "villager", "villager", "villager",
        ),
        rules={
            "guard": False,
            "idiot": True,
            "wolf_king": False,
            "white_wolf_king": False,
            "knight": False,
            "double_save_death": False,
            "witch_one_potion_per_night": True,
        },
        difficulty="标准",
    ),
    "wolfking12": Variant(
        key="wolfking12",
        name="12 人狼王守卫",
        player_count=12,
        subtitle="狼王 + 3 狼 · 预女猎守 · 4 民",
        description="狼王出局可开枪，守卫与女巫存在同守同救判定。刀口与守护的博弈更重。",
        tags=("进阶", "狼王", "守卫"),
        roles=(
            "wolf_king", "werewolf", "werewolf", "werewolf",
            "seer", "witch", "hunter", "guard",
            "villager", "villager", "villager", "villager",
        ),
        rules={
            "guard": True,
            "idiot": False,
            "wolf_king": True,
            "white_wolf_king": False,
            "knight": False,
            "double_save_death": True,
            "witch_one_potion_per_night": True,
        },
        difficulty="进阶",
    ),
    "whitewolf12": Variant(
        key="whitewolf12",
        name="12 人白狼王骑士",
        player_count=12,
        subtitle="白狼王 + 3 狼 · 预女骑守 · 4 民",
        description="白狼王可白天自爆带人，骑士可决斗验狼。技能牌多，白天信息爆发强。",
        tags=("进阶", "白狼王", "骑士"),
        roles=(
            "white_wolf_king", "werewolf", "werewolf", "werewolf",
            "seer", "witch", "knight", "guard",
            "villager", "villager", "villager", "villager",
        ),
        rules={
            "guard": True,
            "idiot": False,
            "wolf_king": False,
            "white_wolf_king": True,
            "knight": True,
            "double_save_death": True,
            "witch_one_potion_per_night": True,
        },
        difficulty="进阶",
    ),
}


TIMINGS = {
    "standard": {
        "night_council": 30,
        "night": 12,
        "dawn": 8,
        "board": 8,
        "council": 80,
        "speech": 60,
        "vote_advice": 30,
        "vote_reveal": 8,
        "last_words": 30,
        "review": 120,
    },
    "fast": {
        "night_council": 8,
        "night": 5,
        "dawn": 3,
        "board": 4,
        "council": 12,
        "speech": 9,
        "vote_advice": 6,
        "vote_reveal": 5,
        "last_words": 7,
        "review": 60,
    },
}


def get_variant(key: str) -> Variant:
    if key not in VARIANTS:
        raise KeyError(f"unknown variant: {key}")
    return VARIANTS[key]


def variant_public(v: Variant) -> dict:
    counts: dict[str, int] = {}
    for r in v.roles:
        counts[r] = counts.get(r, 0) + 1
    return {
        "key": v.key,
        "name": v.name,
        "playerCount": v.player_count,
        "subtitle": v.subtitle,
        "description": v.description,
        "tags": list(v.tags),
        "rules": v.rules,
        "difficulty": v.difficulty,
        "roles": [
            {
                "key": k,
                "name": ROLES[k].name,
                "camp": ROLES[k].camp,
                "team": ROLES[k].team,
                "count": counts[k],
                "summary": ROLES[k].summary,
            }
            for k in counts
        ],
    }
