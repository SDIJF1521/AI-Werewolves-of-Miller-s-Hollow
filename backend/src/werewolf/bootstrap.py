"""组合根：把基础设施适配器装配进应用服务。"""

from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv

from .application.services.room_service import RoomService
from .infrastructure.ai.adapter import AIDirectorFactory, LLMProbe
from .infrastructure.persistence.memory_rooms import InMemoryRoomRepository
from .infrastructure.realtime.ws_hub import WebSocketHub
from .infrastructure.security.memory_vault import MemoryCredentialVault

load_dotenv()


@dataclass
class Container:
    rooms: InMemoryRoomRepository
    realtime: WebSocketHub
    vault: MemoryCredentialVault
    ai_factory: AIDirectorFactory
    probe: LLMProbe
    service: RoomService


def build_container() -> Container:
    rooms = InMemoryRoomRepository()
    realtime = WebSocketHub()
    vault = MemoryCredentialVault()
    ai_factory = AIDirectorFactory()
    probe = LLMProbe()
    service = RoomService(rooms, realtime, vault, ai_factory)
    return Container(rooms, realtime, vault, ai_factory, probe, service)
