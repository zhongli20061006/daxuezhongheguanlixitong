"""课表模块的请求/响应模型"""
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    """课表条目"""
    id: int
    course_name: str
    teacher_name: str
    classroom_name: str
    day_of_week: int
    period: str
    weeks: str
    course_type: str
    credit: float

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """课表列表"""
    schedules: list[ScheduleItem]


class ScheduleCreateRequest(BaseModel):
    """创建课表（管理员）"""
    teacher_id: int = Field(..., gt=0)
    subject_id: int = Field(..., gt=0)
    class_id: int = Field(..., gt=0)
    classroom_id: int = Field(..., gt=0)
    weeks: str = Field(..., min_length=1, max_length=20)
    day_of_week: int = Field(..., ge=1, le=7)
    period: str = Field(..., min_length=1, max_length=10)
    semester: str = Field(..., min_length=1, max_length=20)


class ScheduleUpdateRequest(BaseModel):
    """更新课表（管理员，所有字段可选）"""
    teacher_id: int | None = Field(None, gt=0)
    subject_id: int | None = Field(None, gt=0)
    class_id: int | None = Field(None, gt=0)
    classroom_id: int | None = Field(None, gt=0)
    weeks: str | None = Field(None, min_length=1, max_length=20)
    day_of_week: int | None = Field(None, ge=1, le=7)
    period: str | None = Field(None, min_length=1, max_length=10)
    semester: str | None = Field(None, min_length=1, max_length=20)
