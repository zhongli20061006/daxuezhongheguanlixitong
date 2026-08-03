"""意图识别：LLM 优先（JSON 抽取，失败重试一次），规则引擎兜底，短 TTL 缓存。"""
import re
import time
from datetime import date, timedelta
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

NAV_PHRASES = ("打开", "前往", "进入", "跳转", "页面", "去")

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

_DATE_RE = re.compile(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?")

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


def _norm_ymd(year: str, month: str, day: str) -> str:
    return f"{int(year)}-{int(month):02d}-{int(day):02d}"


def _extract_leave_params(text: str) -> dict[str, str]:
    """规则兜底：抽取请假日期与原因（尽力而为，缺失由动作层提示补充）。"""
    params: dict[str, str] = {}
    dates = _DATE_RE.findall(text)
    if dates:
        params["start_date"] = _norm_ymd(*dates[0])
        params["end_date"] = _norm_ymd(*dates[-1])
    else:
        m = re.search(r"(今天|明天|后天|大后天)", text)
        if m:
            day = date.today() + timedelta(days=_RELATIVE_DAY[m.group(1)])
            params["start_date"] = day.isoformat()
            params["end_date"] = day.isoformat()
    m = re.search(r"(?:因为|原因|理由)[:：]?\s*([^，。,.！!？?\s]{2,30})", text)
    if m:
        params["reason"] = m.group(1).strip()
    return params


def is_confirm_message(text: str) -> bool:
    """整句都是确认短语（如"确认""好的""没问题"）时视为文本确认。"""
    s = text.strip().strip("，,。.!！?？~～ \t")
    return 1 <= len(s) <= 10 and all(c in _CONFIRM_CHARS for c in s)


def is_cancel_message(text: str) -> bool:
    """短句包含取消语义（如"取消""不用了""算了"）时视为放弃待确认操作。"""
    s = text.strip().strip("，,。.!！?？~～ \t")
    return 1 <= len(s) <= 12 and any(w in s for w in _CANCEL_WORDS)


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
                elif pattern:
                    m = re.search(pattern, lowered)
                    if m:
                        params["course"] = m.group(1).strip()
                return Intent(intent=intent, params=params, confidence=0.85, need_confirm=intent in WRITE_INTENTS)
    for page_word, path in PAGE_KEYWORDS.items():
        if page_word in lowered:
            return Intent(intent=IntentType.navigate, params={"page": path}, confidence=0.9, need_confirm=False)
    return None


EXTRACT_SYSTEM_PROMPT = (
    "你是教务智能体的意图识别器。把用户指令解析为有序意图列表（JSON）。"
    "可选意图：navigate(跳转页面,params.page)、query_schedule(查课表)、study_plan(学习方案)、"
    "enroll(选课,params.course)、drop(退课,params.course)、query_classroom(查空教室)、"
    "reserve_classroom(预约教室,params.classroom/week/day_of_week/period/reason，week为1-52周次，"
    "day_of_week为1-7，period如\"1-2\"节次，reason为预约理由)、"
    "repair_submit(报修,params.location/type/description，type取值为\"水电设备/电子产品/家具类/教学用具\")、"
    "leave_apply(请假,params.start_date/end_date/reason，日期格式YYYY-MM-DD)、chat(闲聊/其他)。"
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
