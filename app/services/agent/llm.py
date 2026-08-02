"""Ollama 客户端：无状态、不碰业务库；超时、并发信号量、连续失败熔断。"""
import asyncio
import json
import logging
import time

import httpx

logger = logging.getLogger("student_management")


class OllamaUnavailable(Exception):
    pass


class OllamaTimeout(Exception):
    pass


class OllamaBusy(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout: float = 10.0,
        max_concurrency: int = 4,
        queue_timeout: float = 15.0,
        circuit_failures: int = 3,
        circuit_cooldown: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.queue_timeout = queue_timeout
        self.circuit_failures = circuit_failures
        self.circuit_cooldown = circuit_cooldown
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._sem = asyncio.Semaphore(max_concurrency)
        self._consecutive_failures = 0
        self._open_until = 0.0

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, transport=self._transport)
        return self._client

    def status(self) -> str:
        if time.time() < self._open_until:
            return "unavailable"
        return "ok"

    async def ping(self) -> bool:
        """轻量探测 Ollama 是否在线（GET /api/tags），不计入熔断计数。"""
        if time.time() < self._open_until:
            return False
        try:
            resp = await self._get_client().get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return True
        except (httpx.HTTPError, httpx.TimeoutException):
            return False

    def _note_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_failures:
            self._open_until = time.time() + self.circuit_cooldown
            self._consecutive_failures = 0
            logger.warning("Ollama circuit breaker opened for %ss", self.circuit_cooldown)

    async def _run(self, fn):
        if time.time() < self._open_until:
            raise OllamaUnavailable("模型服务熔断中，请稍后重试")
        acquired = False
        try:
            try:
                await asyncio.wait_for(self._sem.acquire(), timeout=self.queue_timeout)
                acquired = True
            except asyncio.TimeoutError:
                raise OllamaBusy("模型服务繁忙，请稍后重试")
            return await fn()
        except (OllamaBusy, OllamaUnavailable, OllamaTimeout):
            raise
        except httpx.TimeoutException:
            self._note_failure()
            raise OllamaTimeout("模型响应超时")
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            self._note_failure()
            raise OllamaUnavailable("模型服务不可用")
        finally:
            if acquired:
                self._sem.release()

    async def chat(self, messages: list[dict], format_json: bool = False) -> str:
        async def call():
            payload = {"model": self.model, "messages": messages, "stream": False}
            if format_json:
                payload["format"] = "json"
            resp = await self._get_client().post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        return await self._run(call)

    async def extract_json(self, messages: list[dict]) -> dict:
        content = await self.chat(messages, format_json=True)
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("模型输出不是 JSON 对象")
        return data
