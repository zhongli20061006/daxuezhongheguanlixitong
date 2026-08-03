"""
考核接口
POST /scores/manual              — 手动录入（支持单条/批量，自动 upsert）
POST /scores/import              — Excel 批量导入期末成绩
POST /scores/calculate-total     — 触发总评计算
PUT  /scores/{id}               — 修改已录入成绩
GET  /scores/student/{student_id} — 查看学生所有成绩
"""
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from openpyxl import load_workbook

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    Score, ScoreType, Schedule, Subject, Student, CourseSelection, Teacher,
)
from app.utils.gpa_calculator import score_to_gpa
from app.services.score_service import (
    DAILY_WEIGHT, FINAL_WEIGHT, auto_calculate_total_if_ready, record_score,
)
from app.schemas.score import (
    ManualScoreRequest, ManualScoreResponse,
    ImportScoreResponse,
    ScoreItem, StudentScoresResponse,
)

router = APIRouter(prefix="/scores", tags=["考核"])

async def _get_teacher_id(db: AsyncSession, current_user: dict) -> int:
    """通过工号(job_number)查 teacher 表数字 id，用于校验课程归属"""
    from app.models import Teacher
    result = await db.execute(
        select(Teacher.id).where(Teacher.job_number == current_user["role_id"])
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师信息不存在")
    return t


@router.post("/manual", response_model=ManualScoreResponse, summary="手动录入成绩")
async def manual_score(
    req: ManualScoreRequest,
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    """
    教师手动录入平时/期末成绩
    - 校验教师是否教授该课程
    - 校验学生是否在选课名单中
    - 已存在记录则 UPDATE，否则 INSERT
    - 录入完成后自动检查是否可计算总评
    """
    teacher_id = await _get_teacher_id(db, current_user)
    try:
        score_type = ScoreType(req.score_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的成绩类型: {req.score_type}",
        )

    # 校验课表是否属于当前教师
    sch_result = await db.execute(
        select(Schedule).where(
            Schedule.id == req.schedule_id,
            Schedule.teacher_id == teacher_id,
        )
    )
    schedule = sch_result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程"
        )

    inserted = 0
    updated = 0

    for entry in req.scores:
        if entry.score < 0 or entry.score > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"学生 {entry.student_id} 的分数 {entry.score} 超出 0-100 范围",
            )

        # 校验学生是否选了该课
        sel_result = await db.execute(
            select(CourseSelection).where(
                CourseSelection.student_id == entry.student_id,
                CourseSelection.schedule_id == req.schedule_id,
                CourseSelection.status == 1,
            )
        )
        if not sel_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"学生 {entry.student_id} 未选此课程",
            )

        inserted_i, updated_i = await record_score(
            db, schedule_id=req.schedule_id, student_id=entry.student_id,
            score=entry.score, score_type=score_type,
        )
        inserted += inserted_i
        updated += updated_i

    try:
        await db.flush()
        calculated = await auto_calculate_total_if_ready(db, req.schedule_id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="成绩保存失败"
        )
    return ManualScoreResponse(
        inserted=inserted, updated=updated, calculated=calculated,
    )


@router.post("/import", response_model=ImportScoreResponse, summary="Excel导入成绩")
async def import_scores(
    schedule_id: int = ...,
    file: UploadFile = File(..., description="Excel文件 (.xlsx)"),
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    """
    Excel 批量导入期末成绩
    校验：文件格式 → 表头 → 行数据 → 选课名单对账 → 重复检查
    """
    teacher_id = await _get_teacher_id(db, current_user)

    # Step 1: 校验文件格式
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .xlsx 格式"
        )

    # Step 2: 校验课表权限
    sch_result = await db.execute(
        select(Schedule, Subject).join(Subject, Schedule.subject_id == Subject.id).where(
            Schedule.id == schedule_id,
            Schedule.teacher_id == teacher_id,
        )
    )
    row = sch_result.one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程"
        )

    # Step 3: 读取 Excel
    contents = await file.read()
    try:
        wb = load_workbook(io.BytesIO(contents), read_only=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="文件格式损坏或无法读取"
        )

    ws = wb.active
    if not ws:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作表为空")

    # Step 4: 校验表头
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要表头+一行数据")
    headers = [str(h).strip() if h else "" for h in rows[0]]
    if "学号" not in headers or "分数" not in headers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="表头需包含'学号'和'分数'列",
        )
    id_col = headers.index("学号")
    score_col = headers.index("分数")

    # Step 5: 逐行校验
    data_rows = rows[1:]
    excel_students: dict[str, float] = {}
    for i, row_data in enumerate(data_rows, start=2):
        sid = str(row_data[id_col]).strip() if row_data[id_col] else ""
        raw_score = row_data[score_col]
        if not sid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"第{i}行：学号为空",
            )
        try:
            score_val = float(raw_score)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"第{i}行：分数不是有效数字",
            )
        if score_val < 0 or score_val > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"第{i}行（{sid}）：分数 {score_val} 超出 0-100 范围",
            )
        if sid in excel_students:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"第{i}行：学号 {sid} 在文件中重复",
            )
        excel_students[sid] = score_val
    wb.close()

    # Step 6: 与选课名单对账
    sel_result = await db.execute(
        select(CourseSelection).where(
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        )
    )
    enrolled_ids = {s.student_id for s in sel_result.scalars().all()}

    warnings = []
    for sid in excel_students:
        if sid not in enrolled_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"学号 {sid} 未选此课程",
            )
    # 反向检查：选课名单中缺失的学生（不阻断，只记录）
    for sid in enrolled_ids:
        if sid not in excel_students:
            warnings.append(f"学生 {sid} 在选课名单中但未在Excel中找到")

    # Step 7: 检查是否已有期末成绩记录
    exist_check = await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.score_type == ScoreType.final,
            Score.attempt == 1,
        )
    )
    if exist_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该课程已录入期末成绩，请使用修改功能",
        )

    # Step 8: 批量插入
    try:
        for sid, score_val in excel_students.items():
            gpa = score_to_gpa(score_val)
            db.add(Score(
                student_id=sid,
                schedule_id=schedule_id,
                score=score_val,
                gpa=float(gpa),
                score_type=ScoreType.final,
                attempt=1,
            ))
        await db.flush()

        # Step 9: 自动计算总评
        calculated = await auto_calculate_total_if_ready(db, schedule_id)

        await db.commit()
        return ImportScoreResponse(
            success_count=len(excel_students),
            warnings=warnings,
            calculated=calculated,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入失败: {str(e)}",
        )


@router.post("/calculate-total", summary="计算总评")
async def calculate_total(
    schedule_id: int = ...,
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    """
    对指定课程的所有学生计算总评（平时gpa*0.2 + 期末gpa*0.8）
    仅在平时和期末成绩都齐全时才计算
    """
    teacher_id = await _get_teacher_id(db, current_user)
    sch_result = await db.execute(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.teacher_id == teacher_id,
        )
    )
    if not sch_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")

    try:
        calculated = await auto_calculate_total_if_ready(db, schedule_id)
        await db.commit()
        return {"message": f"计算完成", "calculated": calculated}
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="总评计算失败")


@router.put("/{score_id}", summary="修改成绩")
async def update_score(
    score_id: int,
    new_score: float = ...,
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    """
    修改已录入的成绩，自动重算对应绩点
    如果该学生已有总评记录，自动重新计算
    """
    teacher_id = await _get_teacher_id(db, current_user)

    if new_score < 0 or new_score > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分数范围 0-100")

    score_result = await db.execute(select(Score).where(Score.id == score_id))
    score = score_result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成绩记录不存在")

    if score.score_type == ScoreType.total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="总评成绩由系统自动计算，不允许手动修改",
        )

    # 校验教师权限
    sch_result = await db.execute(
        select(Schedule).where(
            Schedule.id == score.schedule_id,
            Schedule.teacher_id == teacher_id,
        )
    )
    if not sch_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该成绩")

    # 更新分数和绩点
    score.score = new_score
    score.gpa = float(score_to_gpa(new_score))
    await db.flush()

    # 如果该学生已有总评记录，自动重算
    total_result = await db.execute(
        select(Score).where(
            Score.student_id == score.student_id,
            Score.schedule_id == score.schedule_id,
            Score.score_type == ScoreType.total,
            Score.attempt == 1,
        )
    )
    total = total_result.scalar_one_or_none()
    if total:
        await _recalc_total(score.student_id, score.schedule_id, db)

    await db.commit()
    return {"message": "成绩已更新", "score_id": score_id}


@router.get("/by-schedule/{schedule_id}", summary="获取课程成绩（教师回填用）")
async def get_scores_by_schedule(
    schedule_id: int,
    score_type: str = ...,
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    teacher_id = await _get_teacher_id(db, current_user)
    sch = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.teacher_id == teacher_id))
    schedule = sch.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该课程")

    try:
        st = ScoreType(score_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的成绩类型")

    result = await db.execute(
        select(Score, Student).join(Student, Score.student_id == Student.id)
        .where(Score.schedule_id == schedule_id, Score.score_type == st, Score.attempt == 1)
    )
    scores = [{"student_id": s.student_id, "student_name": stu.name, "score": float(s.score) if s.score is not None else None} for s, stu in result.all()]
    return {"scores": scores}


@router.get("/student/{student_id}", response_model=StudentScoresResponse, summary="查看学生成绩")
async def student_scores(
    student_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查看指定学生的所有成绩
    学生只能查看自己，教师可查看所教学生
    """
    role = current_user["role"]
    if role == "student" and current_user["username"] != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能查看自己的成绩")

    # 查询成绩 + JOIN 科目/课表信息，按课程名排序
    result = await db.execute(
        select(Score, Subject)
        .join(Schedule, Score.schedule_id == Schedule.id)
        .join(Subject, Schedule.subject_id == Subject.id)
        .where(Score.student_id == student_id)
        .order_by(Subject.name, Score.score_type)
    )
    scores = [
        ScoreItem(
            id=sc.id,
            course_name=subj.name,
            credit=float(subj.credit),
            score=float(sc.score) if sc.score is not None else None,
            gpa=float(sc.gpa),
            score_type=sc.score_type if isinstance(sc.score_type, str) else str(sc.score_type.value),
            attempt=sc.attempt,
            updated_at=sc.updated_at.strftime("%Y-%m-%d %H:%M:%S") if sc.updated_at else "",
        )
        for sc, subj in result.all()
    ]
    return StudentScoresResponse(student_id=student_id, scores=scores)


async def _recalc_total(student_id: str, schedule_id: int, db: AsyncSession):
    """
    重算单个学生的总评成绩（平时gpa*0.2 + 期末gpa*0.8）
    写入 score 表（score_type='总评', score=NULL）
    """
    daily_result = await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.schedule_id == schedule_id,
            Score.score_type == ScoreType.daily,
            Score.attempt == 1,
        )
    )
    final_result = await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.schedule_id == schedule_id,
            Score.score_type == ScoreType.final,
            Score.attempt == 1,
        )
    )
    daily = daily_result.scalar_one_or_none()
    final = final_result.scalar_one_or_none()
    if not daily or not final:
        return

    total_gpa = daily.gpa * DAILY_WEIGHT + final.gpa * FINAL_WEIGHT
    total_gpa = round(float(total_gpa), 1)

    # UPSERT 总评记录
    exist = await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.schedule_id == schedule_id,
            Score.score_type == ScoreType.total,
            Score.attempt == 1,
        )
    )
    existing = exist.scalar_one_or_none()
    if existing:
        existing.gpa = total_gpa
    else:
        db.add(Score(
            student_id=student_id,
            schedule_id=schedule_id,
            score=None,  # 总评不存百分制分数
            gpa=total_gpa,
            score_type=ScoreType.total,
            attempt=1,
        ))
