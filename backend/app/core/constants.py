"""全项目共用的业务常量。改这里即可同步影响校验、字典接口和种子数据。"""
from typing import Literal, get_args

# 校区：库里直接存中文名称
CampusArea = Literal["黄埔校区", "琶洲校区"]
CAMPUS_AREAS: list[str] = list(get_args(CampusArea))
