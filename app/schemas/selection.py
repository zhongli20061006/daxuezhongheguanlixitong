"""选课模块的请求/响应模型"""
from pydantic import BaseModel, Field


class EnrollResponse(BaseModel):
    """选课成功响应"""
    message: str
    schedule_id: int


class DropResponse(BaseModel):
    """退课成功响应"""
    message: str


class CourseItem(BaseModel):
    """课程条目（学生视角）"""
    selection_id: int
    schedule_id: int
    course_name: str
    teacher_name: str
    classroom_name: str
    day_of_week: int
    period: str
    weeks: str
    credit: float
    course_type: str

    class Config:
        from_attributes = True


class TeacherCourseItem(BaseModel):
    """课程条目（教师视角：含学生信息）"""
    selection_id: int
    schedule_id: int
    course_name: str
    student_id: str
    student_name: str
    day_of_week: int
    period: str
    weeks: str
    credit: float
    course_type: str

    class Config:
        from_attributes = True


class MyCoursesStudentResponse(BaseModel):
    """学生：我的选课列表"""
    courses: list[CourseItem]


class MyCoursesTeacherResponse(BaseModel):
    """教师：我的课程选课学生名单"""
    courses: list[TeacherCourseItem]


class AvailableCourseItem(BaseModel):
    """可选课程条目"""
    schedule_id: int
    course_name: str
    teacher_name: str
    classroom_name: str
    day_of_week: int
    period: str
    weeks: str
    credit: float
    course_type: str
    enrolled: int = 0
    capacity: int = 0
    selected: bool = False

    class Config:
        from_attributes = True


class AvailableCoursesResponse(BaseModel):
    """可选课程列表"""
    courses: list[AvailableCourseItem]
