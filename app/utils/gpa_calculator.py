"""
5分制绩点计算模块
智能医学工程专业使用5分制绩点体系

百分制 → 5分制绩点映射表：
  90-100 → 5.0
  85-89  → 4.5
  82-84  → 4.0
  78-81  → 3.5
  75-77  → 3.0
  72-74  → 2.5
  68-71  → 2.0
  64-67  → 1.5
  60-63  → 1.0
  <60    → 0
"""
from decimal import Decimal, ROUND_HALF_UP

# 绩点映射表：(分数下限, 分数上限, 绩点)
_GPA_MAP = [
    (90, 100, Decimal("5.0")),
    (85, 89, Decimal("4.5")),
    (82, 84, Decimal("4.0")),
    (78, 81, Decimal("3.5")),
    (75, 77, Decimal("3.0")),
    (72, 74, Decimal("2.5")),
    (68, 71, Decimal("2.0")),
    (64, 67, Decimal("1.5")),
    (60, 63, Decimal("1.0")),
    (0, 59, Decimal("0")),
]


def score_to_gpa(score: float | int | Decimal) -> Decimal:
    """
    将百分制分数转换为5分制绩点
    参数: score — 百分制分数 (0~100)
    返回: Decimal — 5分制绩点
    异常: ValueError — 分数超出范围
    """
    if not isinstance(score, Decimal):
        score = Decimal(str(score))
    score = score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    if score > 100:
        raise ValueError(f"分数不能超过100，当前值: {score}")
    if score < 0:
        raise ValueError(f"分数不能为负数，当前值: {score}")

    for lo, hi, gpa in _GPA_MAP:
        if lo <= score <= hi:
            return gpa

    return Decimal("0")
