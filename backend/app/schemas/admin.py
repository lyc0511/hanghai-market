from pydantic import BaseModel, Field, field_validator


class RejectIn(BaseModel):
    reason: str = Field(description="驳回原因，2–200 字，会通知给卖家")

    @field_validator("reason")
    @classmethod
    def check_reason(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 200:
            raise ValueError("驳回原因应为 2–200 个字")
        return v
