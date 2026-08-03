"""意图识别：LLM 优先（JSON 抽取，失败重试一次），规则引擎兜底，短 TTL 缓存。"""
import re
import time
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable
from app.services.agent.prompts import INTENT_SYSTEM_PROMPT


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
    approve_leave = "approve_leave"
    query_scores = "query_scores"
    query_notifications = "query_notifications"
    query_exams = "query_exams"
    chat = "chat"


WRITE_INTENTS = frozenset({
    IntentType.enroll, IntentType.drop, IntentType.reserve_classroom,
    IntentType.repair_submit, IntentType.leave_apply, IntentType.approve_leave,
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

KNOWN_PAGES = frozenset({
    "/", "/dashboard", "/schedule", "/selection", "/scores", "/scores/input",
    "/classrooms", "/repairs", "/repairs/manage", "/leaves", "/plan",
    "/my-exams", "/my-invigilations", "/advisor", "/notifications", "/profile", "/admin",
})

NAV_PHRASES = ("打开", "前往", "进入", "跳转", "页面", "去")

RULE_TABLE: list[tuple[IntentType, list[str], str | None]] = [
    (IntentType.study_plan, ["学习方案", "学习计划", "怎么学", "复习计划"], None),
    (IntentType.query_schedule, ["上什么课", "课程安排", "课表"], None),
    (IntentType.query_classroom, ["空教室", "教室可用", "查教室"], None),
    (IntentType.query_exams, ["考试", "监考"], None),
    (IntentType.query_scores, ["成绩", "绩点"], None),
    (IntentType.query_notifications, ["通知", "未读"], None),
    (IntentType.reserve_classroom, ["预约教室", "借教室", "订教室", "申请教室"], None),
    (IntentType.drop, ["退课", "退选", "不上了"], r"(?:退课|退选)\s*([^\s，。,.！!？?]+)"),
    (IntentType.enroll, ["选课", "选这门", "报名", "选修", "帮我选", "要选"], r"(?:选|报)(?:修|名)?\s*([^\s，。,.！!？?]+)"),
    (IntentType.repair_submit, ["报修", "修一下", "后勤", "东西坏了"], None),
    (IntentType.approve_leave, ["审批", "批准", "驳回", "同意请假"], None),
    (IntentType.leave_apply, ["请假", "休假申请"], None),
]

_DATE_RE = re.compile(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?")
_SHORT_DATE_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})号?")
_MONTH_DAY_RE = re.compile(r"(\d{1,2})月(\d{1,2})[日号]?")

_REPAIR_TYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("水电设备", ("水电", "水龙头", "漏水", "断电", "灯", "插座", "水管")),
    ("电子产品", ("电脑", "投影", "屏幕", "打印机", "电子", "网络")),
    ("家具类", ("桌椅", "椅子", "桌子", "柜子", "床", "家具")),
    ("教学用具", ("黑板", "白板", "粉笔", "多媒体", "讲台", "教具")),
]

_WEEKDAY_CN_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}

_RELATIVE_DAY = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}

_CONFIRM_CHARS = frozenset("嗯好可以确认确定同意执行提交没问题行是的就这么办")
_CANCEL_WORDS = ("取消", "不用", "算了", "撤销", "不办了", "别了")
_CONFIRM_PHRASES = frozenset({
    "确认", "确定", "同意", "执行", "确认执行", "提交", "直接提交", "帮我提交",
    "帮我直接提交", "就这么办", "没问题", "好的", "好", "嗯", "嗯嗯", "可以", "行",
    "是的", "对", "继续", "下一步", "继续吧", "提交吧", "就这么定了",
})


def _norm_ymd(year: str, month: str, day: str) -> str:
    return f"{int(year)}-{int(month):02d}-{int(day):02d}"


def _norm_short_ymd(month: str, day: str) -> str:
    """短日期（如 8.3号 / 8月4日）补全为当前年份的 YYYY-MM-DD。"""
    try:
        return date(date.today().year, int(month), int(day)).isoformat()
    except ValueError:
        return ""


def _extract_leave_params(text: str) -> dict[str, str]:
    """规则兜底：抽取请假日期与原因（尽力而为，缺失由动作层提示补充）。"""
    params: dict[str, str] = {}
    dates = _DATE_RE.findall(text)
    if dates:
        params["start_date"] = _norm_ymd(*dates[0])
        params["end_date"] = _norm_ymd(*dates[-1])
    else:
        candidates: list[tuple[int, str]] = []
        for m in re.finditer(r"(今天|明天|后天|大后天)", text):
            day = date.today() + timedelta(days=_RELATIVE_DAY[m.group(1)])
            candidates.append((m.start(), day.isoformat()))
        for m in re.finditer(_SHORT_DATE_RE, text):
            value = _norm_short_ymd(*m.groups())
            if value:
                candidates.append((m.start(), value))
        for m in re.finditer(_MONTH_DAY_RE, text):
            value = _norm_short_ymd(*m.groups())
            if value:
                candidates.append((m.start(), value))
        if candidates:
            candidates.sort()
            params["start_date"] = candidates[0][1]
            params["end_date"] = candidates[-1][1]
    m = re.search(r"(?:因为|原因|理由)[:：]?\s*(?:是)?\s*([^，。,.！!？?\s]{2,30})", text)
    if m:
        params["reason"] = m.group(1).strip()
    else:
        m = re.search(r"[，,。]\s*([^，。,.！!？?\s]{1,20})$", text)
        if m:
            params["reason"] = m.group(1).strip()
    return params


def extract_params_for(intent_type: "IntentType", text: str) -> dict[str, str]:
    """按意图类型抽取参数，供动作层/多轮补全复用。"""
    if intent_type == IntentType.leave_apply:
        return _extract_leave_params(text)
    if intent_type == IntentType.repair_submit:
        return _extract_repair_params(text)
    if intent_type == IntentType.reserve_classroom:
        return _extract_reserve_params(text)
    if intent_type == IntentType.approve_leave:
        return _extract_approve_params(text)
    return {}


def is_confirm_message(text: str) -> bool:
    """整句都是确认短语（如"确认""好的""没问题"）时视为文本确认。"""
    s = text.strip().strip("，,。.!！?？~～ \t")
    return s in _CONFIRM_PHRASES or (
        1 <= len(s) <= 8 and all(c in _CONFIRM_CHARS for c in s)
    )


def is_cancel_message(text: str) -> bool:
    """短句包含取消语义（如"取消""不用了""算了"）时视为放弃待确认操作。"""
    s = text.strip().strip("，,。.!！?？~～ \t")
    return 1 <= len(s) <= 12 and any(w in s for w in _CANCEL_WORDS)


def is_param_fragment(text: str) -> bool:
    """短句里含日期/原因等信息片段（如"8.4号到8.5号"），视为补全待办操作的续句。"""
    s = text.strip()
    if not s or len(s) > 30:
        return False
    return bool(re.search(r"\d|号|日|月|周|今天|明天|后天|因为|原因|理由", s))


def _intent_usable(intent: "Intent") -> bool:
    """过滤 LLM 吐出的无效意图（如把\"下一步\"解析成跳转 next）。"""
    if intent.intent == IntentType.navigate:
        page = (intent.params.get("page") or "").rstrip("/") or "/"
        return page in KNOWN_PAGES
    return True


def _extract_repair_params(text: str) -> dict[str, str]:
    """规则兜底：抽取报修地点/类型/描述。"""
    params: dict[str, str] = {}
    for type_name, keywords in _REPAIR_TYPE_KEYWORDS:
        if any(kw in text for kw in keywords):
            params["type"] = type_name
            break
    m = re.search(r"(?:在|地点|位置)[:：]?\s*([^，。,.！!？?\s]{1,30})", text)
    if not m:
        m = re.search(r"([\u4e00-\u9fa5]{2,12}(?:教室|宿舍|办公室|实验室|机房|楼|馆|大厅|卫生间))", text)
    if not m:
        m = re.search(r"([A-Za-z]{1,4}\d{2,4})", text)
    if m:
        params["location"] = m.group(1).strip()
    m = re.search(r"([^，。,.！!？?\s]{1,20}?)(?:坏了|有问题|需要修|故障|不能用)", text)
    if m:
        params["description"] = m.group(1).strip()
    return params


def _extract_reserve_params(text: str) -> dict[str, str]:
    """规则兜底：抽取教室名/周次/星期/节次/理由。"""
    params: dict[str, str] = {}
    m = re.search(r"([A-Za-z]{1,4}\d{2,4})", text)
    if m:
        params["classroom"] = m.group(1)
    m = re.search(r"第?\s*(\d{1,2})\s*周", text)
    if m:
        params["week"] = str(int(m.group(1)))
    m = re.search(r"周([一二三四五六日天])", text)
    if m:
        params["day_of_week"] = str(_WEEKDAY_CN_MAP[m.group(1)])
    m = re.search(r"(\d{1,2})\s*[-~至]\s*(\d{1,2})\s*节?", text)
    if m:
        params["period"] = f"{int(m.group(1))}-{int(m.group(2))}"
    m = re.search(r"(?:用于|因为|理由|为了)[:：]?\s*([^，。,.！!？?\s]{2,20})", text)
    if m:
        params["reason"] = m.group(1).strip()
    return params


def _extract_approve_params(text: str) -> dict[str, str]:
    """规则兜底：抽取审批的请假编号/学生、结果与意见。"""
    params: dict[str, str] = {}
    if "驳回" in text:
        params["result"] = "驳回"
    elif any(k in text for k in ("通过", "同意", "批准")):
        params["result"] = "通过"
    m = re.search(r"(?:第)?\s*(\d+)\s*(?:号|条)", text)
    if m:
        params["leave"] = m.group(1)
    m = re.search(r"([\u4e00-\u9fa5]{2,4})(?:同学)?的请假", text)
    if m:
        params["student"] = m.group(1)
    m = re.search(r"(?:意见|备注)[:：]?\s*([^，。,.！!？?\s]{1,30})", text)
    if m:
        params["comment"] = m.group(1).strip()
    return params


def match_rules(text: str) -> "Intent | None":
    """导航短语优先（跳转），其次动作规则表，最后裸页面词兜底跳转。"""
    lowered = text.strip()
    if any(p in lowered for p in NAV_PHRASES):
        for page_word, path in PAGE_KEYWORDS.items():
            if page_word in lowered:
                return Intent(intent=IntentType.navigate, params={"page": path}, confidence=0.9, need_confirm=False)
    for intent, keywords, pattern in RULE_TABLE:
        for kw in keywords:
            if kw in lowered:
                params: dict[str, str] = {}
                if intent == IntentType.leave_apply:
                    params = _extract_leave_params(lowered)
                elif intent == IntentType.repair_submit:
                    params = _extract_repair_params(lowered)
                elif intent == IntentType.reserve_classroom:
                    params = _extract_reserve_params(lowered)
                elif intent == IntentType.approve_leave:
                    params = _extract_approve_params(lowered)
                elif pattern:
                    m = re.search(pattern, lowered)
                    if m:
                        params["course"] = m.group(1).strip()
                return Intent(intent=intent, params=params, confidence=0.85, need_confirm=intent in WRITE_INTENTS)
    for page_word, path in PAGE_KEYWORDS.items():
        if page_word in lowered:
            return Intent(intent=IntentType.navigate, params={"page": path}, confidence=0.9, need_confirm=False)
    return None


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
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ])
                intents = self._parse_llm(data)
                if intents:
                    # LLM 把动作请求误判成闲聊时，规则命中则优先规则
                    if all(i.intent == IntentType.chat for i in intents):
                        rule = match_rules(text)
                        if rule:
                            self._put(text, [rule], now)
                            return [rule], "rules"
                    # 写操作参数以规则抽取为准，避免模型幻觉日期/地点
                    for intent in intents:
                        if intent.intent in WRITE_INTENTS:
                            for key, value in extract_params_for(intent.intent, text).items():
                                if value:
                                    intent.params[key] = value
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
            try:
                intent = Intent(**item)
            except (ValueError, ValidationError):
                continue
            intent.need_confirm = intent.intent in WRITE_INTENTS
            if not _intent_usable(intent):
                continue
            intents.append(intent)
        return intents

    def _put(self, text: str, intents: list[Intent], now: float) -> None:
        if len(self._cache) >= self.cache_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            self._cache.pop(oldest, None)
        self._cache[text] = (now, intents)
