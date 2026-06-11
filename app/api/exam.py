"""
考试接口
POST /exam/generate       — 自动排考
GET  /exam/list           — 考试列表（管理员）
PUT  /exam/{id}/publish   — 发布考试
GET  /exam/my-exams       — 学生考试安排
GET  /exam/my-invigilations — 教师监考安排
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.exam import Exam, ExamArrangement, ExamStudent
from app.models.subject import Subject
from app.models.classroom import Classroom
from app.models.teacher import Teacher
from app.services.exam_scheduler import exam_scheduler
from app.schemas.exam import ExamItem, ExamListResponse, ExamGenerateRequest, ExamGenerateResponse

router = APIRouter(prefix="/exam", tags=["考试"])


@router.post("/generate", response_model=ExamGenerateResponse, summary="自动排考")
async def generate_exams(
    req: ExamGenerateRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    # 先删除同学期已有考试（幂等：每次重新生成）
    existing_exams = await db.execute(select(Exam.id).where(Exam.semester == req.semester))
    exam_ids = [row[0] for row in existing_exams.all()]
    if exam_ids:
        await db.execute(delete(ExamStudent).where(ExamStudent.exam_id.in_(exam_ids)))
        await db.execute(delete(ExamArrangement).where(ExamArrangement.exam_id.in_(exam_ids)))
        await db.execute(delete(Exam).where(Exam.id.in_(exam_ids)))
        await db.flush()

    result = await exam_scheduler.generate(db, req.semester)
    return ExamGenerateResponse(
        message=result["message"],
        exam_count=result["exam_count"],
        conflict_count=result["conflict_count"],
    )


@router.get("/list", response_model=ExamListResponse, summary="考试列表")
async def list_exams(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Exam, Subject, ExamArrangement, Classroom, Teacher)
        .join(Subject, Exam.subject_id == Subject.id)
        .outerjoin(ExamArrangement, Exam.id == ExamArrangement.exam_id)
        .outerjoin(Classroom, ExamArrangement.classroom_id == Classroom.id)
        .outerjoin(Teacher, ExamArrangement.invigilator_id == Teacher.id)
        .order_by(ExamArrangement.date.asc(), ExamArrangement.start_time.asc())
    )
    items = []
    for e, subj, arr, cr, t in rows:
        items.append(ExamItem(
            id=e.id, subject_name=subj.name,
            classroom_name=cr.name if cr else None,
            date=arr.date.strftime("%Y-%m-%d") if arr and arr.date else None,
            start_time=arr.start_time if arr else None,
            end_time=arr.end_time if arr else None,
            duration_minutes=e.duration_minutes,
            status=e.status,
            invigilator_name=t.name if t else None,
            semester=e.semester, exam_type=e.exam_type,
        ))
    return ExamListResponse(exams=items)


@router.put("/{exam_id}/publish", summary="发布考试")
async def publish_exam(
    exam_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试不存在")
    exam.status = "已发布"
    await db.commit()
    return {"message": "考试已发布"}


@router.get("/my-exams", response_model=ExamListResponse, summary="我的考试")
async def my_exams(
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Exam, Subject, ExamArrangement, Classroom, ExamStudent)
        .join(Subject, Exam.subject_id == Subject.id)
        .join(ExamArrangement, Exam.id == ExamArrangement.exam_id)
        .join(Classroom, ExamArrangement.classroom_id == Classroom.id)
        .join(ExamStudent, Exam.id == ExamStudent.exam_id)
        .where(ExamStudent.student_id == current_user["username"])
        .order_by(ExamArrangement.date.asc(), ExamArrangement.start_time.asc())
    )
    return ExamListResponse(exams=[
        ExamItem(
            id=e.id, subject_name=s.name, classroom_name=c.name,
            date=a.date.strftime("%Y-%m-%d") if a.date else None,
            start_time=a.start_time, end_time=a.end_time,
            duration_minutes=e.duration_minutes, status=e.status,
            seat_no=es.seat_no, semester=e.semester, exam_type=e.exam_type,
        ) for e, s, a, c, es in rows
    ])


@router.get("/my-invigilations", response_model=ExamListResponse, summary="监考安排")
async def my_invigilations(
    current_user: dict = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Exam, Subject, ExamArrangement, Classroom)
        .join(Subject, Exam.subject_id == Subject.id)
        .join(ExamArrangement, Exam.id == ExamArrangement.exam_id)
        .join(Classroom, ExamArrangement.classroom_id == Classroom.id)
        .where(ExamArrangement.invigilator_id == current_user["username"])
        .order_by(ExamArrangement.date.asc(), ExamArrangement.start_time.asc())
    )
    return ExamListResponse(exams=[
        ExamItem(
            id=e.id, subject_name=s.name, classroom_name=c.name,
            date=a.date.strftime("%Y-%m-%d") if a.date else None,
            start_time=a.start_time, end_time=a.end_time,
            duration_minutes=e.duration_minutes, status=e.status,
            semester=e.semester, exam_type=e.exam_type,
        ) for e, s, a, c in rows
    ])
