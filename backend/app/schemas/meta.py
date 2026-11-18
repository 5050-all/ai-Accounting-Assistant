"""基础数据和健康检查的响应模型。

- CategoryOption 对应 GET /categories 的列表项；
- HealthResponse 对应 GET /health 的响应。
"""

from pydantic import BaseModel, Field

from app.schemas.transaction import Category


class CategoryOption(BaseModel):
    """GET /categories 返回的一项。

    value 是 Category 枚举值，label 是展示文案；
    当前两者都取中文类别名，前端下拉框直接使用。
    """

    value: Category = Field(..., description="类别取值")
    label: str = Field(..., description="展示文案")


class HealthResponse(BaseModel):
    """GET /health 的响应。

    status 固定为 ok；version 来自 FastAPI 应用的 version 字段。
    """

    status: str = Field(..., description="固定为 ok")
    version: str = Field(..., description="应用版本号")
