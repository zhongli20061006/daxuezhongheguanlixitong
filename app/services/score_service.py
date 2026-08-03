"""成绩写入服务：API 与智能体共用，避免录入/总评逻辑漂移。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CourseSelection, Score, ScoreType
from app.utils.gpa_calculator import score_to_gpa

# 总评计算权重：平时占20%，期末占80%
DAILY_WEIGHT = 0.2
FINAL_WEIGHT = 0.8


async def record_score(
    db: AsyncSession, *,
    schedule_id: int, student_id: str, score: float, score_type: str | ScoreType,
) -> tuple[int, int]:
    """录入或更新一条成绩（平时/期末），返回 (inserted, updated)。"""
    st = score_type if isinstance(score_type, ScoreType) else ScoreType(score_type)
    existing = (await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.schedule_id == schedule_id,
            Score.score_type == st,
            Score.attempt == 1,
        )
    )).scalar_one_or_none()
    if existing:
        existing.score = score
        existing.gpa = float(score_to_gpa(score))
        return 0, 1
    db.add(Score(
        student_id=student_id,
        schedule_id=schedule_id,
        score=score,
        gpa=float(score_to_gpa(score)),
        score_type=st,
        attempt=1,
    ))
    return 1, 0


async def auto_calculate_total_if_ready(db: AsyncSession, schedule_id: int) -> int:
    """该课表所有学生平时+期末齐全时计算总评，返回计算人数。"""
    enrolled_ids = [row[0] for row in (await db.execute(
        select(CourseSelection.student_id).where(
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        )
    )).all()]
    if not enrolled_ids:
        return 0
    daily_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.daily,
            Score.attempt == 1,
        )
    )).scalars().all()}
    final_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.final,
            Score.attempt == 1,
        )
    )).scalars().all()}
    total_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.total,
            Score.attempt == 1,
        )
    )).scalars().all()}
    calculated = 0
    for sid in enrolled_ids:
        daily, final = daily_map.get(sid), final_map.get(sid)
        if daily and final:
            total_gpa = round(float(daily.gpa) * DAILY_WEIGHT + float(final.gpa) * FINAL_WEIGHT, 1)
            existing = total_map.get(sid)
            if existing:
                existing.gpa = total_gpa
            else:
                db.add(Score(
                    student_id=sid, schedule_id=schedule_id, score=None,
                    gpa=total_gpa, score_type=ScoreType.total, attempt=1,
                ))
            calculated += 1
    return calculated
