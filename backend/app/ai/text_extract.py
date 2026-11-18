"""一句话记账的文本抽取接口。

输入用户输入的自然语言，输出结构化的支出字段；字段含义与
schemas.transaction.TransactionDraft 一致：金额单位「分」，时间带时区，
无法识别的字段返回 None。
"""

from dataclasses import dataclass
from datetime import datetime

from app.schemas.transaction import Category


@dataclass(frozen=True)
class ExpenseExtraction:
    """一次文本抽取的结果。

    missing_fields 不在这里计算，接口层会根据值为 None 的字段自动得出。
    """

    amount_cents: int | None
    merchant: str | None
    occurred_at: datetime | None
    category: Category | None
    confidence: float


def extract(text: str) -> ExpenseExtraction:
    """把一句话解析成结构化支出。

    参数:
        text: 用户输入的自然语言，已去除首尾空格，长度 1~200。

    返回:
        ExpenseExtraction：未识别字段为 None。

    当前未实现，调用会抛出 NotImplementedError。
    """
    raise NotImplementedError("AI 文本抽取尚未接入")
