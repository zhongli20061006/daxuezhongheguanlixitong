"""教室查询模块的响应模型"""
from pydantic import BaseModel, Field


class ClassroomItem(BaseModel):
    """教室基本信息"""
    id: int
    name: str
    capacity: int
    building: str | None = None
    has_projector: bool = False

    class Config:
        from_attributes = True


class ClassroomAvailableResponse(BaseModel):
    """空闲教室列表"""
    classrooms: list[ClassroomItem]


class OccupiedDetail(BaseModel):
    """占用详情"""
    course_name: str
    teacher_name: str
    weeks: str
    day_of_week: int
    period: str


class ClassroomAvailabilityResponse(BaseModel):
    """单间教室空闲状态"""
    available: bool
    classroom: ClassroomItem | None = None
    occupied_by: OccupiedDetail | None = None
