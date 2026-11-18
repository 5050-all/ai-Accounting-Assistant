"""分类统计的响应模型，供 GET /stats/category 使用。

store.category_totals() 返回 CategoryTotal 聚合行，
api/stats.py 再转换成 CategoryStat，并补上 ratio。
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.transaction import Category


class CategoryStat(BaseModel):
    """单个类别的聚合结果。

    category / total_cents / count 来自 store.CategoryTotal；
    ratio 由 api/stats.py 用该类金额除以总金额计算。
    """

    category: Category
    total_cents: int = Field(..., description="该类总支出，单位「分」")
    count: int = Field(..., description="该类笔数")
    ratio: float = Field(..., ge=0.0, le=1.0, description="占总支出比例，0~1")


class CategoryStatsResponse(BaseModel):
    """分类统计接口的完整响应。

    date_from / date_to 是经过 UTC 转换后的查询边界；
    total_cents 是范围内总支出；items 已按 total_cents 降序排列。
    """

    date_from: datetime | None = Field(None, description="统计起始（含），null 表示不限")
    date_to: datetime | None = Field(None, description="统计结束（含），null 表示不限")
    total_cents: int = Field(..., description="总支出，单位「分」")
    items: list[CategoryStat] = Field(..., description="按金额从高到低排序")
