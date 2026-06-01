"""
周次字符串解析模块
解析 schedule.weeks 字段（如 "1-18"、"1-18(单)"、"2-16(双)"）
输出 start, end, parity 供教室空闲判断使用
"""
import re
from typing import Literal

Parity = Literal["all", "odd", "even"]


def parse_weeks(weeks_str: str) -> tuple[int, int, Parity]:
    """
    解析周次字符串
    参数: weeks_str — 如 "1-18" / "1-18(单)" / "2-16(双)"
    返回: (起始周, 结束周, 奇偶标志)
          parity: "all"=每周, "odd"=单周, "even"=双周
    异常: ValueError — 格式无法解析
    """
    # 匹配模式："1-18"、"1-18(单)"、"2-16(双)"
    pattern = r"^(\d+)\s*-\s*(\d+)(?:\((单|双)\))?$"
    match = re.match(pattern, weeks_str.strip())
    if not match:
        raise ValueError(f"无法解析周次格式: {weeks_str!r}，期望格式如 '1-18' 或 '1-18(单)'")

    start = int(match.group(1))
    end = int(match.group(2))
    raw_parity = match.group(3)

    if raw_parity == "单":
        parity: Parity = "odd"
    elif raw_parity == "双":
        parity: Parity = "even"
    else:
        parity = "all"

    return start, end, parity


def is_week_matched(week: int, weeks_str: str) -> bool:
    """
    判断指定周次是否匹配周次字符串
    参数: week — 要检查的周次 (1-based)
          weeks_str — 周次字符串，如 "1-18(单)"
    返回: True 表示该周的课表包含此周次

    示例:
      is_week_matched(3, "1-18")      → True   (每周都有课)
      is_week_matched(5, "1-18(单)")   → True   (5是单周)
      is_week_matched(6, "1-18(单)")   → False  (6是双周)
      is_week_matched(2, "2-16(双)")   → True   (2是双周且在范围内)
      is_week_matched(17, "2-16(双)")  → False  (超出范围)
    """
    start, end, parity = parse_weeks(weeks_str)
    if week < start or week > end:
        return False
    if parity == "odd" and week % 2 == 0:
        return False
    if parity == "even" and week % 2 == 1:
        return False
    return True
