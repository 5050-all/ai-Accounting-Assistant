"""预算相关的请求与响应模型。

预算按「月份 + 类别」唯一，category 为 null 表示整月总预算。
金额单位与其他接口一致：整数「分」。
"""

import re

from pydantic import BaseModel, Field, field_validator

from app.schemas.transaction import Category

# 月份只接受 YYYY-MM，避免把任意字符串写进 budgets.month。
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class BudgetUpsertRequest(BaseModel):
    """PUT /budgets 的请求体。

    同一个 month + category 重复提交时覆盖原金额，不新增行。
    """

    month: str = Field(..., description="月份，格式 YYYY-MM", examples=["2026-11"])
    category: Category | None = Field(None, description="类别；null 表示整月总预算")
    amount_cents: int = Field(..., gt=0, description="预算金额，单位「分」，必须大于 0")

    @field_validator("month")
    @classmethod
    def _check_month(cls, value: str) -> str:
        """拦截 2026-13、2026-1 之类的非法月份。"""
        if not _MONTH_PATTERN.fullmatch(value):
            raise ValueError("month 格式必须是 YYYY-MM")
        return value


class BudgetItem(BaseModel):
    """一条预算本身，PUT 的响应。"""

    id: int = Field(..., description="预算 id，删除时使用")
    month: str = Field(..., description="月份，YYYY-MM")
    category: Category | None = Field(None, description="类别；null 表示整月总预算")
    amount_cents: int = Field(..., description="预算金额，单位「分」")


class BudgetStatus(BaseModel):
    """预算 + 当月实际支出 + 使用状态，GET /budgets 的列表项。"""

    id: int = Field(..., description="预算 id")
    category: Category | None = Field(None, description="类别；null 表示整月总预算")
    amount_cents: int = Field(..., description="预算金额，单位「分」")
    spent_cents: int = Field(..., description="当月已支出，单位「分」")
    ratio: float = Field(..., ge=0.0, description="已用比例，可能大于 1")
    status: str = Field(..., description="normal=正常，warning=接近上限，exceeded=已超支")


class BudgetOverview(BaseModel):
    """GET /budgets 的响应。

    items 中总预算行（category 为 null）排在最前，其后按类别枚举顺序排列；
    spent_cents 是当月全部类别的总支出，供页面显示整体情况。
    """

    month: str = Field(..., description="月份，YYYY-MM")
    spent_cents: int = Field(..., description="当月总支出，单位「分」")
    items: list[BudgetStatus] = Field(..., description="预算列表，总预算行在前")
