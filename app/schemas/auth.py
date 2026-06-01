"""认证模块的 Pydantic 请求/响应模型"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名（学号或工号）")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
    role: str = Field(..., description="用户角色")
    must_change_password: bool = Field(..., description="是否必须修改密码")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码，至少6位")
