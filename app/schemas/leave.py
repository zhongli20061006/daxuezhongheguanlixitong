from pydantic import BaseModel, Field
from typing import Optional


class LeaveApplyRequest(BaseModel):
    start_date: str = Field(..., description="开始日期，格式YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期，格式YYYY-MM-DD")
    reason: str = Field(..., min_length=1, max_length=500, description="请假原因")


class ApprovalRequest(BaseModel):
    leave_id: int = Field(..., description="请假申请ID")
    result: str = Field(..., pattern="^(通过|驳回)$", description="审批结果：通过/驳回")
    comment: Optional[str] = Field(None, description="审批意见")


class LeaveItem(BaseModel):
    id: int
    student_id: str
    student_name: Optional[str] = None
    start_date: str
    end_date: str
    total_days: int
    reason: str
    status: str
    submit_time: str


class LeaveListResponse(BaseModel):
    leaves: list[LeaveItem]


class ApprovalRecordItem(BaseModel):
    id: int
    leave_id: int
    approver_id: str
    approver_role: str
    level: int
    result: str
    comment: Optional[str] = None
    created_at: str


class LeaveDetailResponse(BaseModel):
    leave: LeaveItem
    approvals: list[ApprovalRecordItem]
