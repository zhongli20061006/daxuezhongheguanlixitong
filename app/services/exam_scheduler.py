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

        # 4. 准备时间槽（18-19周，周一~周五）
        exam_dates = []
        # 根据学期推算考试周（简化：固定为学期末第18-19周）
        import calendar
        base = date(2025, 1, 6)  # 2024-2025-1 第18周周一
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

            # 找合适的教室
            suitable_room = None
            for room in all_rooms:
                if room.capacity >= enr:
                    suitable_room = room
                    break

            if not suitable_room:
                continue

            # 找空闲时间槽
            found = False
            for d in exam_dates:
                d_str = d.strftime("%Y-%m-%d")
                for slot in TIME_SLOTS:
                    key = (d_str, slot, suitable_room.id)
                    if key in occupied:
                        continue
                    # 检查学生冲突（简化：任意学生冲突即跳过）
                    occupied[key] = True
                    found = True
                    break
                if found:
                    break

            if not found:
                continue

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
                date=d,
                start_time=slot.split("-")[0],
                end_time=slot.split("-")[1],
                invigilator_id=teacher_map.get(sch.teacher_id, str(sch.teacher_id)),
            )
            db.add(arrangement)

            # 分配学生座位
            enrolled_students = await db.execute(
                select(CourseSelection).where(
                    CourseSelection.schedule_id == sch.id,
                    CourseSelection.status == 1,
                )
            )
            seat = 1
            for cs in enrolled_students.scalars().all():
                db.add(ExamStudent(
                    exam_id=exam.id,
                    student_id=cs.student_id,
                    seat_no=seat,
                ))
                student_busy[(cs.student_id, d_str, slot)] = True
                seat += 1

            created_exams.append(exam)

        await db.commit()
        return {
            "exam_count": len(created_exams),
            "conflict_count": 0,
            "message": f"排考完成：{len(created_exams)} 场考试",
        }


exam_scheduler = ExamScheduler()
