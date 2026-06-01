"""
节次字符串解析模块
解析 schedule.period 字段（如 "1-2"、"5-5"）
输出 start, end 供教室空闲判断使用（判断两节课是否时间重叠）
"""


def parse_period(period_str: str) -> tuple[int, int]:
    """
    解析节次字符串为起止节号
    参数: period_str — 如 "1-2"（第1-2节连上）、"5-5"（仅第5节）
    返回: (起始节号, 结束节号)
    异常: ValueError — 格式无法解析
    """
    parts = period_str.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"无法解析节次格式: {period_str!r}，期望格式如 '1-2' 或 '5-5'")
    start = int(parts[0])
    end = int(parts[1])
    if start > end:
        raise ValueError(f"起始节号不能大于结束节号: {period_str!r}")
    return start, end


def is_period_overlap(period_a: str, period_b: str) -> bool:
    """
    判断两节课的时间段是否重叠
    参数: period_a — 如 "1-2"
          period_b — 如 "3-4"
    返回: True 表示时间冲突（重叠）
          False 表示不重叠

    示例:
      overlap("1-2", "3-4") → False (不重叠)
      overlap("1-3", "2-4") → True  (第2-3节重叠)
      overlap("1-2", "1-2") → True  (完全相同)
    """
    a_start, a_end = parse_period(period_a)
    b_start, b_end = parse_period(period_b)
    # 重叠条件：两个区间有交集
    # 不自反地：a_start <= b_end AND b_start <= a_end
    return a_start <= b_end and b_start <= a_end
