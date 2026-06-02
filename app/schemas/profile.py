from pydantic import BaseModel, Field


class PhoneUpdateRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号，11位数字")
