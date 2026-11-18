"""AI 能力接口。

- text_extract：一句话 -> 结构化支出字段；
- receipt_ocr：小票/截图 -> 文本与结构化支出字段。

返回结构中的字段与 schemas.transaction.TransactionDraft 保持一致，
调用方拿到结果后可直接组装草稿。
"""

from app.ai.receipt_ocr import ReceiptRecognition, recognize
from app.ai.text_extract import ExpenseExtraction, extract

__all__ = [
    "ExpenseExtraction",
    "ReceiptRecognition",
    "extract",
    "recognize",
]
