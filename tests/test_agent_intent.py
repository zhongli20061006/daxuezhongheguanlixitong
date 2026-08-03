"""意图识别：规则匹配、LLM 优先、降级、缓存。"""
from datetime import date, timedelta

import pytest

from app.services.agent.intent import (
    IntentResolver, IntentType, extract_params_for, is_cancel_message, is_confirm_message,
    is_param_fragment, match_rules,
)
from app.services.agent.llm import OllamaUnavailable
from app.services.agent.prompts import (
    BASE_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT, INTENT_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT,
)


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
    for msg in (
        "确认", "好的", "嗯嗯", "没问题", "同意", "就这么办", "可以",
        "下一步", "继续", "继续吧", "直接提交", "帮我提交", "帮我直接提交", "提交吧",
    ):
        assert is_confirm_message(msg), msg
    for msg in ("帮我查课表", "提交请假信息", "你好", "明天上什么课", "请假：帮我直接提交"):
        assert not is_confirm_message(msg), msg


def test_cancel_message_detection():
    assert is_cancel_message("取消")
    assert is_cancel_message("不用了")
    assert is_cancel_message("算了")
    assert not is_cancel_message("明天上什么课")


def test_extract_params_leave_relative_range_and_reason():
    params = extract_params_for(IntentType.leave_apply, "明天到后天，感冒")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after = (date.today() + timedelta(days=2)).isoformat()
    assert params["start_date"] == tomorrow
    assert params["end_date"] == day_after
    assert params["reason"] == "感冒"


def test_extract_params_leave_short_dates():
    """8.3号-8.5号这类短日期应解析为当前年份的实际日期。"""
    d1 = date.today() + timedelta(days=1)
    d2 = date.today() + timedelta(days=2)
    params = extract_params_for(IntentType.leave_apply, f"{d1.month}.{d1.day}号到{d2.month}.{d2.day}号")
    assert params["start_date"] == d1.isoformat()
    assert params["end_date"] == d2.isoformat()


def test_extract_params_leave_mixed_relative_and_short():
    d2 = date.today() + timedelta(days=2)
    params = extract_params_for(IntentType.leave_apply, f"明天到{d2.month}.{d2.day}号")
    assert params["start_date"] == (date.today() + timedelta(days=1)).isoformat()
    assert params["end_date"] == d2.isoformat()


def test_unified_prompts_contain_identity_and_rules():
    assert "智伴校园" in BASE_SYSTEM_PROMPT
    assert "绝不声称" in BASE_SYSTEM_PROMPT
    assert "确认" in CHAT_SYSTEM_PROMPT
    assert "意图解析员" in INTENT_SYSTEM_PROMPT
    assert "学习规划师" in PLAN_SYSTEM_PROMPT
    assert "approve_leave" in INTENT_SYSTEM_PROMPT
    assert "query_scores" in INTENT_SYSTEM_PROMPT
    assert "query_exams" in INTENT_SYSTEM_PROMPT
    assert "query_notifications" in INTENT_SYSTEM_PROMPT


def test_rules_query_scores():
    intent = match_rules("查一下我的成绩")
    assert intent.intent == IntentType.query_scores
    assert intent.need_confirm is False


def test_rules_query_notifications():
    intent = match_rules("查看我的通知")
    assert intent.intent == IntentType.query_notifications


def test_rules_query_exams():
    intent = match_rules("我的考试安排")
    assert intent.intent == IntentType.query_exams


def test_rules_approve_leave_extracts_params():
    intent = match_rules("审批3号请假，通过")
    assert intent.intent == IntentType.approve_leave
    assert intent.need_confirm is True
    assert intent.params["leave"] == "3"
    assert intent.params["result"] == "通过"


def test_rules_approve_reject():
    intent = match_rules("驳回1号请假")
    assert intent.intent == IntentType.approve_leave
    assert intent.params["result"] == "驳回"


def test_rules_plan_followup():
    intent = match_rules("其他的呢")
    assert intent.intent == IntentType.study_plan
    intent = match_rules("剩下的课怎么安排")
    assert intent.intent == IntentType.study_plan
    # 具体动作不被追问词误伤
    intent = match_rules("帮我选其他课")
    assert intent.intent == IntentType.enroll


def test_rules_query_classroom_extracts_params():
    intent = match_rules("帮我查询第三周星期一第1--2节的空教室")
    assert intent.intent == IntentType.query_classroom
    assert intent.params["week"] == "3"
    assert intent.params["day_of_week"] == "1"
    assert intent.params["period"] == "1-2"
    intent = match_rules("查周五第3-4节空教室")
    assert intent.params["day_of_week"] == "5"
    assert intent.params["period"] == "3-4"


def test_is_param_fragment():
    assert is_param_fragment("8.4号到8.5号")
    assert is_param_fragment("明天")
    assert is_param_fragment("因为感冒")
    assert not is_param_fragment("你是谁")
    assert not is_param_fragment("帮我查课表")


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


@pytest.mark.asyncio
async def test_resolver_rules_beat_llm_chat_for_actions():
    """LLM 把动作请求误判成闲聊时，规则命中则优先规则，避免代写文案。"""
    llm = FakeLLM(result={"intents": [{"intent": "chat", "params": {}, "confidence": 0.9}]})
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("我要请假明天因为感冒")
    assert source == "rules"
    assert intents[0].intent == IntentType.leave_apply
    assert intents[0].params["start_date"] == (date.today() + timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_resolver_filters_invalid_navigate():
    """LLM 返回 navigate next 这类非法跳转时被过滤，回退到规则/闲聊。"""
    llm = FakeLLM(result={"intents": [
        {"intent": "navigate", "params": {"page": "next"}, "confidence": 0.9},
    ]})
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("下一步")
    assert source == "fallback"
    assert intents[0].intent == IntentType.chat


@pytest.mark.asyncio
async def test_resolver_rules_params_override_llm_hallucination():
    """LLM 幻觉出旧日期时，规则抽取的实际日期应覆盖它。"""
    llm = FakeLLM(result={"intents": [
        {"intent": "leave_apply", "params": {"start_date": "2023-07-01"}, "confidence": 0.9},
    ]})
    resolver = IntentResolver(llm)
    intents, source = await resolver.resolve("我要请假明天因为感冒")
    assert source == "llm"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert intents[0].params["start_date"] == tomorrow
    assert intents[0].params["end_date"] == tomorrow
    assert intents[0].params["reason"] == "感冒"
