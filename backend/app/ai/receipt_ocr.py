"""小票与支付截图的 OCR 接口。

输入图片字节，输出识别文本和结构化字段；字段含义与
schemas.transaction.TransactionDraft 一致：金额单位「分」，时间带时区，
无法识别的字段返回 None。
"""

from dataclasses import dataclass
from datetime import datetime

from app.schemas.transaction import Category


@dataclass(frozen=True)
class ReceiptRecognition:
    """一次小票识别的结果。

    raw_text 保留 OCR 原始文本，便于人工核对，也可作为规则抽取的输入。
    """

    raw_text: str | None
    amount_cents: int | None
    merchant: str | None
    occurred_at: datetime | None
    category: Category | None
    confidence: float


def recognize(image: bytes) -> ReceiptRecognition:
    """识别一张小票或支付截图。

    参数:
        image: 上传文件的内容字节，MIME 和大小已由接口层校验。

    返回:
        ReceiptRecognition：未识别字段为 None。

    当前未实现，调用会抛出 NotImplementedError。
    """
    raise NotImplementedError("小票 OCR 尚未接入")
