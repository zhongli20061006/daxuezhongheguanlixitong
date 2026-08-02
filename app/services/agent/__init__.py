"""智能体服务包：消息协议模型。"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """对话消息协议：前端按 kind 渲染不同卡片。"""
    kind: Literal["text", "card", "confirmation", "error", "summary"]
    title: str = ""
    content: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    confirm_token: str | None = None
    navigation: str | None = None


__all__ = ["AgentMessage"]
