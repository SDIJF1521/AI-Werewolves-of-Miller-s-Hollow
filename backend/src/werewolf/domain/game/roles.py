"""角色值对象与角色目录。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    key: str
    name: str
    camp: str  # wolf / good
    team: str  # wolf / god / villager
    summary: str
    ability: str
    color: str


ROLES: dict[str, Role] = {
    "werewolf": Role(
        "werewolf", "狼人", "wolf", "wolf",
        "夜晚与狼队友共同刀人，白天伪装成好人。",
        "每晚与狼队共同选择一名玩家击杀；可以悍跳、倒钩、自爆（若板子允许）。",
        "#d9534f",
    ),
    "wolf_king": Role(
        "wolf_king", "狼王", "wolf", "wolf",
        "狼队领袖，出局时可能开枪带走一人。",
        "被投票放逐或被狼刀带走时可以开枪；被女巫毒杀时不能开枪。",
        "#b23a48",
    ),
    "white_wolf_king": Role(
        "white_wolf_king", "白狼王", "wolf", "wolf",
        "白天可以自爆并带走一名玩家。",
        "白天发言/投票阶段可自爆，公开身份并指定一名玩家一起出局。",
        "#8e3b5a",
    ),
    "seer": Role(
        "seer", "预言家", "good", "god",
        "每晚查验一名玩家的阵营。",
        "每晚查验一人，得到“好人/狼人”的结果；需要带领好人找狼。",
        "#e8b84b",
    ),
    "witch": Role(
        "witch", "女巫", "good", "god",
        "拥有一瓶解药和一瓶毒药。",
        "每晚可救被狼刀的人或毒杀一人，通常一晚只能使用一瓶药。",
        "#8f6bd6",
    ),
    "hunter": Role(
        "hunter", "猎人", "good", "god",
        "出局时可以开枪带走一人。",
        "被狼刀或放逐时可以开枪；被女巫毒杀时不能开枪。",
        "#c9824b",
    ),
    "guard": Role(
        "guard", "守卫", "good", "god",
        "每晚守护一人，使其免于狼刀。",
        "不能连续两晚守护同一人；与女巫解药同时作用可能造成“同守同救”死亡（视板子）。",
        "#4c9f8a",
    ),
    "idiot": Role(
        "idiot", "白痴", "good", "god",
        "被放逐时翻牌免死，但失去投票权。",
        "首次被放逐时翻牌存活，之后不能再投票；仍算神职。",
        "#7fa6c9",
    ),
    "knight": Role(
        "knight", "骑士", "good", "god",
        "白天可以决斗一名玩家。",
        "决斗狼人则狼人出局；决斗好人则骑士出局。整局一次。",
        "#5c8dd6",
    ),
    "villager": Role(
        "villager", "平民", "good", "villager",
        "没有技能，靠发言和投票找狼。",
        "白天分析、站边、投票，是好人阵营的投票基本盘。",
        "#9aa7b4",
    ),
}


def role_public() -> list[dict]:
    return [
        {
            "key": r.key,
            "name": r.name,
            "camp": r.camp,
            "team": r.team,
            "summary": r.summary,
            "ability": r.ability,
            "color": r.color,
        }
        for r in ROLES.values()
    ]
