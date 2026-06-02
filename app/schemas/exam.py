from pydantic import BaseModel, Field
from typing import Optional


class ExamGenerateRequest(BaseModel):
    semester: str = Field(default="2024-2025-1", description="学期")


class ExamItem(BaseModel):
    id: int
    subject_name: str
    classroom_name: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: int
    status: str
    student_count: int = 0
    invigilator_name: Optional[str] = None
    seat_no: Optional[int] = None
    semester: str = ""
    exam_type: str = "统一考试"


class ExamListResponse(BaseModel):
    exams: list[ExamItem]


class ExamGenerateResponse(BaseModel):
    message: str
    exam_count: int
    conflict_count: int
