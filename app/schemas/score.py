"""考核模块的请求/响应模型"""
from pydantic import BaseModel, Field


class ScoreEntry(BaseModel):
    """单条成绩录入项"""
    student_id: str = Field(..., min_length=1, description="学号")
    score: float = Field(..., ge=0, le=100, description="百分制分数 (0~100)")


class ManualScoreRequest(BaseModel):
    """手动录入成绩请求"""
    schedule_id: int = Field(..., gt=0, description="课表ID")
    score_type: str = Field(..., pattern=r"^(平时|期末)$", description="成绩类型：平时/期末")
    scores: list[ScoreEntry] = Field(..., min_length=1, description="成绩列表")


class ManualScoreResponse(BaseModel):
    """录入结果"""
    inserted: int = Field(..., description="成功录入条数")
    updated: int = Field(0, description="更新条数（已有记录）")
    calculated: int = Field(0, description="已计算总评的学生数")


class ImportScoreResponse(BaseModel):
    """Excel导入结果"""
    success_count: int
    warnings: list[str] = []
    calculated: int = 0


class ScoreItem(BaseModel):
    """成绩条目"""
    id: int
    course_name: str
    credit: float
    score: float | None = None
    gpa: float
    score_type: str
    attempt: int
    updated_at: str

    class Config:
        from_attributes = True


class StudentScoresResponse(BaseModel):
    """学生成绩汇总"""
    student_id: str
    scores: list[ScoreItem]
