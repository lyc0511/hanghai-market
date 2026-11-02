from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class EnumsOut(BaseModel):
    content_type: dict[str, str]
    content_status: dict[str, str]
    item_condition: dict[str, str]
    club_type: dict[str, str]
    intent_status: dict[str, str]
    report_reason: dict[str, str]
    campus_area: list[str]
