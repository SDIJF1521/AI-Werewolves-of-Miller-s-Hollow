"""AI 端口与跨层 DTO。

application 只依赖这个 Protocol；具体 LLM/演示脑实现放在 infrastructure。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from ...domain.council.strategy import Adoption, AggregatedStrategy, StrategyPackage
from ...domain.game.entities import GameState

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "custom": "",
}
DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
    "moonshot": "moonshot-v1-8k",
    "custom": "",
}


@dataclass
class AIConfig:
    """模型连接配置，含明文密钥；只允许出现在 application/infrastructure。"""

    provider: str = "deepseek"
    base_url: str = ""
    model: str = ""
    api_key: str = ""

    def normalized(self) -> AIConfig:
        provider = self.provider if self.provider in DEFAULT_BASE_URLS else "custom"
        base = (self.base_url or DEFAULT_BASE_URLS.get(provider, "")).rstrip("/")
        model = self.model or DEFAULT_MODELS.get(provider, "")
        return AIConfig(provider=provider, base_url=base, model=model, api_key=self.api_key.strip())

    @property
    def masked_key(self) -> str:
        if not self.api_key:
            return ""
        if len(self.api_key) > 10:
            return self.api_key[:4] + "…" + self.api_key[-4:]
        return "••••"

    def public(self) -> dict:
        return {
            "provider": self.provider,
            "baseUrl": self.base_url,
            "model": self.model,
            "maskedKey": self.masked_key,
            "hasKey": bool(self.api_key),
        }


@dataclass
class AIResult:
    speech: str
    claim: str = "none"
    suspects: list[int] = field(default_factory=list)
    trusts: list[int] = field(default_factory=list)
    vote_intent: Optional[int] = None
    inner: str = ""
    feedback_detail: str = ""
    source: str = "mock"
    error: Optional[str] = None


@dataclass
class AIStatus:
    seat: int
    mode: str = "demo"  # demo / llm / fallback
    model: str = ""
    last_error: str = ""

    def public(self) -> dict:
        return {"seat": self.seat, "mode": self.mode, "model": self.model, "lastError": self.last_error}


class AIAgent(Protocol):
    """一局中所有 AI 玩家的能力集合（每个座位一个 Agent）。"""

    def has_key(self, seat: int) -> bool: ...
    def status_public(self) -> list[dict]: ...
    def config_public(self, seat: int) -> dict: ...
    async def speak(
        self,
        state: GameState,
        seat: int,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
        recent_speeches: Optional[list[str]] = None,
    ) -> AIResult: ...
    def demo_speak(
        self,
        state: GameState,
        seat: int,
        agg: Optional[AggregatedStrategy],
        adoption: Adoption,
    ) -> AIResult: ...
    def night_action(self, state: GameState, seat: int, action: str) -> Optional[int]: ...
    def witch_actions(self, state: GameState, seat: int, wolf_target: Optional[int]) -> tuple[bool, Optional[int]]: ...
    def wolf_kill_target(self, state: GameState) -> Optional[int]: ...
    def wolf_vote_target(self, state: GameState) -> Optional[int]: ...
    def auto_strategy(self, state: GameState, seat: int) -> StrategyPackage: ...
    def vote(
        self,
        state: GameState,
        seat: int,
        adoption: Adoption,
        vote_advice: Optional[int] = None,
    ) -> Optional[int]: ...
    def revenge_target(self, state: GameState, seat: int) -> Optional[int]: ...
    def knight_target(self, state: GameState, seat: int) -> Optional[int]: ...
    def white_wolf_target(self, state: GameState, seat: int) -> Optional[int]: ...
    def last_words(self, state: GameState, seat: int) -> str: ...


class AIAgentFactory(Protocol):
    def create(self, configs: dict[int, AIConfig], seed: int) -> AIAgent: ...


class AIProbe(Protocol):
    async def ping(self, config: AIConfig) -> str: ...
