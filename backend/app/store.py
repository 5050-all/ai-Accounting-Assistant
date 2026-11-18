"""数据访问层：账目与解析草稿的读写。

api/*.py 只通过 SessionDep 拿到 Session，所有 SQL 都调用这里：
- save_draft()        INSERT transaction_drafts
- create_transaction() 查询/删除草稿 + INSERT transactions，同一次 commit
- list_transactions()  COUNT + SELECT transactions
- category_totals()    GROUP BY category 聚合

这些函数接收调用方传入的 Session，不创建 Session，也不处理 HTTP 状态码。
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BudgetORM, TransactionDraftORM, TransactionORM
from app.schemas.transaction import Category, Source, Transaction, TransactionDraft


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    """store.category_totals() 的聚合结果行。

    api/stats.py 用它组装 CategoryStat，并计算 ratio。
    """

    category: Category
    total_cents: int
    count: int


def new_draft_id() -> str:
    """生成 32 位 uuid4 hex，作为 transaction_drafts.draft_id 和接口 draft_id。"""
    return uuid4().hex


def save_draft(session: Session, draft: TransactionDraft) -> TransactionDraft:
    """把 TransactionDraft 写入 transaction_drafts 并提交。

    参数:
        session: 请求级 Session。
        draft: api 层构造的草稿，字段与 TransactionDraftORM 一一对应。

    返回:
        传入的 draft 本身；调用方直接作为响应返回。

    副作用:
        session.add() + commit() 后草稿行落库，created_at 使用当前 UTC 时间。
    """
    row = TransactionDraftORM(
        draft_id=draft.draft_id,
        source=draft.source,
        amount_cents=draft.amount_cents,
        merchant=draft.merchant,
        occurred_at=draft.occurred_at,
        category=draft.category,
        confidence=draft.confidence,
        missing_fields=draft.missing_fields,
        raw_text=draft.raw_text,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.commit()
    return draft


def create_transaction(
    session: Session,
    *,
    amount_cents: int,
    merchant: str,
    occurred_at: datetime,
    category: Category,
    source: Source | None = None,
    note: str | None = None,
    draft_id: str | None = None,
) -> Transaction:
    """保存一笔账，并处理 draft_id 对应的草稿。

    参数:
        session: 请求级 Session。
        amount_cents / merchant / occurred_at / category: 已由 CreateTransactionRequest 校验。
        source: 请求显式指定的来源；为 None 时尝试从草稿读取，最后回退 manual。
        note: 备注，可为 None。
        draft_id: 草稿 id；对应行存在时读取 source 并删除。

    返回:
        Transaction：commit + refresh 后的 ORM 行转换而来，包含自增 id 和 created_at。

    事务:
        查询草稿、删除草稿、插入账目在同一次 commit 中完成；
        插入失败时草稿删除也会回滚。
    """
    if draft_id:
        # 只有请求带了 draft_id 才查草稿；查不到时按普通账目处理，不报错。
        draft = session.get(TransactionDraftORM, draft_id)
        if draft is not None:
            # 请求显式传了 source 就优先用它，否则继承草稿的 source。
            source = source or draft.source
            session.delete(draft)

    row = TransactionORM(
        amount_cents=amount_cents,
        merchant=merchant,
        occurred_at=occurred_at,
        category=category,
        # 没有草稿且请求没传 source 时，视为手工录入。
        source=source or Source.MANUAL,
        note=note,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.commit()
    # refresh 读取数据库生成的自增 id 和 created_at，再转成 Pydantic 响应模型。
    session.refresh(row)
    return Transaction.model_validate(row)


def delete_transaction(session: Session, transaction_id: int) -> bool:
    """按 id 删除一笔账目。

    参数:
        session: 请求级 Session。
        transaction_id: transactions.id；不存在时不做任何写入。

    返回:
        True 表示删除成功；False 表示 id 不存在。

    事务:
        单条 DELETE，commit 后立即生效；草稿表不受影响。
    """
    row = session.get(TransactionORM, transaction_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def list_transactions(
    session: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    category: Category | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    """按时间和类别筛选 transactions，返回当前页与总数。

    参数:
        date_from / date_to: 可选的时间边界，已转 UTC；
                             分别对应 occurred_at >= date_from 和 <= date_to。
        category: 可选类别，对应 category = category。
        limit / offset: 分页参数，由 TransactionQuery 限制 limit 1~100、offset >= 0。

    返回:
        (当前页 Transaction 列表, 符合筛选条件的总条数)。

    SQL:
        先 COUNT(*) 得到 total，再执行带排序和分页的 SELECT；
        排序为 occurred_at DESC, id DESC，保证同一时间的账目分页稳定。
    """
    # filters 收集非空条件，COUNT 和 SELECT 复用同一组条件。
    filters = []
    if date_from is not None:
        filters.append(TransactionORM.occurred_at >= date_from)
    if date_to is not None:
        filters.append(TransactionORM.occurred_at <= date_to)
    if category is not None:
        filters.append(TransactionORM.category == category)

    # total 是筛选后的总条数，不是当前页条数。
    total = session.scalar(
        select(func.count()).select_from(TransactionORM).where(*filters)
    ) or 0
    rows = session.scalars(
        select(TransactionORM)
        .where(*filters)
        # id 作为次级排序，保证同一时间的账目分页时顺序稳定。
        .order_by(TransactionORM.occurred_at.desc(), TransactionORM.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    # ORM 行逐条转成 Pydantic 响应模型，避免把 SQLAlchemy 对象暴露给 API 层。
    return [Transaction.model_validate(row) for row in rows], total


def category_totals(
    session: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[CategoryTotal], int]:
    """按 category 聚合 transactions，返回各类汇总和总支出。

    参数:
        date_from / date_to: 可选的时间边界，已转 UTC。

    返回:
        (CategoryTotal 列表, 总支出分)。列表按 total_cents 降序；
        没有数据时返回 ([], 0)。

    SQL:
        SELECT category, SUM(amount_cents), COUNT(id)
        ... GROUP BY category
        api/stats.py 用这些行计算 ratio。
    """
    filters = []
    if date_from is not None:
        filters.append(TransactionORM.occurred_at >= date_from)
    if date_to is not None:
        filters.append(TransactionORM.occurred_at <= date_to)

    rows = session.execute(
        select(
            TransactionORM.category,
            func.sum(TransactionORM.amount_cents),
            func.count(TransactionORM.id),
        )
        .where(*filters)
        .group_by(TransactionORM.category)
    ).all()

    # 数据库返回的是 Row，这里转成不可变的 CategoryTotal，并统一整数类型。
    items = [
        CategoryTotal(
            category=category,
            total_cents=int(total or 0),
            count=int(count),
        )
        for category, total, count in rows
    ]
    # 接口约定 items 按金额从高到低排序，排序放在 store 层统一处理。
    items.sort(key=lambda item: item.total_cents, reverse=True)
    return items, sum(item.total_cents for item in items)


def list_budgets(session: Session, month: str) -> list[BudgetORM]:
    """读取某个月的全部预算行。

    参数:
        session: 请求级 Session。
        month: 月份，格式 YYYY-MM。

    返回:
        BudgetORM 列表；排序（总预算在前）由 api/budgets.py 负责。
    """
    return list(session.scalars(select(BudgetORM).where(BudgetORM.month == month)))


def upsert_budget(
    session: Session,
    *,
    month: str,
    category: str,
    amount_cents: int,
) -> BudgetORM:
    """按 month + category 写入或更新一条预算。

    参数:
        session: 请求级 Session。
        month: 月份，格式 YYYY-MM。
        category: 类别中文值；空字符串表示整月总预算。
        amount_cents: 预算金额，单位「分」，已由请求模型确保大于 0。

    返回:
        commit + refresh 后的 ORM 行，包含自增 id。
    """
    row = session.scalar(
        select(BudgetORM).where(
            BudgetORM.month == month,
            BudgetORM.category == category,
        )
    )
    now = datetime.now(UTC)
    if row is None:
        row = BudgetORM(
            month=month,
            category=category,
            amount_cents=amount_cents,
            updated_at=now,
        )
        session.add(row)
    else:
        row.amount_cents = amount_cents
        row.updated_at = now
    session.commit()
    session.refresh(row)
    return row


def delete_budget(session: Session, budget_id: int) -> bool:
    """删除一条预算。

    返回:
        True 表示删除成功；False 表示 id 不存在。
    """
    row = session.get(BudgetORM, budget_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
