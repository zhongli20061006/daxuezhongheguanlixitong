"""后勤报修模块的请求/响应模型"""
from pydantic import BaseModel, Field


class RepairCreateRequest(BaseModel):
    """创建报修请求"""
    location: str = Field(..., min_length=1, max_length=200, description="报修地点")
    type: str = Field(
        ..., pattern=r"^(水电设备|电子产品|家具类|教学用具)$", description="报修类型"
    )
    description: str = Field(..., min_length=1, description="问题详细描述")


class RepairStatusUpdateRequest(BaseModel):
    """更新报修状态请求"""
    status: str = Field(
        ..., pattern=r"^(已接单|处理中|已完成|已确认|已取消)$", description="新状态"
    )


class RepairItem(BaseModel):
    """报修记录"""
    id: int
    user_id: str
    role: str
    location: str
    type: str
    description: str
    status: str
    assigned_worker_id: str | None = None
    submit_time: str
    accept_time: str | None = None
    complete_time: str | None = None
    confirm_time: str | None = None
    cancel_time: str | None = None

    class Config:
        from_attributes = True


class RepairListResponse(BaseModel):
    """报修列表"""
    repairs: list[RepairItem]
