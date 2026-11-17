from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request

from ...application.ports.ai import DEFAULT_BASE_URLS, DEFAULT_MODELS, AIConfig
from ...application.presenters import member_public, room_public, snapshot
from ...domain.game.personas import PERSONAS
from ...domain.game.roles import role_public
from ...domain.game.variants import LIE_LEVELS, POSTURES, TIMINGS, VARIANTS, variant_public
from ...domain.rooms.entities import Member, Room
from .schemas import (
    AssignTeamBody,
    CaptainBody,
    CreateRoomBody,
    JoinRoomBody,
    KeyBody,
    TestKeyBody,
)

router = APIRouter(prefix="/api")


def container(request: Request):
    return request.app.state.container


def room_or_404(code: str, request: Request) -> Room:
    try:
        return container(request).service.get_or_raise(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def auth(room: Room, player_id: Optional[str], token: Optional[str]) -> Member:
    if not player_id or not token:
        raise HTTPException(status_code=401, detail="缺少玩家身份，请重新加入房间")
    member = room.members.get(player_id)
    if not member or member.token != token:
        raise HTTPException(status_code=401, detail="身份已失效，请重新加入房间")
    return member


def session_payload(room: Room, member: Member) -> dict:
    return {
        "playerId": member.id,
        "token": member.token,
        "member": member_public(room, member),
        "room": room_public(room),
    }


@router.get("/health")
async def health(request: Request):
    c = container(request)
    return {"ok": True, "rooms": len(c.rooms.list()), "app": "AI 狼人杀 · 幕后智囊团"}


@router.get("/config")
async def game_config():
    return {
        "appName": "AI 狼人杀 · 幕后智囊团",
        "variants": [variant_public(v) for v in VARIANTS.values()],
        "roles": role_public(),
        "postures": list(POSTURES),
        "lieLevels": list(LIE_LEVELS),
        "timings": TIMINGS,
        "personas": [
            {
                "name": p.name,
                "avatar": p.avatar,
                "title": p.title,
                "intro": p.intro,
                "color": p.color,
                "temperament": p.temperament,
            }
            for p in PERSONAS
        ],
        "providers": [
            {
                "key": key,
                "name": {
                    "deepseek": "DeepSeek",
                    "openai": "OpenAI",
                    "siliconflow": "硅基流动",
                    "moonshot": "Moonshot",
                    "custom": "自定义 OpenAI 兼容",
                }.get(key, key),
                "baseUrl": DEFAULT_BASE_URLS[key],
                "defaultModel": DEFAULT_MODELS[key],
            }
            for key in DEFAULT_BASE_URLS
        ],
    }


@router.get("/ice")
async def ice_config():
    stun = os.getenv("STUN_URLS", "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302")
    servers = [{"urls": u.strip()} for u in stun.split(",") if u.strip()]
    turn_url = os.getenv("TURN_URL", "")
    if turn_url:
        servers.append(
            {
                "urls": turn_url,
                "username": os.getenv("TURN_USERNAME", ""),
                "credential": os.getenv("TURN_CREDENTIAL", ""),
            }
        )
    return {"iceServers": servers}


@router.post("/rooms")
async def create_room(body: CreateRoomBody, request: Request):
    if body.variantKey not in VARIANTS:
        raise HTTPException(status_code=400, detail="未知板子")
    if body.timing not in TIMINGS:
        raise HTTPException(status_code=400, detail="未知节奏")
    if body.mode not in ("multiplayer", "practice"):
        raise HTTPException(status_code=400, detail="未知对局模式")
    try:
        room = container(request).service.create(
            host_name=body.name,
            room_name=body.roomName or f"{body.name} 的牌局",
            variant_key=body.variantKey,
            timing=body.timing,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    host = room.members[room.host_id]
    return {"code": room.code, **session_payload(room, host)}


@router.get("/rooms/{code}")
async def get_room(code: str, request: Request):
    room = room_or_404(code, request)
    return {"room": room_public(room), "serverTime": int(time.time() * 1000)}


@router.get("/rooms/{code}/snapshot")
async def get_snapshot(
    code: str,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    return snapshot(room, member, container(request).service.statuses(room))


@router.post("/rooms/{code}/join")
async def join_room(code: str, body: JoinRoomBody, request: Request):
    room = room_or_404(code, request)
    try:
        member = await container(request).service.join(room, body.name, body.teamSeat, body.spectator)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return session_payload(room, member)


@router.post("/rooms/{code}/team")
async def assign_team(
    code: str,
    body: AssignTeamBody,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    try:
        await container(request).service.assign_team(room, member, body.teamSeat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "member": member_public(room, member)}


@router.post("/rooms/{code}/captain")
async def set_captain(
    code: str,
    body: CaptainBody,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    try:
        await container(request).service.set_captain(room, member, body.teamSeat, body.captainId)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.post("/rooms/{code}/key")
async def set_key(
    code: str,
    body: KeyBody,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    cfg = AIConfig(body.provider, body.baseUrl, body.model, body.apiKey)
    try:
        await container(request).service.set_key(room, member, cfg)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "key": room.teams[member.team_seat].key_public()}


@router.delete("/rooms/{code}/key")
async def delete_key(
    code: str,
    request: Request,
    seat: int = Query(...),
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    try:
        await container(request).service.clear_key(room, member, seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.post("/rooms/{code}/start")
async def start_game(
    code: str,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    try:
        await container(request).service.start_game(room, member)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "status": room.status}


@router.post("/rooms/{code}/advance")
async def advance(
    code: str,
    request: Request,
    x_player_id: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    room = room_or_404(code, request)
    member = auth(room, x_player_id, x_session_token)
    try:
        container(request).service.advance(room, member)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return {"ok": True}


@router.post("/ai/test")
async def test_ai_key(body: TestKeyBody, request: Request):
    cfg = AIConfig(body.provider, body.baseUrl, body.model, body.apiKey).normalized()
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="请填写 API Key")
    try:
        reply = await container(request).probe.ping(cfg)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "reply": reply, "model": cfg.model, "baseUrl": cfg.base_url}
