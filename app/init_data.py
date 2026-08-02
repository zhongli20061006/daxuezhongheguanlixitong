"""
数据初始化脚本
功能：清空所有表后插入完整的测试数据，生成随机密码并打印到控制台
特性：可重复执行（TRUNCATE 方式），每次运行生成不同的随机密码

运行方式（在项目根目录执行）：
    python -m app.init_data
    或
    python app/init_data.py
"""
import secrets
import string
import sys
import os

# 确保从任何目录运行都能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import text
from app.database import SyncSessionLocal, sync_engine, Base
from app.models import (
    Teacher, StudentClass, Subject, SubjectType,
    Classroom, Schedule, CourseCapacity,
    UserCredential, UserRole, Student, Staff,
    SystemConfig, TrainingPlan, PlanCourse,
)


def generate_password(length: int = 12) -> str:
    """
    生成加密安全的随机密码
    参数: length — 密码长度，默认12位
    返回: 包含大小写字母和数字的随机字符串
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(plain_text: str) -> str:
    """将明文密码通过 bcrypt 哈希后返回哈希值"""
    return bcrypt.hashpw(plain_text.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def truncate_all_tables():
    """
    按外键依赖的反序清空所有表
    TRUNCATE 比 DELETE 更快（不逐行记日志），且会重置 AUTO_INCREMENT
    需要先关闭外键检查（SET FOREIGN_KEY_CHECKS = 0），否则会因 FK 约束拒绝执行
    """
    # 清空顺序：先删依赖表，再删被依赖表，避免外键冲突
    truncate_order = [
        "score",              # FK → student, schedule
        "course_selection",   # FK → schedule
        "course_capacity",    # FK → schedule
        "schedule",           # FK → teacher, subject, class, classroom
        "student",            # FK → class
        "user_credential",    # 无 FK，独立
        "staff",              # 无 FK，独立
        "repair",             # 无 FK，独立
        "teacher",            # 被 schedule 引用
        "subject",            # 被 schedule 引用
        "class",              # 被 schedule, student 引用
        "classroom",          # 被 schedule 引用
        "system_config",      # 无 FK，独立
    ]
    with sync_engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.commit()
        for table in truncate_order:
            conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            conn.commit()
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()
    print("所有表已清空，AUTO_INCREMENT 已重置\n")


def init_data():
    """
    主初始化函数
    执行顺序：
    1. 确保表结构存在（幂等建表）
    2. TRUNCATE 清空所有数据（幂等：支持重复执行）
    3. 依次插入：班级 → 教师 → 科目 → 课表 → 容量 → 学生 → 后勤 → 认证账号
    4. 打印所有账号密码到控制台
    """
    # Step 0: 确保表结构存在（如果表不存在则创建，已存在则跳过）
    Base.metadata.create_all(bind=sync_engine)

    # Step 1: 清空旧数据
    truncate_all_tables()

    # 存储明文密码，最后统一打印
    credentials: list[dict] = []

    with SyncSessionLocal() as db:
        # ===== Step 2: 插入班级（3个）=====
        classes = [
            StudentClass(name="2024级计算机科学1班", major="计算机科学与技术", grade=2024, advisor_id=10001),
            StudentClass(name="2024级软件工程1班", major="软件工程", grade=2024, advisor_id=10005),
            StudentClass(name="2023级计算机科学1班", major="计算机科学与技术", grade=2023, advisor_id=10002),
        ]
        db.add_all(classes)
        db.flush()  # 立即获取自增 ID，供后续步骤使用（不提交事务）

        # ===== Step 3: 插入教师（5人）=====
        # 工号作为主键，手工指定 id 而非自增
        teachers = [
            Teacher(id=10001, name="张伟", job_number="T10001", department="计算机科学学院", title="教授", is_college_admin=True),
            Teacher(id=10002, name="李娜", job_number="T10002", department="数学学院", title="副教授"),
            Teacher(id=10003, name="王强", job_number="T10003", department="外国语学院", title="讲师"),
            Teacher(id=10004, name="赵敏", job_number="T10004", department="物理学院", title="副教授"),
            Teacher(id=10005, name="刘洋", job_number="T10005", department="体育学院", title="讲师"),
        ]
        db.add_all(teachers)

        # ===== Step 4: 插入科目（10门）=====
        # 分类：4门必修 + 4门限选（分2组）+ 2门选修
        subjects = [
            # 必修课：不进入选课系统，按班级固定分配
            Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
            Subject(id=2, name="大学英语", credit=4.0, type=SubjectType.compulsory),
            Subject(id=3, name="程序设计基础", credit=4.0, type=SubjectType.compulsory),
            Subject(id=4, name="数据结构与算法", credit=4.0, type=SubjectType.compulsory),
            # 限选课 — 分组 CS_LTD_01（编程方向）：同组内至多选2门
            Subject(id=5, name="Java程序设计", credit=3.0, type=SubjectType.limited, limited_group="CS_LTD_01"),
            Subject(id=6, name="Python数据分析", credit=3.0, type=SubjectType.limited, limited_group="CS_LTD_01"),
            # 限选课 — 分组 CS_LTD_02（网络与数据库方向）
            Subject(id=7, name="数据库原理", credit=3.0, type=SubjectType.limited, limited_group="CS_LTD_02"),
            Subject(id=8, name="计算机网络", credit=3.0, type=SubjectType.limited, limited_group="CS_LTD_02"),
            # 选修课：先到先得，达到容量上限后无法选择
            Subject(id=9, name="人工智能导论", credit=2.0, type=SubjectType.elective),
            Subject(id=10, name="摄影基础", credit=1.0, type=SubjectType.elective),
        ]
        db.add_all(subjects)
        db.flush()

        # ===== Step 4.5: 插入教室（10间）=====
        # 为课表中的教室字段提供 FK 引用
        classrooms = [
            Classroom(id=1, name="D101", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=2, name="D102", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=3, name="D103", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=4, name="D104", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=5, name="D201", capacity=80, building="教学楼D", has_projector=False),
            Classroom(id=6, name="D202", capacity=80, building="教学楼D", has_projector=False),
            Classroom(id=7, name="D301", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=8, name="D302", capacity=60, building="教学楼D", has_projector=False),
            Classroom(id=9, name="D401", capacity=120, building="教学楼D", has_projector=True),
            Classroom(id=10, name="D402", capacity=120, building="教学楼D", has_projector=True),
        ]
        db.add_all(classrooms)
        db.flush()

        # ===== Step 5: 插入课表（15条）=====
        # classroom_id 映射: 1=D101, 2=D102, 3=D103, 4=D104, 5=D201,
        #                    6=D202, 7=D301, 8=D302, 9=D401, 10=D402
        schedules_data = [
            # ---- 班级1（2024CS1）的课表 ----
            # 必修课 4 门
            {"teacher_id": 10001, "subject_id": 3, "class_id": 1, "classroom_id": 1,
             "weeks": "1-18", "day_of_week": 1, "period": "1-2", "semester": "2024-2025-1"},
            {"teacher_id": 10001, "subject_id": 4, "class_id": 1, "classroom_id": 1,
             "weeks": "1-18", "day_of_week": 2, "period": "1-2", "semester": "2024-2025-1"},
            {"teacher_id": 10002, "subject_id": 1, "class_id": 1, "classroom_id": 5,
             "weeks": "1-18", "day_of_week": 1, "period": "3-4", "semester": "2024-2025-1"},
            {"teacher_id": 10003, "subject_id": 2, "class_id": 1, "classroom_id": 7,
             "weeks": "1-18", "day_of_week": 3, "period": "1-2", "semester": "2024-2025-1"},
            # 限选课 4 门
            {"teacher_id": 10001, "subject_id": 5, "class_id": 1, "classroom_id": 2,
             "weeks": "1-18", "day_of_week": 4, "period": "1-2", "semester": "2024-2025-1"},
            {"teacher_id": 10004, "subject_id": 6, "class_id": 1, "classroom_id": 3,
             "weeks": "1-18", "day_of_week": 4, "period": "3-4", "semester": "2024-2025-1"},
            {"teacher_id": 10004, "subject_id": 7, "class_id": 1, "classroom_id": 3,
             "weeks": "1-18", "day_of_week": 5, "period": "1-2", "semester": "2024-2025-1"},
            {"teacher_id": 10001, "subject_id": 8, "class_id": 1, "classroom_id": 2,
             "weeks": "1-18", "day_of_week": 5, "period": "3-4", "semester": "2024-2025-1"},
            # 选修课 2 门
            {"teacher_id": 10005, "subject_id": 9, "class_id": 1, "classroom_id": 9,
             "weeks": "1-12", "day_of_week": 1, "period": "5-6", "semester": "2024-2025-1"},
            {"teacher_id": 10005, "subject_id": 10, "class_id": 1, "classroom_id": 10,
             "weeks": "1-8", "day_of_week": 3, "period": "5-6", "semester": "2024-2025-1"},
            # ---- 班级2（2024SE1）的课表 ----
            {"teacher_id": 10002, "subject_id": 1, "class_id": 2, "classroom_id": 5,
             "weeks": "1-18", "day_of_week": 2, "period": "3-4", "semester": "2024-2025-1"},
            {"teacher_id": 10003, "subject_id": 2, "class_id": 2, "classroom_id": 7,
             "weeks": "1-18", "day_of_week": 3, "period": "3-4", "semester": "2024-2025-1"},
            {"teacher_id": 10004, "subject_id": 3, "class_id": 2, "classroom_id": 4,
             "weeks": "1-18", "day_of_week": 1, "period": "3-4", "semester": "2024-2025-1"},
            # ---- 班级3（2023CS1）的课表 ----
            {"teacher_id": 10002, "subject_id": 1, "class_id": 3, "classroom_id": 6,
             "weeks": "1-18", "day_of_week": 1, "period": "1-2", "semester": "2024-2025-1"},
            {"teacher_id": 10003, "subject_id": 2, "class_id": 3, "classroom_id": 8,
             "weeks": "1-18", "day_of_week": 2, "period": "1-2", "semester": "2024-2025-1"},
        ]
        # 批量创建 Schedule 对象并插入
        schedules = [Schedule(**data) for data in schedules_data]
        db.add_all(schedules)
        # ===== Step 5.5: 智能体测试数据 —— 周末课表 + 可选课程（agent01 一周每天有课）=====
        weekend_schedules = [
            Schedule(teacher_id=10001, subject_id=1, class_id=1, classroom_id=5,
                     weeks="1-18", day_of_week=6, period="1-2", semester="2024-2025-1"),
            Schedule(teacher_id=10002, subject_id=2, class_id=1, classroom_id=7,
                     weeks="1-18", day_of_week=7, period="3-4", semester="2024-2025-1"),
        ]
        db.add_all(weekend_schedules)
        db.flush()

        agent_ai_subject = Subject(id=11, name="人工智能实战", credit=2.0, type=SubjectType.elective)
        db.add(agent_ai_subject)
        db.flush()

        agent_ai_schedule = Schedule(
            teacher_id=10001, subject_id=11, class_id=1, classroom_id=9,
            weeks="1-18", day_of_week=6, period="5-6", semester="2024-2025-1",
        )
        db.add(agent_ai_schedule)
        db.flush()
        db.add(CourseCapacity(schedule_id=agent_ai_schedule.id, enrolled=0, capacity=30))
        db.flush()  # 获取自增 ID，供容量表使用

        # ===== Step 6: 插入课程容量（仅限选和选修课）=====
        # TRUNCATE 后 schedule 自增从 1 开始，限选课是第 5-8 条，选修课是第 9-10 条
        capacity_data = [
            {"schedule_id": 5, "enrolled": 0, "capacity": 50},   # Java程序设计（限选）
            {"schedule_id": 6, "enrolled": 0, "capacity": 50},   # Python数据分析（限选）
            {"schedule_id": 7, "enrolled": 0, "capacity": 50},   # 数据库原理（限选）
            {"schedule_id": 8, "enrolled": 0, "capacity": 50},   # 计算机网络（限选）
            {"schedule_id": 9, "enrolled": 0, "capacity": 30},   # 人工智能导论（选修）
            {"schedule_id": 10, "enrolled": 0, "capacity": 30},  # 摄影基础（选修）
        ]
        capacities = [CourseCapacity(**data) for data in capacity_data]
        db.add_all(capacities)
        db.flush()

        # ===== Step 7: 插入学生（20人）=====
        # 班级1: 10人 (S2024001~S2024010)
        # 班级2: 6人  (S2024011~S2024016)
        # 班级3: 4人  (S2024017~S2024020)
        student_names = [
            "赵晓明", "钱丽华", "孙志强", "李芳菲", "周建国",
            "吴美玲", "郑浩然", "王雪梅", "冯志远", "陈思雨",
            "褚博文", "卫晓燕", "蒋明辉", "沈佳琪", "韩志鹏",
            "杨雨桐", "朱文博", "秦思源", "许梦洁", "何浩然",
        ]
        students = []
        for i, name in enumerate(student_names):
            student_id = f"S2024{i + 1:03d}"
            if i < 10:
                cid = 1
            elif i < 16:
                cid = 2
            else:
                cid = 3
            students.append(Student(id=student_id, name=name, class_id=cid))
        db.add_all(students)
        # 智能体测试学生：agent01（用户名=学号，与全系统"username 即学号"的约定保持一致），密码固定 test123456
        db.add(Student(id="agent01", name="智能体测试员", class_id=1))

        # ===== Step 8: 插入后勤工人（2人）=====
        staff_data = [
            Staff(id="G10001", name="陈师傅", department="后勤管理处", job_type="维修"),
            Staff(id="G10002", name="黄阿姨", department="餐饮服务中心", job_type="餐饮"),
        ]
        db.add_all(staff_data)
        db.flush()

        # ===== Step 9: 创建用户认证账号（所有角色统一管理）=====
        # 每个账号生成随机密码，首次登录强制修改
        all_accounts = [
            # 管理员（2人）— role_id 用独立编号
            {"username": "admin01", "role": UserRole.admin, "role_id": "A001"},
            {"username": "admin02", "role": UserRole.admin, "role_id": "A002"},
            # 教师（5人）— username 和 role_id 均用工号
            {"username": "T10001", "role": UserRole.teacher, "role_id": "T10001"},
            {"username": "T10002", "role": UserRole.teacher, "role_id": "T10002"},
            {"username": "T10003", "role": UserRole.teacher, "role_id": "T10003"},
            {"username": "T10004", "role": UserRole.teacher, "role_id": "T10004"},
            {"username": "T10005", "role": UserRole.teacher, "role_id": "T10005"},
            # 学生（20人）— username 和 role_id 均用学号
            *[{"username": s.id, "role": UserRole.student, "role_id": s.id} for s in students],
            # 后勤（2人）— username 和 role_id 均用工号
            {"username": "G10001", "role": UserRole.staff, "role_id": "G10001"},
            {"username": "G10002", "role": UserRole.staff, "role_id": "G10002"},
        ]

        for account in all_accounts:
            plain_pwd = generate_password()
            credential = UserCredential(
                username=account["username"],
                password_hash=hash_password(plain_pwd),
                role=account["role"],
                role_id=account["role_id"],
                must_change_password=True,
            )
            db.add(credential)
            credentials.append({
                "username": account["username"],
                "password": plain_pwd,
                "role": account["role"].value,
            })

        # agent01：智能体测试专用账号，密码固定，首次登录不强制改密
        db.add(UserCredential(
            username="agent01",
            password_hash=hash_password("test123456"),
            role=UserRole.student,
            role_id="agent01",
            must_change_password=False,
        ))
        credentials.append({"username": "agent01", "password": "test123456", "role": "student"})

        # ===== Step 9.5: 插入系统配置 =====
        # 选课时间窗口和退课截止时间，datetime 格式 "YYYY-MM-DD HH:MM:SS"
        system_configs = [
            # 选课窗口常开（智能体/演示随时可测选课）
            SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
            SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
            SystemConfig(config_key="drop_deadline", config_value="2099-12-31 18:00:00"),
        ]
        db.add_all(system_configs)

        # ===== Step 9.6: 插入培养方案 =====
        plan_cs = TrainingPlan(
            major="计算机科学与技术", grade=2024,
            total_credits_required=170, elective_credits_required=20,
        )
        plan_se = TrainingPlan(
            major="软件工程", grade=2024,
            total_credits_required=170, elective_credits_required=20,
        )
        db.add_all([plan_cs, plan_se])
        db.flush()

        # 为CS2024方案添加课程映射
        plan_courses = []
        for plan_id in [plan_cs.id, plan_se.id]:
            courses = [
                # 必修课
                {"subject_id": 1, "course_type": "compulsory", "credit": 5.0},
                {"subject_id": 2, "course_type": "compulsory", "credit": 4.0},
                {"subject_id": 3, "course_type": "compulsory", "credit": 4.0},
                {"subject_id": 4, "course_type": "compulsory", "credit": 4.0},
                # 限选课 — CS_LTD_01（编程方向），至少选2门
                {"subject_id": 5, "course_type": "limited", "limited_group": "CS_LTD_01", "min_required": 2, "credit": 3.0},
                {"subject_id": 6, "course_type": "limited", "limited_group": "CS_LTD_01", "min_required": 2, "credit": 3.0},
                # 限选课 — CS_LTD_02（网络与数据库方向），至少选2门
                {"subject_id": 7, "course_type": "limited", "limited_group": "CS_LTD_02", "min_required": 2, "credit": 3.0},
                {"subject_id": 8, "course_type": "limited", "limited_group": "CS_LTD_02", "min_required": 2, "credit": 3.0},
                # 选修课
                {"subject_id": 9, "course_type": "elective", "credit": 2.0},
                {"subject_id": 10, "course_type": "elective", "credit": 1.0},
            ]
            for c in courses:
                plan_courses.append(PlanCourse(plan_id=plan_id, **c))
        db.add_all(plan_courses)

        # 一次性提交所有数据
        db.commit()
        print(f"数据初始化完成！共插入 {len(credentials)} 个用户账号\n")

    # ===== Step 10: 打印账号密码到控制台 =====
    # 不在 db session 内打印，避免 IO 阻塞占用数据库连接
    admin_accounts = [c for c in credentials if c["role"] == "admin"]
    teacher_accounts = [c for c in credentials if c["role"] == "teacher"]
    student_accounts = [c for c in credentials if c["role"] == "student"]
    staff_accounts = [c for c in credentials if c["role"] == "staff"]

    print("=" * 72)
    print("  账号密码列表（首次登录需修改密码）")
    print("=" * 72)
    print(f"\n  【管理员账号 ({len(admin_accounts)}个)】")
    print(f"  {'用户名':<14} {'密码':<16} {'角色'}")
    print(f"  {'─' * 14} {'─' * 16} {'─' * 8}")
    for c in admin_accounts:
        print(f"  {c['username']:<14} {c['password']:<16} {c['role']}")

    print(f"\n  【教师账号 ({len(teacher_accounts)}个)】")
    print(f"  {'用户名':<14} {'密码':<16} {'角色'}")
    print(f"  {'─' * 14} {'─' * 16} {'─' * 8}")
    for c in teacher_accounts:
        print(f"  {c['username']:<14} {c['password']:<16} {c['role']}")

    print(f"\n  【学生账号 ({len(student_accounts)}个)】")
    print(f"  {'用户名':<14} {'密码':<16} {'角色'}")
    print(f"  {'─' * 14} {'─' * 16} {'─' * 8}")
    for c in student_accounts:
        print(f"  {c['username']:<14} {c['password']:<16} {c['role']}")

    print(f"\n  【后勤账号 ({len(staff_accounts)}个)】")
    print(f"  {'用户名':<14} {'密码':<16} {'角色'}")
    print(f"  {'─' * 14} {'─' * 16} {'─' * 8}")
    for c in staff_accounts:
        print(f"  {c['username']:<14} {c['password']:<16} {c['role']}")

    print("\n" + "=" * 72)
    print("  提示：所有用户首次登录后必须修改密码")
    print("=" * 72)


if __name__ == "__main__":
    init_data()
