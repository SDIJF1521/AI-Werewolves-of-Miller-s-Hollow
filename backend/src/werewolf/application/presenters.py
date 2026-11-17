"""应用层读模型 / Presenter。

领域层保持纯净；所有给前端的 JSON 结构在这里组装。
"""

from __future__ import annotations

from typing import Optional

from ..domain.game.variants import variant_public
from ..domain.rooms.entities import Member, Room, TeamState
from ..domain.shared.time import now_ms


def member_public(room: Room, member: Member) -> dict:
    team = room.teams.get(member.team_seat or 0)
    return {
        "id": member.id,
        "name": member.name,
        "teamSeat": member.team_seat,
        "isHost": member.id == room.host_id,
        "isSpectator": member.is_spectator,
        "connected": member.connected,
        "weight": room.member_weight(member),
        "isCaptain": bool(team and team.captain_id == member.id),
        "hasKey": bool(team and team.key_holder_id == member.id and team.has_key),
        "voiceMuted": member.voice_muted,
        "voiceSpeaking": member.voice_speaking,
    }


def ai_identity(room: Room, seat: int) -> dict:
    p = room.game.by_seat(seat) if room.game else None
    persona = p.persona if p else room.ai_persona(seat)
    reveal = room.status == "finished"
    return {
        "seat": seat,
        "name": persona.name,
        "avatar": persona.avatar,
        "title": persona.title,
        "color": persona.color,
        "role": p.role if (p and reveal) else None,
        "roleName": p.role_def.name if (p and reveal) else None,
    }


def team_public(room: Room, seat: int) -> dict:
    team: TeamState = room.teams[seat]
    members = room.team_members(seat)
    return {
        "seat": seat,
        "ai": ai_identity(room, seat),
        "members": [member_public(room, m) for m in members],
        "advisorCount": len(members),
        "captainId": team.captain_id,
        "hasKey": team.has_key,
        "key": team.key_public(),
        "submittedCount": len(team.packages),
        "locked": team.locked,
        "nightLocked": team.night_locked,
        "nightOrder": team.night_order.to_public() if team.night_order else None,
        "voiceCount": len(team.voice),
        "voice": room.team_voice_members(seat),
    }


def room_public(room: Room) -> dict:
    staffed = sum(1 for seat in room.teams if room.team_members(seat))
    return {
        "code": room.code,
        "name": room.name,
        "status": room.status,
        "mode": room.mode,
        "hostId": room.host_id,
        "variantKey": room.variant_key,
        "variant": variant_public(room.variant),
        "timing": room.timing,
        "timings": room.timings,
        "playerCount": room.variant.player_count,
        "minPlayers": 9,
        "maxAdvisors": 1,
        "maxPlayersPerAi": 1,
        "memberCount": len(room.members),
        "staffedTeams": staffed,
        "spectatorCount": sum(1 for m in room.members.values() if m.is_spectator),
        "createdAt": room.created_at,
        "teams": [team_public(room, seat) for seat in sorted(room.teams)],
        "lobbyChat": room.lobby_chat[-80:],
        "lobbyVoice": room.lobby_voice_members(),
        "maxLobbyVoice": 8,
    }


def team_private(room: Room, member: Member) -> dict:
    if not member.team_seat:
        return {}
    seat = member.team_seat
    team = room.teams[seat]
    agg = room.aggregate_for(team) if team.packages else team.final_aggregate
    return {
        "seat": seat,
        "ai": ai_identity(room, seat),
        "members": [member_public(room, m) for m in room.team_members(seat)],
        "packages": {mid: pkg.to_public() for mid, pkg in team.packages.items()},
        "locked": team.locked,
        "advice": team.advice,
        "nightOrder": team.night_order.to_public() if team.night_order else None,
        "nightLocked": team.night_locked,
        "nightFeedback": team.night_feedback,
        "chat": team.chat[-80:],
        "voice": room.team_voice_members(seat),
        "aggregate": agg.public_summary() if agg else None,
        "captainId": team.captain_id,
        "key": team.key_public(),
    }


def private_for_member(room: Room, member: Member, ai_status: Optional[list[dict]] = None) -> dict:
    if not member.team_seat:
        return {}
    seat = member.team_seat
    team = room.teams[seat]
    data = {
        "teamSeat": seat,
        "captainId": team.captain_id,
        "key": team.key_public(),
        "submittedCount": len(team.packages),
        "locked": team.locked,
        "advice": team.advice,
        "voice": room.team_voice_members(seat),
        "aiStatus": None,
    }
    if room.game:
        data.update(room.game.private_for(seat))
        statuses = ai_status or []
        data["aiStatus"] = next(
            (s for s in statuses if s.get("seat") == seat),
            {"seat": seat, "mode": "demo", "model": "本地演示脑", "lastError": ""},
        )
    return data


def snapshot(room: Room, member: Member, ai_status: Optional[list[dict]] = None) -> dict:
    data = {
        "room": room_public(room),
        "you": member_public(room, member),
        "team": team_private(room, member) if member.team_seat else None,
        "private": private_for_member(room, member, ai_status),
        "serverTime": now_ms(),
    }
    if room.game:
        data["game"] = room.game.public_state(
            reveal=room.status == "finished",
            viewer_team=member.team_seat,
        )
        data["aiStatus"] = ai_status or []
        if room.status == "finished":
            data["review"] = room.game.review()
    return data
