from pydantic import BaseModel, Field
from typing import Optional


class TrainingPlanCreate(BaseModel):
    major: str = Field(..., min_length=1, description="专业名称")
    grade: int = Field(..., gt=2000, description="入学年级")
    total_credits_required: float = Field(..., gt=0, description="总学分要求")
    elective_credits_required: float = Field(..., ge=0, description="选修学分要求")


class PlanCourseCreate(BaseModel):
    plan_id: int = Field(..., description="方案ID")
    subject_id: int = Field(..., description="科目ID")
    course_type: str = Field(..., description="课程类型：compulsory/limited/elective")
    limited_group: Optional[str] = Field(None, description="限选组名")
    min_required: Optional[int] = Field(None, description="限选组至少选几门")
    credit: float = Field(..., gt=0, description="学分")


class PlanItem(BaseModel):
    id: int
    major: str
    grade: int
    total_credits_required: float
    elective_credits_required: float


class PlanCourseItem(BaseModel):
    id: int
    plan_id: int
    subject_id: int
    subject_name: Optional[str] = None
    course_type: str
    limited_group: Optional[str] = None
    min_required: Optional[int] = None
    credit: float


class PlanListResponse(BaseModel):
    plans: list[PlanItem]


class PlanCourseListResponse(BaseModel):
    courses: list[PlanCourseItem]


class GraduationAuditRequest(BaseModel):
    student_id: str = Field(..., description="学号")


class AuditItem(BaseModel):
    id: int
    student_id: str
    student_name: Optional[str] = None
    plan_id: int
    major: Optional[str] = None
    total_credits_earned: float
    total_credits_required: float
    elective_credits_earned: float
    elective_credits_required: float
    compulsory_passed: int
    compulsory_total: int
    limited_groups_passed: Optional[str] = None
    is_graduatable: bool
    detail: Optional[str] = None
    updated_at: str


class AuditListResponse(BaseModel):
    audits: list[AuditItem]
