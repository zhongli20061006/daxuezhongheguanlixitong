"""意图识别：规则匹配、LLM 优先、降级、缓存。"""
from datetime import date, timedelta

import pytest

from app.services.agent.intent import (
    IntentResolver, IntentType, is_cancel_message, is_confirm_message, match_rules,
)
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


def test_rules_leave_apply_extracts_params():
    intent = match_rules("我要请假 2026-08-05 到 2026-08-06 因为感冒")
    assert intent.intent == IntentType.leave_apply
    assert intent.need_confirm is True
    assert intent.params["start_date"] == "2026-08-05"
    assert intent.params["end_date"] == "2026-08-06"
    assert intent.params["reason"] == "感冒"


def test_rules_repair_submit_extracts_params():
    intent = match_rules("我要报修，地点D101，投影仪坏了，类型电子产品")
    assert intent.intent == IntentType.repair_submit
    assert intent.need_confirm is True
    assert intent.params["location"] == "D101"
    assert intent.params["type"] == "电子产品"
    assert intent.params["description"] == "投影仪"


def test_rules_reserve_classroom_extracts_params():
    intent = match_rules("帮我预约教室D101，第3周周五1-2节，用于班会")
    assert intent.intent == IntentType.reserve_classroom
    assert intent.need_confirm is True
    assert intent.params["classroom"] == "D101"
    assert intent.params["week"] == "3"
    assert intent.params["day_of_week"] == "5"
    assert intent.params["period"] == "1-2"
    assert intent.params["reason"] == "班会"


def test_rules_reserve_classroom_not_navigate():
    """写操作关键词优先于裸页面词，避免"预约教室"被误判为跳转。"""
    intent = match_rules("预约教室D101")
    assert intent.intent == IntentType.reserve_classroom


def test_rules_leave_apply_relative_date():
    intent = match_rules("我要请假明天因为感冒")
    assert intent.intent == IntentType.leave_apply
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert intent.params["start_date"] == tomorrow
    assert intent.params["end_date"] == tomorrow
    assert intent.params["reason"] == "感冒"


def test_confirm_message_detection():
    for msg in ("确认", "好的", "嗯嗯", "没问题", "同意", "就这么办", "可以"):
        assert is_confirm_message(msg), msg
    for msg in ("帮我查课表", "提交请假信息", "你好", "明天上什么课"):
        assert not is_confirm_message(msg), msg


def test_cancel_message_detection():
    assert is_cancel_message("取消")
    assert is_cancel_message("不用了")
    assert is_cancel_message("算了")
    assert not is_cancel_message("明天上什么课")


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
