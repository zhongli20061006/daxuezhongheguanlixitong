# AI 智能体助手（Agent 主页）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给大学生管理系统新增一个默认主页——对话式智能体：自然语言指令 → 意图识别（本地 Qwen 优先 + 规则兜底）→ 动作执行（只读直跑、写操作二次确认），支持页面跳转、明天课表查询、学习方案生成、选课/退课，并配套多会话窗口与 `agent01` 测试账号。

**Architecture:** 后端新增 `app/services/agent/` 包（session/confirmations/llm/intent/actions）与 `app/api/agent.py` 路由，复用现有 JWT 认证与业务服务层，LLM 只经 `actions.py` 注入的脱敏上下文访问 Ollama（无状态、不碰 DB）。前端新增 `Agent.vue` 作为 `/` 默认路由，配合 Pinia store 管理会话与消息卡片。设计文档：`docs/superpowers/specs/2026-08-02-agent-assistant-design.md`。

**Tech Stack:** FastAPI、SQLAlchemy async、Pydantic v2、httpx（调用 Ollama）、pytest-asyncio、Vue 3 + Element Plus + Pinia。

---

## 文件结构总览

后端新增：

- `app/services/agent/__init__.py` — `AgentMessage` 消息模型（前后端协议）
- `app/services/agent/confirmations.py` — 一次性确认令牌
- `app/services/agent/session.py` — 多会话记忆（窗口/事实表/上下文预算）
- `app/services/agent/llm.py` — Ollama 客户端（超时/并发/熔断）
- `app/services/agent/intent.py` — 意图模型 + 规则兜底 + 解析器（LLM 优先）
- `app/services/agent/actions.py` — 动作执行器（权限复核/数据拉取/上下文组装/写操作预检与执行）
- `app/api/agent.py` — `/agent/chat`、`/agent/confirm`、`/agent/status`、`/agent/sessions`

后端修改：

- `app/config.py` — 新增智能体配置项
- `app/main.py` — 注册 agent 路由
- `app/init_data.py` — 新增 `agent01` 测试学生、周末课表、可选课程、常开选课窗口

前端新增：

- `student-management-frontend/src/api/agent.js`
- `student-management-frontend/src/stores/agent.js`
- `student-management-frontend/src/views/Agent.vue`

前端修改：

- `student-management-frontend/src/router/index.js` — `/` 默认 Agent 页
- `student-management-frontend/src/components/AppNavbar.vue` — 侧边栏加"AI 助手"
- `student-management-frontend/src/views/Login.vue` — 登录后默认跳 `/`

测试新增：`tests/test_agent_confirmations.py`、`tests/test_agent_session.py`、`tests/test_agent_llm.py`、`tests/test_agent_intent.py`、`tests/test_agent_actions.py`、`tests/test_agent_api.py`、`tests/test_agent_seed.py`

---

## Task 1: 智能体配置项

**Files:**
- Modify: `app/config.py`（在 `debug_sql` 之后追加）
- Modify: `.env.example`、`.env`（追加注释与默认值）

- [ ] **Step 1: 修改 `app/config.py`，追加配置项**

```python
    # ===== 智能体助手配置 =====
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: float = 10.0
    ollama_max_concurrency: int = 4
    ollama_queue_timeout: float = 15.0
    ollama_circuit_failures: int = 3
    ollama_circuit_cooldown: float = 60.0
    agent_confirm_ttl: int = 300
    agent_session_ttl: int = 1800
    agent_session_limit: int = 20
    context_budget_tokens: int = 8000
```

- [ ] **Step 2: 修改 `.env.example` 与 `.env`，追加**

```ini
# ===== 智能体助手（Ollama 本地模型）=====
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=10
OLLAMA_MAX_CONCURRENCY=4
AGENT_CONFIRM_TTL=300
AGENT_SESSION_TTL=1800
AGENT_SESSION_LIMIT=20
CONTEXT_BUDGET_TOKENS=8000
```

- [ ] **Step 3: 验证配置可加载**

Run: `.venv\Scripts\python.exe -c "from app.config import settings; print(settings.ollama_model, settings.context_budget_tokens)"`
Expected: `qwen2.5:7b 8000`

- [ ] **Step 4: Commit**

```bash
git add app/config.py .env.example .env
git commit -m "feat(agent): add ollama and agent session config"
```

---

## Task 2: 消息模型与确认令牌

**Files:**
- Create: `app/services/agent/__init__.py`
- Create: `app/services/agent/confirmations.py`
- Test: `tests/test_agent_confirmations.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_confirmations.py`**

```python
"""确认令牌：创建、消费（一次性）、过期、跨用户隔离"""
import time
import pytest
from app.services.agent.confirmations import ConfirmationStore


def test_create_and_consume_once():
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll", "schedule_id": 5})
    payload = store.consume("S2024001", token)
    assert payload == {"action": "enroll", "schedule_id": 5}
    # 一次性：再次消费返回 None
    assert store.consume("S2024001", token) is None


def test_wrong_user_cannot_consume():
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll"})
    assert store.consume("S2024002", token) is None
    assert store.consume("S2024001", token) is not None


def test_expired_token(monkeypatch):
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll"})
    monkeypatch.setattr(store, "_now", lambda: time.time() + 301)
    assert store.consume("S2024001", token) is None


def test_unknown_token():
    store = ConfirmationStore(ttl=300)
    assert store.consume("S2024001", "nope") is None
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_confirmations.py -v`
Expected: FAIL（`ModuleNotFoundError: app.services.agent.confirmations`）

- [ ] **Step 3: 创建 `app/services/agent/__init__.py`**

```python
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
```

- [ ] **Step 4: 创建 `app/services/agent/confirmations.py`**

```python
"""一次性确认令牌：写操作执行前必须经用户确认。"""
import time
import uuid
from typing import Any


class ConfirmationStore:
    def __init__(self, ttl: int = 300):
        self._ttl = ttl
        self._items: dict[str, dict[str, Any]] = {}

    def _now(self) -> float:
        return time.time()

    def create(self, user_id: str, payload: dict[str, Any]) -> str:
        token = uuid.uuid4().hex
        self._items[token] = {
            "user_id": user_id,
            "payload": payload,
            "expires_at": self._now() + self._ttl,
        }
        return token

    def consume(self, user_id: str, token: str) -> dict[str, Any] | None:
        item = self._items.pop(token, None)
        if not item:
            return None
        if item["user_id"] != user_id:
            return None
        if self._now() > item["expires_at"]:
            return None
        return item["payload"]
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_confirmations.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/services/agent tests/test_agent_confirmations.py
git commit -m "feat(agent): add message protocol and one-shot confirmation store"
```

---

## Task 3: 会话记忆（多窗口 + 上下文预算）

**Files:**
- Create: `app/services/agent/session.py`
- Test: `tests/test_agent_session.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_session.py`**

```python
"""会话记忆：多窗口隔离、LRU 上限、TTL、上下文预算裁剪、事实表。"""
import time
import pytest
from app.services.agent.session import SessionStore


def test_create_get_ownership():
    store = SessionStore()
    sess = store.create("S2024001")
    assert store.get("S2024001", sess["session_id"]) is not None
    assert store.get("S2024002", sess["session_id"]) is None


def test_list_and_delete():
    store = SessionStore()
    a = store.create("u1")
    b = store.create("u1")
    assert len(store.list_sessions("u1")) == 2
    assert store.delete("u1", a["session_id"]) is True
    assert store.delete("u2", b["session_id"]) is False
    assert len(store.list_sessions("u1")) == 1


def test_lru_eviction():
    store = SessionStore(max_sessions=2)
    a = store.create("u1")
    store.create("u1")
    c = store.create("u1")
    assert store.get("u1", a["session_id"]) is None
    assert store.get("u1", c["session_id"]) is not None


def test_ttl_expiry(monkeypatch):
    store = SessionStore(ttl=30)
    sess = store.create("u1")
    monkeypatch.setattr(store, "_now", lambda: time.time() + 31)
    assert store.get("u1", sess["session_id"]) is None


def test_context_budget_trims_oldest():
    store = SessionStore(max_messages=10)
    sess = store.create("u1")
    store.add_message("u1", sess["session_id"], "user", "A" * 100)
    store.add_message("u1", sess["session_id"], "assistant", "B" * 100)
    ctx = store.build_context("u1", sess["session_id"], budget_tokens=50)
    assert all(m["content"] in ("A" * 100, "B" * 100) for m in ctx)
    assert len(ctx) == 1  # 预算只能装下最后一条


def test_facts_included_in_context():
    store = SessionStore()
    sess = store.create("u1")
    store.add_fact("u1", sess["session_id"], "已选课：高等数学")
    ctx = store.build_context("u1", sess["session_id"], budget_tokens=8000)
    assert "高等数学" in ctx[0]["content"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_session.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 创建 `app/services/agent/session.py`**

```python
"""多会话记忆：每个窗口独立历史 + 事实表，带 LRU/TTL 与上下文预算裁剪。"""
import time
import uuid
from typing import Any


class SessionStore:
    def __init__(self, ttl: int = 1800, max_sessions: int = 20, max_messages: int = 20):
        self.ttl = ttl
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self._sessions: dict[str, dict[str, Any]] = {}

    def _now(self) -> float:
        return time.time()

    def create(self, user_id: str) -> dict[str, Any]:
        now = self._now()
        session = {
            "session_id": uuid.uuid4().hex,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "facts": [],
        }
        self._sessions[session["session_id"]] = session
        self._evict(user_id)
        return session

    def get(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return None
        if self._now() - session["updated_at"] > self.ttl:
            self._sessions.pop(session_id, None)
            return None
        session["updated_at"] = self._now()
        return session

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {
                "session_id": s["session_id"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
                "message_count": len(s["messages"]),
            }
            for s in self._sessions.values()
            if s["user_id"] == user_id
        ]

    def delete(self, user_id: str, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return False
        self._sessions.pop(session_id, None)
        return True

    def add_message(self, user_id: str, session_id: str, role: str, content: str, kind: str = "text") -> None:
        session = self.get(user_id, session_id)
        if not session:
            return
        session["messages"].append({"role": role, "content": content, "kind": kind, "ts": self._now()})
        if len(session["messages"]) > self.max_messages:
            session["messages"] = session["messages"][-self.max_messages:]

    def add_fact(self, user_id: str, session_id: str, fact: str) -> None:
        session = self.get(user_id, session_id)
        if not session:
            return
        if fact not in session["facts"]:
            session["facts"].append(fact)

    def build_context(self, user_id: str, session_id: str, budget_tokens: int = 8000) -> list[dict[str, str]]:
        """按优先级组装：事实表优先，历史从最新往前装，超预算丢弃最旧。"""
        session = self.get(user_id, session_id)
        if not session:
            return []
        parts: list[dict[str, str]] = []
        if session["facts"]:
            parts.append({"role": "system", "content": "对话内已发生的动作事实：" + "；".join(session["facts"])})
        used = sum(self.estimate_tokens(p["content"]) for p in parts)
        for msg in reversed(session["messages"]):
            cost = self.estimate_tokens(msg["content"])
            if used + cost > budget_tokens:
                break
            parts.append({"role": msg["role"], "content": msg["content"]})
            used += cost
        return parts

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """简易估算：中文字符×0.7 + 其他单词数。"""
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        other = len(text.split())
        return max(1, int(cjk * 0.7 + other))

    def _evict(self, user_id: str) -> None:
        user_sessions = [s for s in self._sessions.values() if s["user_id"] == user_id]
        if len(user_sessions) <= self.max_sessions:
            return
        user_sessions.sort(key=lambda s: s["updated_at"])
        for old in user_sessions[: len(user_sessions) - self.max_sessions]:
            self._sessions.pop(old["session_id"], None)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_session.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/agent/session.py tests/test_agent_session.py
git commit -m "feat(agent): add multi-session memory with context budget"
```

---

## Task 4: Ollama 客户端（超时/并发/熔断）

**Files:**
- Create: `app/services/agent/llm.py`
- Test: `tests/test_agent_llm.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_llm.py`**

```python
"""Ollama 客户端：chat、extract_json、超时、并发繁忙、熔断。"""
import asyncio
import json

import httpx
import pytest

from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable


def _client(responses):
    if isinstance(responses, dict):
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
    client = _client(httpx.ConnectTimeout("boom"))
    for _ in range(3):
        with pytest.raises(OllamaTimeout):
            await client.chat([{"role": "user", "content": "x"}])
    assert client.status() == "unavailable"
    with pytest.raises(OllamaUnavailable):
        await client.chat([{"role": "user", "content": "x"}])
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_llm.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 创建 `app/services/agent/llm.py`**

```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_llm.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/agent/llm.py tests/test_agent_llm.py
git commit -m "feat(agent): add ollama client with timeout, concurrency and circuit breaker"
```

---

## Task 5: 意图识别（LLM 优先 + 规则兜底 + 缓存）

**Files:**
- Create: `app/services/agent/intent.py`
- Test: `tests/test_agent_intent.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_intent.py`**

```python
"""意图识别：规则匹配、LLM 优先、降级、缓存。"""
import pytest

from app.services.agent.intent import IntentResolver, IntentType, match_rules
from app.services.agent.llm import OllamaUnavailable


class FakeLLM:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    async def extract_json(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def test_rules_navigate():
    intent = match_rules("打开选课页面")
    assert intent is not None
    assert intent.intent == IntentType.navigate
    assert intent.params["page"] == "/selection"


def test_rules_query_schedule():
    intent = match_rules("明天上什么课")
    assert intent.intent == IntentType.query_schedule
    assert intent.need_confirm is False


def test_rules_enroll_is_write():
    intent = match_rules("帮我选高等数学")
    assert intent.intent == IntentType.enroll
    assert intent.need_confirm is True


def test_rules_drop_beats_enroll():
    intent = match_rules("我想退选高等数学")
    assert intent.intent == IntentType.drop
    assert intent.need_confirm is True


@pytest.mark.asyncio
async def test_resolver_llm_first():
    llm = FakeLLM(result={"intents": [{"intent": "study_plan", "params": {}, "confidence": 0.9}]})
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("给明天学习方案")
    assert source == "llm"
    assert intents[0].intent == IntentType.study_plan


@pytest.mark.asyncio
async def test_resolver_falls_back_to_rules():
    llm = FakeLLM(error=OllamaUnavailable("down"))
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("明天上什么课")
    assert source == "rules"
    assert intents[0].intent == IntentType.query_schedule


@pytest.mark.asyncio
async def test_resolver_chat_fallback():
    llm = FakeLLM(error=OllamaUnavailable("down"))
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("今天天气怎么样")
    assert source == "fallback"
    assert intents[0].intent == IntentType.chat


@pytest.mark.asyncio
async def test_resolver_cache():
    llm = FakeLLM(result={"intents": [{"intent": "chat", "params": {}, "confidence": 0.5}]})
    resolver = IntentResolver(llm)
    await resolver.resolve("你好呀")
    await resolver.resolve("你好呀")
    assert llm.calls == 1
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_intent.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 创建 `app/services/agent/intent.py`**

```python
"""意图识别：LLM 优先（JSON 抽取，失败重试一次），规则引擎兜底，短 TTL 缓存。"""
import re
import time
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable


class IntentType(str, Enum):
    navigate = "navigate"
    query_schedule = "query_schedule"
    study_plan = "study_plan"
    enroll = "enroll"
    drop = "drop"
    query_classroom = "query_classroom"
    reserve_classroom = "reserve_classroom"
    repair_submit = "repair_submit"
    leave_apply = "leave_apply"
    chat = "chat"


WRITE_INTENTS = frozenset({
    IntentType.enroll, IntentType.drop, IntentType.reserve_classroom,
    IntentType.repair_submit, IntentType.leave_apply,
})


class Intent(BaseModel):
    intent: IntentType
    params: dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    need_confirm: bool = False


PAGE_KEYWORDS = {
    "选课": "/selection", "课表": "/schedule", "成绩": "/scores", "教室": "/classrooms",
    "报修": "/repairs", "请假": "/leaves", "通知": "/notifications", "个人中心": "/profile",
    "培养方案": "/plan", "考试": "/my-exams", "首页": "/dashboard", "管理后台": "/admin",
}

RULE_TABLE: list[tuple[IntentType, list[str], str | None]] = [
    (IntentType.study_plan, ["学习方案", "学习计划", "怎么学", "复习计划"], None),
    (IntentType.query_schedule, ["上什么课", "课程安排", "课表"], None),
    (IntentType.query_classroom, ["空教室", "教室可用", "查教室"], None),
    (IntentType.reserve_classroom, ["预约教室", "借教室", "订教室", "申请教室"], None),
    (IntentType.drop, ["退课", "退选", "不上了"], r"(?:退课|退选)\s*([^\s，。,.！!？?]+)"),
    (IntentType.enroll, ["选课", "选这门", "报名", "选修", "帮我选", "要选"], r"(?:选|报)(?:修|名)?\s*([^\s，。,.！!？?]+)"),
    (IntentType.repair_submit, ["报修", "修一下", "后勤", "东西坏了"], None),
    (IntentType.leave_apply, ["请假", "休假申请"], None),
]


def match_rules(text: str) -> "Intent | None":
    """页面词优先（跳转），其次按规则表顺序匹配；返回单个意图。"""
    lowered = text.strip()
    for page_word, path in PAGE_KEYWORDS.items():
        if page_word in lowered:
            return Intent(intent=IntentType.navigate, params={"page": path}, confidence=0.9, need_confirm=False)
    for intent, keywords, pattern in RULE_TABLE:
        for kw in keywords:
            if kw in lowered:
                params: dict[str, str] = {}
                if pattern:
                    m = re.search(pattern, lowered)
                    if m:
                        params["course"] = m.group(1).strip()
                return Intent(intent=intent, params=params, confidence=0.85, need_confirm=intent in WRITE_INTENTS)
    return None


EXTRACT_SYSTEM_PROMPT = (
    "你是教务智能体的意图识别器。把用户指令解析为有序意图列表（JSON）。"
    "可选意图：navigate(跳转页面,params.page)、query_schedule(查课表)、study_plan(学习方案)、"
    "enroll(选课,params.course)、drop(退课,params.course)、query_classroom(查空教室)、"
    "reserve_classroom(预约教室)、repair_submit(报修)、leave_apply(请假)、chat(闲聊/其他)。"
    '输出格式：{"intents":[{"intent":"...","params":{...},"confidence":0.9}]}。'
    "只输出 JSON，不要多余文字。"
)


class IntentResolver:
    def __init__(self, llm: OllamaClient, cache_size: int = 200, cache_ttl: float = 300.0):
        self.llm = llm
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, list[Intent]]] = {}

    async def resolve(self, text: str) -> tuple[list[Intent], str]:
        now = time.time()
        cached = self._cache.get(text)
        if cached and now - cached[0] <= self.cache_ttl:
            return cached[1], "cache"

        for _ in range(2):  # JSON 解析失败重试一次
            try:
                data = await self.llm.extract_json([
                    {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ])
                intents = self._parse_llm(data)
                if intents:
                    self._put(text, intents, now)
                    return intents, "llm"
            except (OllamaUnavailable, OllamaTimeout, OllamaBusy):
                break  # 服务问题不重试
            except (ValueError, ValidationError):
                continue

        rule = match_rules(text)
        if rule:
            intents = [rule]
            self._put(text, intents, now)
            return intents, "rules"
        return [Intent(intent=IntentType.chat, confidence=0.3)], "fallback"

    def _parse_llm(self, data: dict) -> list[Intent]:
        raw = data.get("intents") or []
        intents = []
        for item in raw:
            intent = Intent(**item)
            intent.need_confirm = intent.intent in WRITE_INTENTS
            intents.append(intent)
        return intents

    def _put(self, text: str, intents: list[Intent], now: float) -> None:
        if len(self._cache) >= self.cache_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            self._cache.pop(oldest, None)
        self._cache[text] = (now, intents)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_intent.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/agent/intent.py tests/test_agent_intent.py
git commit -m "feat(agent): add llm-first intent resolver with rule fallback"
```

---

## Task 6: 动作执行器（权限/数据/写操作预检与确认执行）

**Files:**
- Create: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_actions.py`**

```python
"""动作执行器：权限、课表查询、学习方案降级、选课预检与确认执行、退课。"""
from datetime import date, timedelta

import pytest

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Student, StudentClass,
    Subject, SubjectType, SystemConfig, Teacher,
)
from app.services.agent.actions import ActionExecutor, _tomorrow_weekday
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import Intent, IntentType
from app.services.agent.llm import OllamaUnavailable
from app.services.agent.session import SessionStore


class FakeLLM:
    def __init__(self):
        self.replies = []

    async def chat(self, messages):
        return "模型回复"

    async def extract_json(self, messages):
        raise OllamaUnavailable("down")  # 强制学习方案走模板降级


async def _seed(db):
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机科学与技术", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Subject(id=2, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="教学楼D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=2, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=_tomorrow_weekday(), period="5-6", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=0, capacity=30))
    await db.commit()


def _executor():
    return ActionExecutor(FakeLLM(), ConfirmationStore(), SessionStore())


@pytest.mark.asyncio
async def test_permission_student_only(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_schedule), "T10001", "teacher", "s", db
    )
    assert msgs[0].kind == "error"


@pytest.mark.asyncio
async def test_enroll_confirmation_then_execute(db):
    await _seed(db)
    executor = _executor()
    intent = Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True)
    msgs = await executor.execute(intent, "S2024001", "student", "sess1", db)
    assert msgs[0].kind == "confirmation"
    token = msgs[0].confirm_token
    results = await executor.execute_confirm(
        executor.confirmations.consume("S2024001", token), db
    )
    assert results[0].kind == "card"
    cap = (await db.execute(
        __import__("sqlalchemy").select(CourseCapacity).where(CourseCapacity.schedule_id == 1)
    )).scalar_one()
    assert cap.enrolled == 1


@pytest.mark.asyncio
async def test_enroll_full_fails(db):
    await _seed(db)
    executor = _executor()
    cap = (await db.execute(
        __import__("sqlalchemy").select(CourseCapacity).where(CourseCapacity.schedule_id == 1)
    )).scalar_one()
    cap.enrolled = cap.capacity
    await db.commit()
    msgs = await executor.execute(
        Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True),
        "S2024001", "student", "sess1", db,
    )
    assert msgs[0].kind == "error"
    assert "已满" in msgs[0].content


@pytest.mark.asyncio
async def test_conflict_detected(db):
    await _seed(db)
    db.add(Schedule(
        id=99, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=_tomorrow_weekday(), period="5-6", semester="2024-2025-1",
    ))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True),
        "S2024001", "student", "sess1", db,
    )
    assert msgs[0].kind == "error"
    assert "冲突" in msgs[0].content


@pytest.mark.asyncio
async def test_study_plan_template_fallback(db):
    await _seed(db)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.study_plan), "S2024001", "student", "sess1", db
    )
    assert msgs[0].kind == "card"
    assert "人工智能实战" in msgs[0].content


@pytest.mark.asyncio
async def test_query_schedule_tomorrow(db):
    await _seed(db)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_schedule), "S2024001", "student", "sess1", db
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["courses"][0]["course"] == "人工智能实战"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 创建 `app/services/agent/actions.py`**

```python
"""动作执行器：权限复核 → 数据拉取 → 上下文组装 → 写操作预检与确认执行。"""
import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Student, Subject, SystemConfig, Teacher,
)
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import Intent, IntentType
from app.services.agent.llm import OllamaClient
from app.services.agent.session import SessionStore

logger = logging.getLogger("student_management")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

STUDENT_ONLY = frozenset({IntentType.query_schedule, IntentType.study_plan, IntentType.enroll, IntentType.drop})
NOT_FOR_ADMIN = frozenset({IntentType.reserve_classroom, IntentType.repair_submit, IntentType.leave_apply})


def _allowed(intent: IntentType, role: str) -> bool:
    if intent in STUDENT_ONLY and role != "student":
        return False
    if intent in NOT_FOR_ADMIN and role == "admin":
        return False
    return True


def _period_range(period: str) -> tuple[int, int]:
    parts = period.split("-")
    return int(parts[0]), int(parts[-1])


def _periods_overlap(a: str, b: str) -> bool:
    a1, a2 = _period_range(a)
    b1, b2 = _period_range(b)
    return max(a1, b1) <= min(a2, b2)


def _weeks_overlap(a: str, b: str) -> bool:
    def rng(s: str) -> tuple[int, int]:
        s = s.strip()
        if "-" in s:
            x, y = s.split("-", 1)
            return int(x), int(y)
        return int(s), int(s)

    a1, a2 = rng(a)
    b1, b2 = rng(b)
    return max(a1, b1) <= min(a2, b2)


def _tomorrow_weekday() -> int:
    return (date.today() + timedelta(days=1)).isoweekday()


class ActionExecutor:
    def __init__(self, llm: OllamaClient, confirmations: ConfirmationStore, sessions: SessionStore):
        self.llm = llm
        self.confirmations = confirmations
        self.sessions = sessions

    async def execute(self, intent: Intent, user_id: str, role: str, session_id: str, db: AsyncSession, raw_text: str = "") -> list:
        from app.services.agent import AgentMessage

        if not _allowed(intent.intent, role):
            return [AgentMessage(kind="error", title="业务失败", content="无权限执行该操作")]
        if intent.intent == IntentType.chat:
            return await self._handle_chat(user_id, session_id, raw_text)
        handler = getattr(self, f"_handle_{intent.intent.value}", None)
        if handler is None:
            return await self._handle_navigate(
                Intent(intent=IntentType.navigate, params={"page": "/"}), user_id, role, session_id, db
            )
        return await handler(intent, user_id, role, session_id, db)

    async def _handle_navigate(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        page = intent.params.get("page") or "/"
        return [AgentMessage(kind="card", title="页面跳转", content=f"正在前往：{page}", navigation=page)]

    async def _handle_query_schedule(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        courses = await self._tomorrow_schedule(user_id, db)
        if not courses:
            return [AgentMessage(kind="card", title="明天的课表", content="明天没有课", data={"courses": []})]
        return [AgentMessage(kind="card", title="明天的课表", content=f"明天共 {len(courses)} 节课", data={"courses": courses})]

    async def _handle_study_plan(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        courses = await self._tomorrow_schedule(user_id, db)
        if not courses:
            return [AgentMessage(kind="card", title="学习方案", content="明天没有课，可以自主安排学习或休息", data={"courses": []})]
        plan_text = await self._generate_plan(courses)
        return [AgentMessage(kind="card", title="明天的学习方案", content=plan_text, data={"courses": courses})]

    async def _handle_chat(self, user_id, session_id, raw_text):
        from app.services.agent import AgentMessage

        context = self.sessions.build_context(user_id, session_id)
        context.append({"role": "user", "content": raw_text or "你好"})
        reply = await self.llm.chat(context)
        return [AgentMessage(kind="text", content=reply)]

    async def _handle_enroll(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        schedule_id = await self._resolve_schedule_id(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            return [AgentMessage(kind="error", title="业务失败", content="没找到要选的课程，请说完整的课程名")]
        ok, reason, info = await self._precheck_enroll(user_id, schedule_id, db)
        if not ok:
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        token = self.confirmations.create(user_id, {
            "action": "enroll", "schedule_id": schedule_id, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(kind="confirmation", title="确认选课", content=reason, data=info, confirm_token=token)]

    async def _handle_drop(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        schedule_id = await self._resolve_schedule_id(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            return [AgentMessage(kind="error", title="业务失败", content="没找到要退的课程")]
        row = (await db.execute(
            select(CourseSelection, Schedule, Subject)
            .join(Schedule, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                CourseSelection.student_id == user_id,
                CourseSelection.schedule_id == schedule_id,
                CourseSelection.status == 1,
            )
        )).one_or_none()
        if not row:
            return [AgentMessage(kind="error", title="业务失败", content="未选该课程，无法退课")]
        token = self.confirmations.create(user_id, {
            "action": "drop", "schedule_id": schedule_id, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(kind="confirmation", title="确认退课", content=f"确认退掉课程：{row[2].name}", data={"course": row[2].name}, confirm_token=token)]

    async def _handle_query_classroom(self, intent, user_id, role, session_id, db):
        return await self._handle_navigate(Intent(intent=IntentType.navigate, params={"page": "/classrooms"}), user_id, role, session_id, db)

    async def _handle_reserve_classroom(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(kind="card", title="教室预约", content="教室预约功能下一期接入，先为你打开教室页面", navigation="/classrooms")]

    async def _handle_repair_submit(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(kind="card", title="报修", content="报修功能下一期接入，先为你打开报修页面", navigation="/repairs")]

    async def _handle_leave_apply(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(kind="card", title="请假", content="请假功能下一期接入，先为你打开请假页面", navigation="/leaves")]

    async def execute_confirm(self, payload: dict, db: AsyncSession) -> list:
        from app.services.agent import AgentMessage

        if not payload:
            return [AgentMessage(kind="error", content="确认已过期或不存在，请重新发起")]
        action = payload.get("action")
        user_id = payload["user_id"]
        session_id = payload.get("session_id", "")
        if action == "enroll":
            schedule_id = int(payload["schedule_id"])
            ok, reason, info = await self._precheck_enroll(user_id, schedule_id, db)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                cap = await db.execute(text(
                    "UPDATE course_capacity SET enrolled = enrolled + 1 "
                    "WHERE schedule_id = :sid AND enrolled < capacity"
                ), {"sid": schedule_id})
                if cap.rowcount == 0:
                    await db.rollback()
                    return [AgentMessage(kind="error", title="业务失败", content="课程已满")]
                db.add(CourseSelection(student_id=user_id, schedule_id=schedule_id, status=1))
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("agent enroll failed")
                return [AgentMessage(kind="error", title="系统异常", content="选课失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已选课：{info.get('course', schedule_id)}")
            return [AgentMessage(kind="card", title="选课成功", content=f"已成功选课：{info.get('course')}", data=info)]
        if action == "drop":
            schedule_id = int(payload["schedule_id"])
            try:
                upd = await db.execute(text(
                    "UPDATE course_selection SET status = 0, cancel_time = :now "
                    "WHERE student_id = :sid AND schedule_id = :schid AND status = 1"
                ), {"sid": user_id, "schid": schedule_id, "now": datetime.now()})
                if upd.rowcount == 0:
                    await db.rollback()
                    return [AgentMessage(kind="error", title="业务失败", content="该课程已退选")]
                await db.execute(text(
                    "UPDATE course_capacity SET enrolled = enrolled - 1 "
                    "WHERE schedule_id = :schid AND enrolled > 0"
                ), {"schid": schedule_id})
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("agent drop failed")
                return [AgentMessage(kind="error", title="系统异常", content="退课失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已退课：{schedule_id}")
            return [AgentMessage(kind="card", title="退课成功", content="退课成功")]
        return [AgentMessage(kind="error", content="未知的确认动作")]

    async def _resolve_schedule_id(self, course: str, student_id: str, db) -> int | None:
        if course.isdigit():
            return int(course)
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        if not stu or not stu.class_id:
            return None
        rows = (await db.execute(
            select(Schedule.id, Subject.name)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Schedule.class_id == stu.class_id)
        )).all()
        for sid, name in rows:
            if course in name:
                return sid
        return None

    async def _selection_window(self, db) -> tuple[bool, str]:
        configs = {
            c.config_key: c.config_value
            for c in (await db.execute(
                select(SystemConfig).where(SystemConfig.config_key.in_(["selection_start_time", "selection_end_time"]))
            )).scalars().all()
        }
        start_str = configs.get("selection_start_time")
        end_str = configs.get("selection_end_time")
        if not start_str or not end_str:
            return True, ""
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False, "选课时间配置错误"
        now = datetime.now()
        if now < start:
            return False, "选课尚未开放"
        if now > end:
            return False, "选课已结束"
        return True, ""

    async def _precheck_enroll(self, student_id: str, schedule_id: int, db) -> tuple[bool, str, dict]:
        row = (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(Schedule.id == schedule_id)
        )).one_or_none()
        if not row:
            return False, "课表记录不存在", {}
        schedule, subject, teacher, classroom = row
        if subject.type.value == "compulsory":
            return False, "必修课无需选课", {}
        window_ok, window_msg = await self._selection_window(db)
        if not window_ok:
            return False, window_msg, {}
        dup = (await db.execute(select(CourseSelection).where(
            CourseSelection.student_id == student_id,
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        ))).scalar_one_or_none()
        if dup:
            return False, "该课程已选，请勿重复", {}
        cap = (await db.execute(select(CourseCapacity).where(CourseCapacity.schedule_id == schedule_id))).scalar_one_or_none()
        if not cap or cap.enrolled >= cap.capacity:
            return False, "课程已满", {}
        if await self._has_conflict(student_id, schedule, db):
            return False, "与已有课表时间冲突", {}
        info = {
            "course": subject.name, "teacher": teacher.name, "classroom": classroom.name,
            "day": WEEKDAY_CN[schedule.day_of_week - 1], "period": schedule.period,
            "weeks": schedule.weeks, "credit": float(subject.credit),
            "enrolled": cap.enrolled, "capacity": cap.capacity,
        }
        return True, "预检通过，确认后执行选课", info

    async def _has_conflict(self, student_id: str, target: Schedule, db) -> bool:
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        rows = []
        if stu and stu.class_id:
            rows.extend((await db.execute(
                select(Schedule).where(Schedule.class_id == stu.class_id, Schedule.semester == target.semester)
            )).scalars().all())
        rows.extend((await db.execute(
            select(Schedule).join(CourseSelection, CourseSelection.schedule_id == Schedule.id)
            .where(CourseSelection.student_id == student_id, CourseSelection.status == 1)
        )).scalars().all())
        seen: set[int] = set()
        for s in rows:
            if s.id == target.id or s.id in seen:
                continue
            seen.add(s.id)
            if s.day_of_week == target.day_of_week and _periods_overlap(s.period, target.period) and _weeks_overlap(s.weeks, target.weeks):
                return True
        return False

    async def _tomorrow_schedule(self, student_id: str, db) -> list[dict]:
        target = _tomorrow_weekday()
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        if not stu or not stu.class_id:
            return []
        courses: list[dict] = []
        for s, subj, t, cr in (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(Schedule.class_id == stu.class_id, Schedule.day_of_week == target)
        )).all():
            courses.append(self._course_dict(s, subj, t, cr))
        seen = {c["schedule_id"] for c in courses}
        for s, subj, t, cr in (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(CourseSelection, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(CourseSelection.student_id == student_id, CourseSelection.status == 1, Schedule.day_of_week == target)
        )).all():
            if s.id not in seen:
                courses.append(self._course_dict(s, subj, t, cr))
        courses.sort(key=lambda c: c["period"])
        return courses

    @staticmethod
    def _course_dict(s, subj, t, cr) -> dict:
        return {
            "schedule_id": s.id, "course": subj.name, "teacher": t.name,
            "classroom": cr.name, "day": WEEKDAY_CN[s.day_of_week - 1],
            "period": s.period, "weeks": s.weeks, "credit": float(subj.credit),
        }

    async def _generate_plan(self, courses: list[dict]) -> str:
        schedule_lines = "\n".join(
            f"- {c['course']}（{c['day']} {c['period']}节，{c['classroom']}，{c['teacher']}）" for c in courses
        )
        prompt = (
            "你是大学生学习规划助手。根据明天的课表生成学习方案，输出 JSON："
            '{"courses":[{"course":"课程名","duration_minutes":60,"preview":"预习要点","review":"复习要点","priority":"高/中/低"}],"summary":"一句话整体安排"}'
            f"\n明天的课表：\n{schedule_lines}"
        )
        try:
            data = await self.llm.extract_json([
                {"role": "system", "content": "只输出 JSON，不要多余文字。"},
                {"role": "user", "content": prompt},
            ])
            return json.dumps(data, ensure_ascii=False)
        except Exception as exc:  # 模型不可用时降级模板
            logger.warning("study plan fell back to template: %s", exc)
            return self._template_plan(courses)

    @staticmethod
    def _template_plan(courses: list[dict]) -> str:
        lines = [f"明天共 {len(courses)} 节课，建议学习方案："]
        for c in courses:
            lines.append(f"- {c['course']}（{c['period']}节）：课前预习 20 分钟，课后复习 40 分钟，整理课堂笔记。")
        lines.append("整体安排：优先完成作业与复习，睡前快速回顾明天的课程要点。")
        return "\n".join(lines)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/agent/actions.py tests/test_agent_actions.py
git commit -m "feat(agent): add action executor with permissions and confirm flow"
```

---

## Task 7: API 路由与注册

**Files:**
- Create: `app/api/agent.py`
- Modify: `app/main.py`
- Test: `tests/test_agent_api.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_api.py`**

```python
"""智能体 API：chat、confirm、status、sessions。"""
import pytest

from app.models import (
    Classroom, CourseCapacity, Schedule, Student, StudentClass, Subject, SubjectType,
    SystemConfig, Teacher,
)
from app.services.agent.llm import OllamaUnavailable


class FakeLLM:
    async def extract_json(self, messages):
        raise OllamaUnavailable("down")

    async def chat(self, messages):
        return "模型回复"

    def status(self):
        return "ok"


async def _seed_agent_data(db):
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=2, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=2, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=5, period="5-6", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=0, capacity=30))
    await db.commit()


@pytest.fixture
def auth_override():
    from app.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "S2024001", "role": "student", "role_id": "S2024001",
    }
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def fake_llm(monkeypatch):
    from app.api import agent as agent_api

    fake = FakeLLM()
    monkeypatch.setattr(agent_api, "agent_llm", fake)
    monkeypatch.setattr(agent_api.resolver, "llm", fake)
    monkeypatch.setattr(agent_api.executor, "llm", fake)
    return fake


@pytest.mark.asyncio
async def test_chat_enroll_confirmation(client, db, auth_override, fake_llm):
    await _seed_agent_data(db)
    resp = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"]
    kinds = [m["kind"] for m in data["messages"]]
    assert "confirmation" in kinds
    assert "summary" in kinds


@pytest.mark.asyncio
async def test_confirm_executes_enroll(client, db, auth_override, fake_llm):
    await _seed_agent_data(db)
    resp = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
    token = next(m["confirm_token"] for m in resp.json()["messages"] if m["kind"] == "confirmation")
    resp2 = await client.post("/agent/confirm", json={"token": token})
    assert resp2.status_code == 200
    assert resp2.json()["messages"][0]["kind"] == "card"


@pytest.mark.asyncio
async def test_confirm_expired_token(client, auth_override, fake_llm):
    resp = await client.post("/agent/confirm", json={"token": "not-a-token"})
    assert resp.status_code == 200
    assert resp.json()["messages"][0]["kind"] == "error"


@pytest.mark.asyncio
async def test_status_and_sessions(client, auth_override, fake_llm):
    status = await client.get("/agent/status")
    assert status.status_code == 200
    assert status.json()["ollama"] == "ok"
    resp = await client.get("/agent/sessions")
    assert resp.status_code == 200
    assert "sessions" in resp.json()
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -v`
Expected: FAIL（`ModuleNotFoundError: app.api.agent`）

- [ ] **Step 3: 创建 `app/api/agent.py`**

```python
"""智能体助手路由：/agent/chat、/agent/confirm、/agent/status、/agent/sessions。"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.services.agent import AgentMessage
from app.services.agent.actions import ActionExecutor
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import IntentResolver
from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable
from app.services.agent.session import SessionStore

logger = logging.getLogger("student_management")

agent_llm = OllamaClient(
    base_url=settings.ollama_base_url,
    model=settings.ollama_model,
    timeout=settings.ollama_timeout,
    max_concurrency=settings.ollama_max_concurrency,
    queue_timeout=settings.ollama_queue_timeout,
    circuit_failures=settings.ollama_circuit_failures,
    circuit_cooldown=settings.ollama_circuit_cooldown,
)
resolver = IntentResolver(agent_llm)
session_store = SessionStore(
    ttl=settings.agent_session_ttl,
    max_sessions=settings.agent_session_limit,
)
confirmation_store = ConfirmationStore(ttl=settings.agent_confirm_ttl)
executor = ActionExecutor(agent_llm, confirmation_store, session_store)

router = APIRouter(prefix="/agent", tags=["智能体助手"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class ConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)


@router.post("/chat", summary="发送消息给智能体")
async def agent_chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user["username"]
    role = current_user["role"]
    if req.session_id:
        if not session_store.get(user_id, req.session_id):
            return {
                "session_id": req.session_id,
                "messages": [AgentMessage(kind="error", content="会话不存在或已过期，请新建对话")],
                "source": "none",
            }
        session_id = req.session_id
    else:
        session_id = session_store.create(user_id)["session_id"]

    session_store.add_message(user_id, session_id, "user", req.message)
    try:
        intents, source = await resolver.resolve(req.message)
    except Exception:
        logger.exception("intent resolution failed")
        intents, source = [], "fallback"

    messages: list[AgentMessage] = []
    success = failed = skipped = 0
    interrupted = False
    for intent in intents:
        try:
            outcome = await executor.execute(intent, user_id, role, session_id, db, raw_text=req.message)
        except (OllamaBusy, OllamaUnavailable) as exc:
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content=str(exc)))
            break
        except OllamaTimeout:
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content="模型响应超时，请稍后再试"))
            break
        except Exception:
            logger.exception("agent action failed")
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content="系统异常，请稍后重试"))
            break
        if not outcome:
            skipped += 1
            continue
        messages.extend(outcome)
        if any(m.kind == "error" for m in outcome):
            failed += 1
        else:
            success += 1

    summary = AgentMessage(
        kind="summary",
        content=f"共 {len(intents)} 个指令：成功 {success}、业务失败 {failed}、跳过 {skipped}、系统中断 {1 if interrupted else 0}",
    )
    messages.append(summary)
    for m in messages:
        session_store.add_message(user_id, session_id, "assistant", m.content or m.title, kind=m.kind)
    return {"session_id": session_id, "messages": messages, "source": source}


@router.post("/confirm", summary="确认执行写操作")
async def agent_confirm(
    req: ConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = confirmation_store.consume(current_user["username"], req.token)
    messages = await executor.execute_confirm(payload, db)
    return {"messages": messages}


@router.get("/status", summary="智能体与模型状态")
async def agent_status(current_user: dict = Depends(get_current_user)):
    return {
        "ollama": agent_llm.status(),
        "session_count": len(session_store.list_sessions(current_user["username"])),
    }


@router.get("/sessions", summary="会话列表")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    return {"sessions": session_store.list_sessions(current_user["username"])}


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    if not session_store.delete(current_user["username"], session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "已删除"}
```

- [ ] **Step 4: 在 `app/main.py` 注册路由**

把导入行：

```python
from app.api import leave, advisor, training_plan, graduation, notification, internal, profile, exam
```

改为：

```python
from app.api import leave, advisor, training_plan, graduation, notification, internal, profile, exam, agent
```

并在现有 `app.include_router(...)` 块末尾追加：

```python
app.include_router(agent.router)
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/api/agent.py app/main.py tests/test_agent_api.py
git commit -m "feat(agent): add agent API routes and register router"
```

---

## Task 8: 种子数据（agent01 测试账号 + 一周七天有课 + 可选课程 + 常开窗口）

**Files:**
- Modify: `app/init_data.py`
- Modify: `README.md`（测试账号表加 agent01）
- Test: `tests/test_agent_seed.py`

- [ ] **Step 1: 写失败测试 `tests/test_agent_seed.py`**

```python
"""种子数据保证：agent01 一周每天有课；可选课程余量>0、窗口开放、无冲突（预检必过）。"""
import pytest
from sqlalchemy import select

from app.models import (
    Classroom, CourseCapacity, Schedule, Student, StudentClass, Subject, SubjectType,
    SystemConfig, Teacher,
)
from app.services.agent.actions import ActionExecutor
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.session import SessionStore


class FakeLLM:
    async def chat(self, messages):
        return "x"

    async def extract_json(self, messages):
        raise Exception("down")


async def _build_seed(db):
    """构造等价于 init_data.py 中 agent01 的种子：班级1 + 周一~周日各一节课 + 可选课程。"""
    db.add_all([
        StudentClass(id=1, name="2024计算机1班", major="计算机科学与技术", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Subject(id=2, name="大学英语", credit=4.0, type=SubjectType.compulsory),
        Subject(id=11, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Classroom(id=9, name="D401", capacity=120, building="D", has_projector=True),
        Student(id="S2024099", name="智能体测试员", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    elective_id = None
    for dow in range(1, 8):
        db.add(Schedule(
            teacher_id=1, subject_id=1 if dow % 2 else 2, class_id=1, classroom_id=1,
            weeks="1-18", day_of_week=dow, period=f"{dow}-{dow}", semester="2024-2025-1",
        ))
        await db.flush()
    elective = Schedule(
        teacher_id=1, subject_id=11, class_id=1, classroom_id=9,
        weeks="1-18", day_of_week=7, period="9-10", semester="2024-2025-1",
    )
    db.add(elective)
    await db.flush()
    elective_id = elective.id
    db.add(CourseCapacity(schedule_id=elective.id, enrolled=0, capacity=30))
    await db.commit()
    return elective_id


@pytest.mark.asyncio
async def test_agent01_has_class_every_day(db):
    await _build_seed(db)
    days = set((await db.execute(select(Schedule.day_of_week).where(Schedule.class_id == 1))).scalars().all())
    assert days >= set(range(1, 8))


@pytest.mark.asyncio
async def test_agent01_enroll_precheck_passes(db):
    elective_id = await _build_seed(db)
    executor = ActionExecutor(FakeLLM(), ConfirmationStore(), SessionStore())
    ok, reason, info = await executor._precheck_enroll("S2024099", elective_id, db)
    assert ok, reason
    assert info["capacity"] >= 1
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_seed.py -v`
Expected: FAIL（`app.services.agent.actions` 尚不存在，先完成 Task 6 再回跑本测试）

- [ ] **Step 3: 修改 `app/init_data.py`**

在 Step 5 末尾 `db.flush()  # 获取自增 ID，供容量表使用` 之后插入：

```python
        # ===== Step 5.5: 智能体测试数据 —— 周末课表 + 可选课程（agent01 一周每天有课）=====
        weekend_schedules = [
            Schedule(teacher_id=10001, subject_id=1, class_id=1, classroom_id=5,
                     weeks="1-18", day_of_week=6, period="1-2", semester="2024-2025-1"),
            Schedule(teacher_id=10002, subject_id=2, class_id=1, classroom_id=7,
                     weeks="1-18", day_of_week=7, period="3-4", semester="2024-2025-1"),
        ]
        db.add_all(weekend_schedules)
        db.flush()

        agent_ai_subject = Subject(id=11, name="人工智能实战", credit=2.0, type=SubjectType.elective)
        db.add(agent_ai_subject)
        db.flush()

        agent_ai_schedule = Schedule(
            teacher_id=10001, subject_id=11, class_id=1, classroom_id=9,
            weeks="1-18", day_of_week=6, period="5-6", semester="2024-2025-1",
        )
        db.add(agent_ai_schedule)
        db.flush()
        db.add(CourseCapacity(schedule_id=agent_ai_schedule.id, enrolled=0, capacity=30))
```

在 Step 7 学生插入完成后（`db.add_all(students)` 之后）追加：

```python
        # 智能体测试学生：agent01，密码固定 test123456
        db.add(Student(id="S2024099", name="智能体测试员", class_id=1))
```

在 Step 9 凭证循环结束、Step 9.5 之前追加：

```python
        # agent01：智能体测试专用账号，密码固定，首次登录不强制改密
        db.add(UserCredential(
            username="agent01",
            password_hash=hash_password("test123456"),
            role=UserRole.student,
            role_id="S2024099",
            must_change_password=False,
        ))
        credentials.append({"username": "agent01", "password": "test123456", "role": "student"})
```

把 Step 9.5 的 `system_configs` 值改为常开窗口（保证智能体随时可测选课）：

```python
        system_configs = [
            SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
            SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
            SystemConfig(config_key="drop_deadline", config_value="2099-12-31 18:00:00"),
        ]
```

- [ ] **Step 4: 更新 `README.md` 测试账号表**

在测试账号表格中追加一行：

```markdown
| 智能体测试学生 | agent01 | test123456 |
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_seed.py -v`
Expected: 2 passed

- [ ] **Step 6: 手工验证种子（需要 MySQL 已启动，本机端口 3307）**

Run: `.venv\Scripts\python.exe -m app.init_data`
Expected: 输出账号表含 `agent01 / test123456`

- [ ] **Step 7: Commit**

```bash
git add app/init_data.py README.md tests/test_agent_seed.py
git commit -m "feat(agent): seed agent01 test student with weekly schedule and open window"
```

---

## Task 9: 前端 API 封装与 Pinia store

**Files:**
- Create: `student-management-frontend/src/api/agent.js`
- Create: `student-management-frontend/src/stores/agent.js`

- [ ] **Step 1: 创建 `student-management-frontend/src/api/agent.js`**

```js
import request from './index'

export function sendChat(sessionId, message) {
  return request.post('/agent/chat', { session_id: sessionId || null, message })
}

export function confirmAction(token) {
  return request.post('/agent/confirm', { token })
}

export function getAgentStatus() {
  return request.get('/agent/status')
}

export function listSessions() {
  return request.get('/agent/sessions')
}

export function deleteSession(sessionId) {
  return request.delete(`/agent/sessions/${sessionId}`)
}
```

- [ ] **Step 2: 创建 `student-management-frontend/src/stores/agent.js`**

```js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { confirmAction, deleteSession, getAgentStatus, listSessions, sendChat } from '../api/agent'

export const useAgentStore = defineStore('agent', () => {
  const sessions = ref([])
  const currentSessionId = ref('')
  const messages = ref([])
  const sending = ref(false)
  const ollamaStatus = ref('unknown')

  async function loadSessions() {
    const res = await listSessions()
    sessions.value = res.sessions || []
  }

  async function newSession() {
    currentSessionId.value = ''
    messages.value = []
    await loadSessions()
  }

  async function send(text) {
    if (!text.trim() || sending.value) return
    sending.value = true
    messages.value.push({ kind: 'text', content: text, own: true })
    try {
      const res = await sendChat(currentSessionId.value, text.trim())
      currentSessionId.value = res.session_id
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
      await loadSessions()
    } catch {
      messages.value.push({ kind: 'error', content: '请求失败，请检查后端服务', own: false })
    } finally {
      sending.value = false
    }
  }

  async function confirm(token) {
    sending.value = true
    try {
      const res = await confirmAction(token)
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
    } catch {
      messages.value.push({ kind: 'error', content: '确认失败，请重试', own: false })
    } finally {
      sending.value = false
    }
  }

  async function removeSession(id) {
    await deleteSession(id)
    if (currentSessionId.value === id) {
      currentSessionId.value = ''
      messages.value = []
    }
    await loadSessions()
  }

  async function refreshStatus() {
    try {
      const res = await getAgentStatus()
      ollamaStatus.value = res.ollama
    } catch {
      ollamaStatus.value = 'unknown'
    }
  }

  return {
    sessions, currentSessionId, messages, sending, ollamaStatus,
    loadSessions, newSession, send, confirm, removeSession, refreshStatus,
  }
})
```

- [ ] **Step 3: Commit**

```bash
git add student-management-frontend/src/api/agent.js student-management-frontend/src/stores/agent.js
git commit -m "feat(agent): add frontend agent api and store"
```

---

## Task 10: 前端路由（Agent 作为默认主页）

**Files:**
- Modify: `student-management-frontend/src/router/index.js`
- Modify: `student-management-frontend/src/components/AppNavbar.vue`
- Modify: `student-management-frontend/src/views/Login.vue`

- [ ] **Step 1: 修改 `router/index.js`**

在 `{ path: '/dashboard', ... }` 之前插入：

```js
  { path: '/', name: 'Agent', component: () => import('../views/Agent.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
```

删除 `{ path: '/', redirect: '/login' }` 这一行，并把默认页映射改为：

```js
const defaultPages = { student: '/', teacher: '/', staff: '/', admin: '/' }
```

- [ ] **Step 2: 修改 `AppNavbar.vue`**

在 `@element-plus/icons-vue` 的 import 列表中新增 `ChatDotRound`，然后在 `menuItems` computed 内、`const menus = {` 之前加入：

```js
  const agentItem = { path: '/', label: 'AI 助手', icon: ChatDotRound }
```

并把 `return menus[role] || []` 改为：

```js
  for (const key of Object.keys(menus)) {
    menus[key] = [agentItem, ...menus[key]]
  }
  return menus[role] || []
```

把 `mobileTabs` 里的 `defaultPage` 三元表达式改为 `const defaultPage = '/'`。

- [ ] **Step 3: 修改 `Login.vue` 登录后默认跳转**

把 `const defaults = { student: '/schedule', teacher: '/scores/input', staff: '/repairs/manage', admin: '/admin' }` 改为：

```js
const defaults = { student: '/', teacher: '/', staff: '/', admin: '/' }
```

- [ ] **Step 4: 构建验证**

Run（在 `student-management-frontend` 目录）: `npm run build`
Expected: 构建成功（仅 chunk 体积警告）

- [ ] **Step 5: Commit**

```bash
git add student-management-frontend/src/router/index.js student-management-frontend/src/components/AppNavbar.vue student-management-frontend/src/views/Login.vue
git commit -m "feat(agent): make agent page the default home route"
```

---

## Task 11: Agent 对话主页（Agent.vue）

**Files:**
- Create: `student-management-frontend/src/views/Agent.vue`

- [ ] **Step 1: 创建 `student-management-frontend/src/views/Agent.vue`**

```vue
<template>
  <div class="agent-layout">
    <aside class="session-panel">
      <el-button type="primary" class="new-session-btn" @click="store.newSession()">
        新建对话
      </el-button>
      <div class="session-list">
        <div
          v-for="s in store.sessions"
          :key="s.session_id"
          class="session-item"
          :class="{ active: s.session_id === store.currentSessionId }"
          @click="selectSession(s.session_id)"
        >
          <span class="session-title">会话 {{ s.message_count }} 条</span>
          <el-button link type="danger" size="small" @click.stop="store.removeSession(s.session_id)">
            删除
          </el-button>
        </div>
      </div>
    </aside>

    <main class="chat-panel">
      <header class="chat-header">
        <h2>智能体助手</h2>
        <span class="model-status" :class="store.ollamaStatus">
          {{ store.ollamaStatus === 'ok' ? '本地模型在线' : '本地模型未连接' }}
        </span>
      </header>

      <div ref="listRef" class="message-list">
        <template v-for="(m, idx) in store.messages" :key="idx">
          <div v-if="m.own" class="msg own">{{ m.content }}</div>
          <div v-else-if="m.kind === 'text'" class="msg">{{ m.content }}</div>
          <div v-else-if="m.kind === 'error'" class="msg error">{{ m.content }}</div>
          <div v-else-if="m.kind === 'summary'" class="msg summary">{{ m.content }}</div>
          <el-card v-else-if="m.kind === 'card'" class="msg-card">
            <template #header>
              <div class="card-head">
                <span>{{ m.title }}</span>
                <el-button v-if="m.navigation" link type="primary" @click="go(m.navigation)">
                  前往页面
                </el-button>
              </div>
            </template>
            <div class="card-content">
              <pre class="plan-text" v-if="m.data?.courses && isPlan(m)">{{ m.content }}</pre>
              <el-table v-else-if="m.data?.courses" :data="m.data.courses" size="small">
                <el-table-column prop="course" label="课程" />
                <el-table-column prop="period" label="节次" width="80" />
                <el-table-column prop="classroom" label="教室" width="100" />
                <el-table-column prop="teacher" label="老师" width="100" />
              </el-table>
              <pre v-else class="plain">{{ m.content }}</pre>
            </div>
          </el-card>
          <el-card v-else-if="m.kind === 'confirmation'" class="msg-card confirm-card">
            <template #header>{{ m.title }}</template>
            <p>{{ m.content }}</p>
            <p v-if="m.data" class="confirm-info">
              {{ m.data.course }}｜{{ m.data.day }} {{ m.data.period }}节｜{{ m.data.classroom }}
              ｜余量 {{ m.data.enrolled }}/{{ m.data.capacity }}
            </p>
            <div class="confirm-actions">
              <el-button type="primary" :disabled="store.sending" @click="store.confirm(m.confirm_token)">
                确认执行
              </el-button>
              <el-button :disabled="store.sending" @click="cancelMsg(m)">取消</el-button>
            </div>
          </el-card>
        </template>
        <div v-if="store.sending" class="msg typing">智能体思考中…</div>
      </div>

      <div class="quick-prompts">
        <el-tag v-for="p in quickPrompts" :key="p" class="prompt-tag" @click="sendText(p)">
          {{ p }}
        </el-tag>
      </div>

      <footer class="input-bar">
        <el-input
          v-model="input"
          placeholder="输入指令，例如：明天上什么课 / 给明天学习方案 / 帮我选人工智能实战"
          @keyup.enter="sendText(input)"
          :disabled="store.sending"
        />
        <el-button type="primary" :loading="store.sending" @click="sendText(input)">发送</el-button>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent'

const store = useAgentStore()
const router = useRouter()
const input = ref('')
const listRef = ref(null)

const quickPrompts = ['明天上什么课', '给明天学习方案', '帮我选人工智能实战', '打开选课页面']

onMounted(async () => {
  await store.loadSessions()
  store.refreshStatus()
})

function isPlan(m) {
  return (m.content || '').trim().startsWith('{')
}

function sendText(text) {
  if (!text || !text.trim() || store.sending) return
  store.send(text.trim())
  input.value = ''
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function selectSession(id) {
  if (store.currentSessionId === id) return
  store.currentSessionId = id
  store.messages = []
  store.send('你好')
}

function go(path) {
  router.push(path)
}

function cancelMsg(m) {
  const i = store.messages.indexOf(m)
  if (i >= 0) store.messages.splice(i, 1)
}
</script>

<style scoped>
.agent-layout { display: flex; height: calc(100vh - 48px); }
.session-panel {
  width: 220px; border-right: 1px solid #e5e7eb; background: #fff;
  display: flex; flex-direction: column; padding: 12px;
}
.new-session-btn { width: 100%; margin-bottom: 12px; }
.session-list { flex: 1; overflow-y: auto; }
.session-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 4px;
}
.session-item:hover { background: #f3f4f6; }
.session-item.active { background: #e0e7ff; }
.session-title { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-header {
  display: flex; align-items: center; gap: 12px; padding: 12px 20px;
  border-bottom: 1px solid #e5e7eb; background: #fff;
}
.chat-header h2 { font-size: 16px; margin: 0; }
.model-status { font-size: 12px; color: #f59e0b; }
.model-status.ok { color: #10b981; }
.message-list {
  flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px;
}
.msg {
  max-width: 75%; padding: 10px 14px; border-radius: 12px; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); white-space: pre-wrap; align-self: flex-start;
}
.msg.own { align-self: flex-end; background: #2563eb; color: #fff; }
.msg.error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.msg.summary { background: transparent; color: #9ca3af; font-size: 12px; align-self: center; }
.msg.typing { color: #9ca3af; font-style: italic; }
.msg-card { max-width: 80%; align-self: flex-start; }
.card-head { display: flex; align-items: center; justify-content: space-between; }
.card-content pre { margin: 0; white-space: pre-wrap; font-family: inherit; font-size: 13px; }
.confirm-info { color: #6b7280; font-size: 13px; }
.confirm-actions { display: flex; gap: 8px; margin-top: 8px; }
.quick-prompts { padding: 8px 20px; display: flex; gap: 8px; flex-wrap: wrap; }
.prompt-tag { cursor: pointer; }
.input-bar { display: flex; gap: 8px; padding: 12px 20px; border-top: 1px solid #e5e7eb; background: #fff; }
</style>
```

- [ ] **Step 2: 构建验证**

Run（在 `student-management-frontend` 目录）: `npm run build`
Expected: 构建成功

- [ ] **Step 3: Commit**

```bash
git add student-management-frontend/src/views/Agent.vue
git commit -m "feat(agent): add agent chat home page with sessions and cards"
```

---

## Task 12: 全量验证与 Ollama 联调

**Files:**
- 验证：无新文件（如发现问题按上表修复）

- [ ] **Step 1: 后端全量测试**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 原有 5 个测试 + 新增约 27 个测试全部通过，无 FAIL

- [ ] **Step 2: 前端构建**

Run（在 `student-management-frontend` 目录）: `npm run build`
Expected: 构建成功，`dist/` 更新

- [ ] **Step 3: 启动 Ollama（首次需拉模型）**

```bash
ollama pull qwen2.5:7b
ollama serve
```

确认：`Invoke-RestMethod http://localhost:11434/api/tags` 返回模型列表。

- [ ] **Step 4: 手工端到端演示（agent01）**

1. 启动 MySQL（3307）→ `python -m app.init_data` → 后端 `uvicorn app.main:app --port 8000` → 前端 `npm run dev`；
2. 用 `agent01 / test123456` 登录，应默认进入智能体主页；
3. 依次输入并核对：
   - "明天上什么课" → 内联课表卡片；
   - "给明天学习方案" → 结构化方案卡片（Ollama 关闭时应为模板方案）；
   - "帮我选人工智能实战" → 确认卡片 → 点确认 → 选课成功卡片；
   - "打开选课页面" → 自动跳转 `/selection`；
   - "新建对话" → 空白窗口，旧窗口可在左侧切换/删除；
4. 关闭 Ollama 后再发"明天上什么课" → 规则兜底仍可用，学习方案为模板降级。

- [ ] **Step 5: Commit（若 Step 1-2 需要修复）**

```bash
git add -A
git commit -m "fix(agent): address verification findings"
```

---

## 自检清单（spec → 任务映射）

| 设计文档要点 | 覆盖任务 |
| --- | --- |
| 配置（OLLAMA_*/AGENT_*/CONTEXT_BUDGET） | Task 1 |
| 消息协议 AgentMessage / 确认令牌 | Task 2 |
| 多会话窗口 / 事实表 / 上下文预算裁剪 | Task 3 |
| LLM 超时/并发/熔断 | Task 4 |
| 意图识别：LLM 优先 + 规则兜底 + 缓存 + 多意图 | Task 5 |
| 动作执行：权限复核 / 只读直跑 / 写操作预检与确认 / 学习方案降级 | Task 6 |
| 失败分级（业务失败继续、系统异常中断） | Task 6 + Task 7 循环逻辑 |
| API 路由与注册 | Task 7 |
| 种子数据 agent01（一周七天、余量>0、窗口常开、无冲突） | Task 8 |
| 前端 API/store | Task 9 |
| 默认主页路由 / 侧边栏入口 / 登录跳转 | Task 10 |
| 对话页（会话列表、卡片、确认按钮、跳转） | Task 11 |
| 全量验证 + Ollama 联调 | Task 12 |

类型一致性说明：`AgentMessage` 的 `kind` 枚举与前端渲染分支一一对应（text/card/confirmation/error/summary）；`Intent` 的 `intent` 名称与 `actions.py` 的 `_handle_<intent>` 方法名一一对应；`confirm_token` 由后端 `ConfirmationStore` 生成、前端 `store.confirm(token)` 透传、后端 `consume` 一次性校验。跨任务引用的 `FakeLLM` 只实现 `chat`/`extract_json`/`status`，与 `OllamaClient` 公共接口一致。
