"""查询参数共用的时间范围模型。

GET /transactions 和 GET /stats/category 都用 DateRangeQuery：
FastAPI 把 query string 的 from / to 解析成 datetime，
本模块负责校验时区、转换为 UTC，并保证起始时间不晚于结束时间。
"""

from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def ensure_utc(value: datetime) -> datetime:
    """校验 datetime 带时区，并转换为 UTC。

    参数:
        value: schema 解析出的 datetime，必须带 tzinfo。

    返回:
        UTC 时区的 datetime。

    异常:
        无时区或 utcoffset 为空时抛 ValueError；
        FastAPI 会把 ValueError 包装成 RequestValidationError，最终返回 422。
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须带时区，例如 2026-11-01T00:00:00+08:00")
    return value.astimezone(UTC)


class DateRangeQuery(BaseModel):
    """from / to 时间范围参数。

    字段名 date_from / date_to 在 SQL 中分别对应 >= / <=，
    对外 alias 保持 from / to，与接口文档一致。
    两个参数都可选；校验后可直接和数据库中的 UTC 时间比较。
    """

    model_config = ConfigDict(populate_by_name=True)

    date_from: datetime | None = Field(None, alias="from", description="起始时间（含）")
    date_to: datetime | None = Field(None, alias="to", description="结束时间（含）")

    @field_validator("date_from", "date_to")
    @classmethod
    def _normalize(cls, value: datetime | None) -> datetime | None:
        """把每个非空时间转成 UTC；None 原样返回。"""
        return None if value is None else ensure_utc(value)

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        """校验起始时间不晚于结束时间。

        from > to 时直接报 422，避免返回空列表让调用方误以为没有数据。
        """
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("from 不能晚于 to")
        return self
