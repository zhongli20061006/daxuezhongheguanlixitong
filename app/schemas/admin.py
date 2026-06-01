"""管理端模块的请求/响应模型"""
from pydantic import BaseModel, Field


class SelectionWindowRequest(BaseModel):
    """设置选课时间窗口"""
    selection_start_time: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        description="选课开始时间，格式 YYYY-MM-DD HH:MM:SS"
    )
    selection_end_time: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        description="选课结束时间，格式 YYYY-MM-DD HH:MM:SS"
    )
    drop_deadline: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        description="退课截止时间，格式 YYYY-MM-DD HH:MM:SS"
    )


class SelectionWindowResponse(BaseModel):
    """当前选课窗口配置"""
    selection_start_time: str | None = None
    selection_end_time: str | None = None
    drop_deadline: str | None = None


class CapacityUpdateRequest(BaseModel):
    """修改课程容量"""
    capacity: int = Field(..., ge=1, description="新容量（≥1）")


class ResetPasswordRequest(BaseModel):
    """重置密码"""
    new_password: str = Field(..., min_length=6, max_length=128)


class UserItem(BaseModel):
    """用户条目"""
    id: int
    username: str
    role: str
    role_id: str
    must_change_password: bool
    created_at: str

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表"""
    users: list[UserItem]
