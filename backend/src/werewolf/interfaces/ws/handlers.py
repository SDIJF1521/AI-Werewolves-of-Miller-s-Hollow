from __future__ import annotations

import json
import time
from typing import Optional

from fastapi import Query, WebSocket, WebSocketDisconnect

from ...application.services.room_service import RoomService
from ...domain.rooms.entities import Room


async def websocket_endpoint(
    websocket: WebSocket,
    code: str,
    player_id: str = Query(...),
    token: str = Query(...),
):
    container = websocket.app.state.container
    service: RoomService = container.service
    room: Optional[Room] = None
    member = None
    conn = None

    try:
        room = service.get_or_raise(code)
        member = room.members.get(player_id)
        if not member or member.token != token:
            await websocket.close(code=4401, reason="unauthorized")
            return
    except LookupError:
        await websocket.close(code=4404, reason="room not found")
        return

    await websocket.accept()
    conn = await container.realtime.register(room.code, member.id, websocket)
    await service.presence(room, member, True)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await service.notifier_for(room).error(member.id, "消息格式错误")
                continue
            await handle_message(service, room, member, msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if room and member and conn:
            await service.voice_leave(room, member)
            await container.realtime.unregister(room.code, member.id, conn)
            online = await container.realtime.online(room.code)
            if member.id not in online:
                await service.presence(room, member, False)


async def handle_message(service: RoomService, room: Room, member, msg: dict) -> None:
    kind = str(msg.get("type") or "")
    notifier = service.notifier_for(room)
    try:
        if kind == "ping":
            await notifier.send(member.id, {"type": "pong", "at": time.time()})
            return
        if kind == "chat":
            await service.chat(room, member, str(msg.get("text") or ""))
            return
        if kind == "lobby_chat":
            await service.lobby_chat(room, member, str(msg.get("text") or ""))
            return
        if kind == "strategy":
            await service.submit_package(room, member, msg.get("package") or {})
            return
        if kind == "night_order":
            await service.submit_night_order(room, member, msg.get("order") or {})
            return
        if kind == "lock_team":
            await service.lock_team(room, member)
            return
        if kind == "reset_lock":
            await service.reset_lock(room, member)
            return
        if kind == "vote_advice":
            seat = msg.get("seat")
            await service.vote_advice(room, member, int(seat) if seat is not None else None)
            return
        if kind == "voice_join":
            await service.voice_join(room, member)
            return
        if kind == "voice_leave":
            await service.voice_leave(room, member)
            return
        if kind == "voice_signal":
            await service.voice_signal(room, member, str(msg.get("target") or ""), msg.get("signal") or {})
            return
        if kind == "voice_state":
            await service.voice_state(
                room,
                member,
                muted=bool(msg.get("muted", False)),
                speaking=bool(msg.get("speaking", False)),
            )
            return
        if kind == "advance":
            service.advance(room, member)
            return
        await notifier.error(member.id, f"未知消息类型：{kind}")
    except PermissionError as exc:
        await notifier.error(member.id, str(exc))
    except ValueError as exc:
        await notifier.error(member.id, str(exc))
    except Exception as exc:  # noqa: BLE001
        await notifier.error(member.id, f"操作失败：{exc}")
