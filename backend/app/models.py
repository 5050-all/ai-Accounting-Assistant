"""SQLAlchemy 表结构。

- transactions：已确认的账目，供查询和统计；
- transaction_drafts：待确认的解析草稿，保存账目时删除。

金额统一用整数「分」；occurred_at / created_at 由 UTCDateTime 按 UTC 存取。
"""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.schemas.transaction import Category, Source


class UTCDateTime(TypeDecorator[datetime]):
    """把 datetime 统一按 UTC 存储和读取。

    SQLite / MySQL 的 DATETIME 不保存时区：
    - 写入前要求 value 带时区，并转换成 UTC；
    - 读回 naive datetime 时补上 UTC，保证接口始终返回带时区的时间。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """写库前调用：校验时区并转换为 UTC。

        value 为 None 时原样返回；无时区时抛 ValueError，
        避免把本地时间当成 UTC 直接写入。
        """
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("时间必须带时区")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """读库后调用：给 naive datetime 补上 UTC 时区。"""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def _enum_column(enum_type: type[Enum]) -> SAEnum:
    """构造枚举列：数据库存枚举的 value 文本。

    Category 存中文（餐饮、交通等），Source 存 text/receipt/manual。
    native_enum=False 让 SQLite/MySQL 都使用 VARCHAR，避免原生枚举的迁移成本。
    """
    return SAEnum(
        enum_type,
        native_enum=False,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class TransactionORM(Base):
    """对应 transactions 表，保存已确认的账目。

    字段与 schemas.transaction.Transaction 一一对应；
    写入入口是 store.create_transaction()，读取入口是 store.list_transactions()。
    """

    __tablename__ = "transactions"
    __table_args__ = (
        # 数据库层兜底金额必须为正；API 层还有 Pydantic gt=0 校验。
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        # 按类别 + 时间筛选/统计时使用。
        Index("ix_transactions_category_occurred", "category", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    merchant: Mapped[str] = mapped_column(String(100), nullable=False)
    # occurred_at / created_at 都通过 UTCDateTime 按 UTC 存取。
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    # 存 Category 枚举的 value（中文），不是 Python 枚举名。
    category: Mapped[Category] = mapped_column(_enum_column(Category), nullable=False)
    # 存 Source 枚举的 value（text/receipt/manual）。
    source: Mapped[Source] = mapped_column(_enum_column(Source), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class TransactionDraftORM(Base):
    """对应 transaction_drafts 表，保存待确认的解析草稿。

    store.save_draft() 写入；store.create_transaction() 保存账目时按 draft_id
    读取并删除对应行。字段与 schemas.transaction.TransactionDraft 对应。
    """

    __tablename__ = "transaction_drafts"

    # draft_id 由 store.new_draft_id() 生成，同时作为接口返回的 draft_id。
    draft_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[Source] = mapped_column(_enum_column(Source), nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer)
    merchant: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    category: Mapped[Category | None] = mapped_column(_enum_column(Category))
    # 规则解析固定为 0.4；视觉模型接入后使用模型返回的置信度。
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # JSON 数组，元素是未识别字段名，和接口的 missing_fields 一致。
    missing_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # 原始输入文本；小票识别暂未写入，保持 None。
    raw_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class BudgetORM(Base):
    """对应 budgets 表，保存按月、按类别的预算。

    唯一键是 (month, category)：同一月份同一类别只有一条预算。
    category 用空字符串表示整月总预算，而不是 NULL——SQLite 的唯一约束
    把多个 NULL 视为互不相同，用 NULL 会插出重复的总预算行。
    """

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("month", "category", name="uq_budgets_month_category"),
        # 预算金额必须为正；接口层还有 Pydantic gt=0 校验。
        CheckConstraint("amount_cents > 0", name="ck_budgets_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 月份格式 YYYY-MM，例如 2026-11。
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    # 空字符串表示总预算，其余存 Category 的中文值。
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # 最近一次设置的 UTC 时间；upsert 时更新。
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
