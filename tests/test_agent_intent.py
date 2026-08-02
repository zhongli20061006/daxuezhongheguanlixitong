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
