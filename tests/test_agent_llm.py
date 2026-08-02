"""Ollama 客户端：chat、extract_json、超时、并发繁忙、熔断。"""
import asyncio
import json

import httpx
import pytest

from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable


def _client(responses):
    if not isinstance(responses, list):
        responses = [responses]

    async def handler(request):
        resp = responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return httpx.Response(200, json=resp)

    return OllamaClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_chat_returns_content():
    client = _client({"message": {"content": "你好"}})
    result = await client.chat([{"role": "user", "content": "hi"}])
    assert result == "你好"


@pytest.mark.asyncio
async def test_extract_json():
    client = _client({"message": {"content": json.dumps({"intents": []})}})
    data = await client.extract_json([{"role": "user", "content": "x"}])
    assert data == {"intents": []}


@pytest.mark.asyncio
async def test_timeout_raises():
    client = _client(httpx.ConnectTimeout("timeout"))
    with pytest.raises(OllamaTimeout):
        await client.chat([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_busy_when_queue_full():
    async def slow(request):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json={"message": {"content": "ok"}})

    client = OllamaClient(
        transport=httpx.MockTransport(slow),
        max_concurrency=1,
        queue_timeout=0.05,
    )
    t1 = asyncio.create_task(client.chat([{"role": "user", "content": "x"}]))
    await asyncio.sleep(0.01)
    with pytest.raises(OllamaBusy):
        await client.chat([{"role": "user", "content": "y"}])
    await t1


@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    client = _client([httpx.ConnectTimeout("boom")] * 3)
    for _ in range(3):
        with pytest.raises(OllamaTimeout):
            await client.chat([{"role": "user", "content": "x"}])
    assert client.status() == "unavailable"
    with pytest.raises(OllamaUnavailable):
        await client.chat([{"role": "user", "content": "x"}])
