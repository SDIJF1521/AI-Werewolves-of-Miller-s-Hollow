from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateRoomBody(BaseModel):
    name: str = Field(min_length=1, max_length=16)
    roomName: str = Field(default="", max_length=24)
    variantKey: str = "classic9"
    timing: str = "standard"
    mode: str = "multiplayer"


class JoinRoomBody(BaseModel):
    name: str = Field(min_length=1, max_length=16)
    teamSeat: Optional[int] = None
    spectator: bool = False


class AssignTeamBody(BaseModel):
    teamSeat: Optional[int] = None


class CaptainBody(BaseModel):
    teamSeat: int
    captainId: Optional[str] = None


class KeyBody(BaseModel):
    provider: str = "deepseek"
    baseUrl: str = ""
    model: str = ""
    apiKey: str = ""


class TestKeyBody(BaseModel):
    provider: str = "deepseek"
    baseUrl: str = ""
    model: str = ""
    apiKey: str = ""
