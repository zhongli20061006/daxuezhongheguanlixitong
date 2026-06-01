"""
选课接口
POST /selection/enroll      — 选课（核心：原子并发 + 业务校验链）
POST /selection/drop        — 退课（防负数 enrolled）
GET  /selection/my-courses  — 我的课程（学生/教师双视角）
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    Schedule, Subject, CourseCapacity, CourseSelection, SystemConfig,
    Teacher, Classroom, Student, StudentClass, TrainingPlan, PlanCourse,
)
from app.schemas.selection import (
    EnrollResponse,
    CourseItem, TeacherCourseItem,
    MyCoursesStudentResponse, MyCoursesTeacherResponse,
    AvailableCourseItem, AvailableCoursesResponse,
)

router = APIRouter(prefix="/selection", tags=["选课"])

@router.get("/available-courses", response_model=AvailableCoursesResponse, summary="可选课程")
async def available_courses(
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    """
    返回当前学生可选的课程列表（非必修、未选课）
    含已选人数/容量/是否已选状态
    """
    student_id = current_user["username"]
    stu_result = await db.execute(select(Student).where(Student.id == student_id))
    student = stu_result.scalar_one_or_none()
    if not student or not student.class_id:
        return AvailableCoursesResponse(courses=[])

    # 查询学生班级的所有限选/选修课，左连容量表和选课记录
    rows = await db.execute(
        text("""
            SELECT s.id AS schedule_id, sub.name AS course_name,
                   t.name AS teacher_name, c.name AS classroom_name,
                   s.day_of_week, s.period, s.weeks, sub.credit, sub.type,
                   COALESCE(cap.enrolled, 0) AS enrolled,
                   COALESCE(cap.capacity, 0) AS capacity,
                   CASE WHEN cs.id IS NOT NULL THEN 1 ELSE 0 END AS selected
            FROM schedule s
            JOIN subject sub ON s.subject_id = sub.id
            JOIN teacher t ON s.teacher_id = t.id
            JOIN classroom c ON s.classroom_id = c.id
            LEFT JOIN course_capacity cap ON cap.schedule_id = s.id
            LEFT JOIN course_selection cs ON cs.schedule_id = s.id
                AND cs.student_id = :sid AND cs.status = 1
            WHERE s.class_id = :cid AND sub.type IN ('limited', 'elective')
            ORDER BY sub.type, sub.name
        """),
        {"sid": student_id, "cid": student.class_id},
    )
    courses = [
        AvailableCourseItem(
            schedule_id=row.schedule_id,
            course_name=row.course_name,
            teacher_name=row.teacher_name,
            classroom_name=row.classroom_name,
            day_of_week=row.day_of_week,
            period=row.period,
            weeks=row.weeks,
            credit=float(row.credit),
            course_type=row.type,
            enrolled=row.enrolled,
            capacity=row.capacity,
            selected=bool(row.selected),
        )
        for row in rows
    ]
    return AvailableCoursesResponse(courses=courses)


@router.post("/enroll", response_model=EnrollResponse, summary="选课")
async def enroll(
    schedule_id: int = Query(..., gt=0, description="课表ID"),
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    """
    选课核心接口
    校验链：身份 → 课表存在 → 时间窗口 → 重复检查 → 频率限制 → 类型判断 → 并发选课
    所有写操作在事务中完成，异常自动 ROLLBACK
    """
    student_id = current_user["username"]

    # === Step 3: 查询课表及关联科目（一次 JOIN 减少查询次数） ===
    result = await db.execute(
        select(Schedule, Subject)
        .join(Subject, Schedule.subject_id == Subject.id)
        .where(Schedule.id == schedule_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课表记录不存在")
    schedule: Schedule = row[0]
    subject: Subject = row[1]

    # === Step 4: 检查选课时间窗口 ===
    now = datetime.now()
    cfg_result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.config_key.in_(["selection_start_time", "selection_end_time"])
        )
    )
    configs = {c.config_key: c.config_value for c in cfg_result.scalars().all()}
    start_str = configs.get("selection_start_time")
    end_str = configs.get("selection_end_time")
    if start_str and end_str:
        try:
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="选课时间配置错误")
        if now < start_time:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="选课未开放")
        if now > end_time:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="选课已结束")

    # === Step 5: 检查是否已选过 ===
    dup_result = await db.execute(
        select(CourseSelection).where(
            CourseSelection.student_id == student_id,
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请勿重复选课")

    # === Step 6: 检查操作频率（2分钟内同一课程退课限制） ===
    two_min_ago = now - timedelta(minutes=2)
    freq_result = await db.execute(
        select(CourseSelection).where(
            CourseSelection.student_id == student_id,
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.cancel_time >= two_min_ago,
        )
    )
    if freq_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="操作过于频繁，请稍后再试",
        )

    # === Step 7 & 8: 判断课程类型 ===
    course_type = subject.type.value
    if course_type == "compulsory":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必修课由管理员统一安排，无需选课",
        )
    elif course_type == "limited":
        # 限选课 — 校验同组已选门数，上限从培养方案获取
        limited_group = subject.limited_group
        if not limited_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该限选课未配置分组，请联系管理员",
            )

        # 查询学生班级→专业→培养方案→该组max限制
        stu_result2 = await db.execute(
            select(Student, StudentClass)
            .join(StudentClass, Student.class_id == StudentClass.id)
            .where(Student.id == student_id)
        )
        stu_row2 = stu_result2.one_or_none()
        group_max = 4  # 默认上限
        if stu_row2 and stu_row2[1]:
            cls = stu_row2[1]
            plan_result = await db.execute(
                select(TrainingPlan).where(
                    TrainingPlan.major == cls.major,
                    TrainingPlan.grade == cls.grade,
                )
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                pc_result = await db.execute(
                    select(PlanCourse).where(
                        PlanCourse.plan_id == plan.id,
                        PlanCourse.course_type == "limited",
                        PlanCourse.limited_group == limited_group,
                    ).limit(1)
                )
                pc = pc_result.scalar_one_or_none()
                if pc and pc.min_required:
                    group_max = pc.min_required

        grp_result = await db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM course_selection cs
                JOIN schedule s ON cs.schedule_id = s.id
                JOIN subject sub ON s.subject_id = sub.id
                WHERE cs.student_id = :sid
                  AND cs.status = 1
                  AND sub.limited_group = :grp
            """),
            {"sid": student_id, "grp": limited_group},
        )
        if grp_result.scalar() >= group_max:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"限选课组已选满（最多{group_max}门），请先退选后再选",
            )

    # === Step 8.4 / 9.1: 事务 — 原子选课 ===
    try:
        # 原子 UPDATE：仅当 enrolled < capacity 时成功，防止超选
        cap_result = await db.execute(
            text("""
                /* 原子选课：CAS方式增加已选人数，仅当未满时成功 */
                UPDATE course_capacity
                SET enrolled = enrolled + 1
                WHERE schedule_id = :sid AND enrolled < capacity
            """),
            {"sid": schedule_id},
        )
        if cap_result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="课程已满"
            )

        # 插入选课记录
        db.add(CourseSelection(
            student_id=student_id,
            schedule_id=schedule_id,
            status=1,
        ))
        await db.commit()

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="系统错误"
        )

    return EnrollResponse(message="选课成功", schedule_id=schedule_id)


@router.post("/drop", summary="退课")
async def drop(
    schedule_id: int = Query(..., gt=0, description="课表ID"),
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    """
    退课接口
    流程：校验课表存在 → 检查退课截止时间 → 查找有效选课记录 → 事务更新
    防止 enrolled 减为负数
    """
    student_id = current_user["username"]

    # 校验课表存在
    sch_result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    if not sch_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课表记录不存在")

    # 检查退课截止时间
    now = datetime.now()
    cfg_result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "drop_deadline")
    )
    cfg = cfg_result.scalar_one_or_none()
    if cfg:
        try:
            deadline = datetime.strptime(cfg.config_value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="退课截止时间配置错误")
        if now > deadline:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="退课时间已截止")

    # 查找有效选课记录
    sel_result = await db.execute(
        select(CourseSelection).where(
            CourseSelection.student_id == student_id,
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        )
    )
    selection = sel_result.scalar_one_or_none()
    if not selection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未选该课程，无法退课")

    # 事务：退课 = 标记取消 + 释放容量
    try:
        now_dt = datetime.now()
        upd_result = await db.execute(
            text("""
                /* 标记选课记录为已退状态 */
                UPDATE course_selection
                SET status = 0, cancel_time = :now
                WHERE student_id = :sid AND schedule_id = :schid AND status = 1
            """),
            {"sid": student_id, "schid": schedule_id, "now": now_dt},
        )
        if upd_result.rowcount == 0:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="该课程已退选"
            )

        # 减少已选人数（防负数：WHERE enrolled > 0）
        cap_result = await db.execute(
            text("""
                /* 退课释放容量，防止 enrolled 减为负数 */
                UPDATE course_capacity
                SET enrolled = enrolled - 1
                WHERE schedule_id = :schid AND enrolled > 0
            """),
            {"schid": schedule_id},
        )
        if cap_result.rowcount == 0:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="系统异常"
            )

        await db.commit()

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="系统错误"
        )

    return {"message": "退课成功"}


@router.get("/my-courses", summary="我的课程")
async def my_courses(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    学生视角：返回已选课程列表（status=1）
    教师视角：返回所教课程的选课学生名单
    """
    role = current_user["role"]

    if role == "student":
        result = await db.execute(
            select(CourseSelection, Schedule, Subject, Teacher, Classroom)
            .join(Schedule, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(
                CourseSelection.student_id == current_user["username"],
                CourseSelection.status == 1,
            )
        )
        rows = result.all()
        return MyCoursesStudentResponse(courses=[
            CourseItem(
                selection_id=cs.id,
                schedule_id=cs.schedule_id,
                course_name=subj.name,
                teacher_name=t.name,
                classroom_name=cr.name,
                day_of_week=s.day_of_week,
                period=s.period,
                weeks=s.weeks,
                credit=float(subj.credit),
                course_type=subj.type.value,
            )
            for cs, s, subj, t, cr in rows
        ])

    elif role == "teacher":
        teacher_job = current_user["username"]
        t_result = await db.execute(select(Teacher).where(Teacher.job_number == teacher_job))
        teacher = t_result.scalar_one_or_none()
        if not teacher:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教师不存在")
        result = await db.execute(
            select(CourseSelection, Schedule, Subject, Student)
            .join(Schedule, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Student, CourseSelection.student_id == Student.id)
            .where(
                Schedule.teacher_id == teacher.id,
                CourseSelection.status == 1,
            )
        )
        rows = result.all()
        return MyCoursesTeacherResponse(courses=[
            TeacherCourseItem(
                selection_id=cs.id,
                schedule_id=cs.schedule_id,
                course_name=subj.name,
                student_id=stu.id,
                student_name=stu.name,
                day_of_week=s.day_of_week,
                period=s.period,
                weeks=s.weeks,
                credit=float(subj.credit),
                course_type=subj.type.value,
            )
            for cs, s, subj, stu in rows
        ])

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅学生和教师可访问此接口"
        )
