"""
个人中心接口
GET  /profile      — 获取个人信息+统计数据
PUT  /profile/phone — 修改手机号
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Teacher, Student, StudentClass, Staff, Subject, Schedule, CourseSelection, Score, ScoreType, LeaveApplication, Repair
from app.schemas.profile import PhoneUpdateRequest

router = APIRouter(prefix="/profile", tags=["个人中心"])


def mask_phone(phone):
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]


@router.get("", summary="获取个人信息")
async def get_profile(current_user=Depends(get_current_user), db=Depends(get_db)):
    uid = current_user["username"]
    role = current_user["role"]
    base = {"user_id": uid, "name": uid, "role": role}
    phone_raw = None
    stats = {}

    if role == "student":
        row = (await db.execute(select(Student, StudentClass).join(StudentClass, Student.class_id == StudentClass.id, isouter=True).where(Student.id == uid))).one_or_none()
        if row:
            stu, cls = row
            base["name"] = stu.name
            base["class_name"] = cls.name if cls else ""
            base["major"] = cls.major if cls else ""
            base["grade"] = cls.grade if cls else ""
            phone_raw = stu.phone
            if cls and cls.advisor_id:
                adv = (await db.execute(select(Teacher).where(Teacher.id == cls.advisor_id))).scalar_one_or_none()
                base["advisor_name"] = adv.name if adv else ""

            cr = (await db.execute(select(func.coalesce(func.sum(Subject.credit), 0)).select_from(CourseSelection).join(Schedule, CourseSelection.schedule_id == Schedule.id).join(Subject, Schedule.subject_id == Subject.id).where(CourseSelection.student_id == uid, CourseSelection.status == 1))).scalar()
            stats["已选学分"] = str(float(cr))
            gp = (await db.execute(select(func.avg(Score.gpa)).where(Score.student_id == uid, Score.score_type == ScoreType.total))).scalar()
            stats["平均绩点"] = str(round(float(gp), 1)) if gp else "0"
            lv = (await db.execute(select(func.count()).select_from(LeaveApplication).where(LeaveApplication.student_id == uid, LeaveApplication.status == "已通过"))).scalar()
            stats["请假通过"] = str(lv)
            rp = (await db.execute(select(func.count()).select_from(Repair).where(Repair.user_id == uid))).scalar()
            stats["报修次数"] = str(rp)

    elif role == "teacher":
        t = (await db.execute(select(Teacher).where(Teacher.job_number == uid))).scalar_one_or_none()
        if t:
            base["name"] = t.name; base["department"] = t.department or ""; base["title"] = t.title or ""; phone_raw = t.phone
            cnt = (await db.execute(select(func.count()).select_from(Schedule).where(Schedule.teacher_id == t.id))).scalar()
            stats["授课门数"] = str(cnt)
            cls_cnt = (await db.execute(select(func.count()).select_from(StudentClass).where(StudentClass.advisor_id == t.id))).scalar()
            stats["管理班级"] = str(cls_cnt)

    elif role == "staff":
        s = (await db.execute(select(Staff).where(Staff.id == uid))).scalar_one_or_none()
        if s:
            base["name"] = s.name; base["department"] = s.department or ""; base["job_type"] = s.job_type or ""; phone_raw = s.phone
            cnt = (await db.execute(select(func.count()).select_from(Repair).where(Repair.assigned_worker_id == uid, Repair.status.in_(["已接单", "处理中"])))).scalar()
            stats["待处理报修"] = str(cnt)

    elif role == "admin":
        base["name"] = "管理员"; base["role_name"] = "系统管理员"

    base["phone"] = mask_phone(phone_raw)
    base["phone_raw"] = phone_raw or ""
    base["statistics"] = stats
    return base


@router.put("/phone", summary="修改手机号")
async def update_phone(req: PhoneUpdateRequest, current_user=Depends(get_current_user), db=Depends(get_db)):
    phone = req.phone.strip()
    if not phone.isdigit() or len(phone) != 11 or not phone.startswith("1"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号格式不正确")
    uid = current_user["username"]
    role = current_user["role"]
    if role == "student":
        s = (await db.execute(select(Student).where(Student.id == uid))).scalar_one_or_none()
        if s: s.phone = phone
    elif role == "teacher":
        t = (await db.execute(select(Teacher).where(Teacher.job_number == uid))).scalar_one_or_none()
        if t: t.phone = phone
    elif role == "staff":
        s = (await db.execute(select(Staff).where(Staff.id == uid))).scalar_one_or_none()
        if s: s.phone = phone
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前角色不可修改手机号")
    await db.commit()
    return {"message": "手机号已更新", "phone": phone}
