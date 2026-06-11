"""
排考算法服务
贪心+回溯：按选课人数降序安排考试，冲突检测后重试
"""
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import Exam, ExamArrangement, ExamStudent, ExamConflict
from app.models.schedule import Schedule
from app.models.subject import Subject, SubjectType
from app.models.course_selection import CourseSelection
from app.models.classroom import Classroom
from app.models.teacher import Teacher
from app.utils.period_parser import is_period_overlap as do_periods_overlap

TIME_SLOTS = ["8:00-10:00", "10:30-12:30", "14:00-16:00", "16:30-18:30", "18:30-20:30"]


def _parse_semester_to_base_date(semester: str) -> date:
    """
    从学期字符串解析考试基准日期（最后两周的起始周一）
    格式: "YYYY-YYYY-N" 如 "2024-2025-1"
    - term "1" (秋季): 次年1月第一个周一
    - term "2" (春季): 次年6月第一个周一
    """
    parts = semester.split("-")
    if len(parts) != 3:
        # 回退到默认值
        return date(2025, 1, 6)
    try:
        start_year = int(parts[0])
        term = parts[2]
    except (ValueError, IndexError):
        return date(2025, 1, 6)

    if term == "1":
        year = start_year + 1
        month = 1
    elif term == "2":
        year = start_year + 1
        month = 6
    else:
        return date(2025, 1, 6)

    first_day = date(year, month, 1)
    # 找到当月第一个周一
    # weekday(): 0=Monday ... 6=Sunday
    days_to_monday = (7 - first_day.weekday()) % 7
    return first_day + timedelta(days=days_to_monday)


class ExamScheduler:

    async def generate(self, db: AsyncSession, semester: str = "2024-2025-1") -> dict:
        # 1. 获取所有必修+限选课程的 schedule
        rows = await db.execute(
            select(Schedule, Subject)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                Schedule.semester == semester,
                Subject.type.in_([SubjectType.compulsory, SubjectType.limited]),
            )
        )
        courses = rows.all()

        if not courses:
            return {"exam_count": 0, "conflict_count": 0, "message": "没有需要考试的课程"}

        # 2. 按选课人数降序排列
        exam_data = []
        for sch, subj in courses:
            count_result = await db.execute(
                select(func.count(CourseSelection.id)).where(
                    CourseSelection.schedule_id == sch.id,
                    CourseSelection.status == 1,
                )
            )
            enr = count_result.scalar() or 0
            exam_data.append({"schedule": sch, "subject": subj, "enrollment": enr})
        exam_data.sort(key=lambda x: x["enrollment"], reverse=True)

        # 3. 准备教室池（普通教室+机房+阶梯教室均可考试）
        c_result = await db.execute(
            select(Classroom).where(
                Classroom.type.in_(["普通教室", "机房", "阶梯教室", None])
            ).order_by(Classroom.capacity.desc())
        )
        all_rooms = c_result.scalars().all()

        # 4. 根据学期动态计算考试日期（学期末最后两周）
        base = _parse_semester_to_base_date(semester)
        exam_dates = []
        for d in range(10):  # 10个工作日（2周）
            exam_dates.append(base + timedelta(days=d))

        # 5. 贪心排考
        # 先获取教师工号映射
        teacher_rows = await db.execute(select(Teacher))
        teacher_map = {t.id: t.job_number for t in teacher_rows.scalars().all()}

        created_exams = []
        occupied = {}  # (date.strftime("%Y-%m-%d"), time_slot, classroom_id) -> True
        student_busy = {}  # (student_id, date_str, time_slot) -> True

        for item in exam_data:
            sch = item["schedule"]
            subj = item["subject"]
            enr = item["enrollment"]

            if enr == 0:
                continue

            # 提前查询该课程的选课学生（用于冲突检测）
            enrolled_students = await db.execute(
                select(CourseSelection).where(
                    CourseSelection.schedule_id == sch.id,
                    CourseSelection.status == 1,
                )
            )
            enrolled_list = enrolled_students.scalars().all()
            enrolled_ids = [cs.student_id for cs in enrolled_list]

            # 找合适的教室
            suitable_room = None
            for room in all_rooms:
                if room.capacity >= enr:
                    suitable_room = room
                    break

            if not suitable_room:
                continue

            # 找空闲时间槽（同时检测学生时间冲突）
            found = False
            chosen_d = None
            chosen_slot = None
            for d in exam_dates:
                d_str = d.strftime("%Y-%m-%d")
                for slot in TIME_SLOTS:
                    key = (d_str, slot, suitable_room.id)
                    if key in occupied:
                        continue
                    # 检查已排考试中是否有该课程的学生在同一时段冲突
                    has_conflict = any(
                        (sid, d_str, slot) in student_busy
                        for sid in enrolled_ids
                    )
                    if has_conflict:
                        continue
                    occupied[key] = True
                    chosen_d = d
                    chosen_slot = slot
                    found = True
                    break
                if found:
                    break

            if not found:
                continue

            d_str = chosen_d.strftime("%Y-%m-%d")

            # 创建考试记录
            exam = Exam(
                semester=semester,
                subject_id=subj.id,
                schedule_id=sch.id,
                exam_type="统一考试",
                duration_minutes=120,
                status="已排考",
                student_count=enr,
            )
            db.add(exam)
            await db.flush()

            # 创建考场安排
            arrangement = ExamArrangement(
                exam_id=exam.id,
                classroom_id=suitable_room.id,
                date=chosen_d,
                start_time=chosen_slot.split("-")[0],
                end_time=chosen_slot.split("-")[1],
                invigilator_id=teacher_map.get(sch.teacher_id, str(sch.teacher_id)),
            )
            db.add(arrangement)

            # 分配学生座位
            seat = 1
            for cs in enrolled_list:
                db.add(ExamStudent(
                    exam_id=exam.id,
                    student_id=cs.student_id,
                    seat_no=seat,
                ))
                student_busy[(cs.student_id, d_str, chosen_slot)] = True
                seat += 1

            created_exams.append(exam)

        await db.commit()
        return {
            "exam_count": len(created_exams),
            "conflict_count": 0,
            "message": f"排考完成：{len(created_exams)} 场考试",
        }


exam_scheduler = ExamScheduler()
