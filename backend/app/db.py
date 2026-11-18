"""database.py 连接层/数据库连接、会话与建表。

 DATABASE_URL 决定连接 SQLite 还是 MySQL；
 engine 管理连接池；
 SessionLocal 按请求创建 Session；
 get_session() / SessionDep 把 Session 注入路由函数；
 init_db() 在应用启动时创建缺失的表。
"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 设置默认库文件的地址在 backend/data 下，不受启动目录影响。
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def _database_url() -> str:
    """读取 DATABASE_URL；未配置时返回 backend/data/app.db 的 SQLite 连接串。

    默认路径用 __file__ 定位，避免从仓库根目录或 backend 目录启动时
    创建出两个不同的数据库文件。
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}"


def _connect_args(url: str) -> dict[str, object]:
    """按数据库类型生成驱动连接参数。

    - sqlite：check_same_thread=False 允许会话跨线程使用，timeout=15 缓解写锁冲突；
    - mysql：charset=utf8mb4 保证中文类别、商户名不乱码；
    - 其他数据库不额外传参。
    """
    if url.startswith("sqlite"):
        return {"check_same_thread": False, "timeout": 15}
    if url.startswith("mysql"):
        return {"charset": "utf8mb4"}
    return {}


# 模块导入时确定连接目标；修改环境变量后需要重启进程才能生效。
DATABASE_URL = _database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args(DATABASE_URL),
    # 取连接前先探活，避免拿到已经被数据库服务端关闭的连接。
    pool_pre_ping=True,
    # 回收周期要小于 MySQL 默认的 wait_timeout。
    pool_recycle=3600,
)

# autoflush=False 避免查询前隐式写入；expire_on_commit=False 让 commit 后仍能读取行属性。
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，models.py 中的表都继承它。

    init_db() 通过 Base.metadata 拿到全部表定义。
    """


def get_session() -> Iterator[Session]:
    """为单个请求创建 Session，请求结束后自动关闭。

    FastAPI 通过 SessionDep 注入；store.py 的函数接收这个 Session 执行 SQL。
    请求处理中如果抛异常，with 块退出时会回滚未提交的改动。
    """
    with SessionLocal() as session:
        yield session


# 路由参数写 session: SessionDep，FastAPI 会调用 get_session() 注入请求级 Session。
SessionDep = Annotated[Session, Depends(get_session)]


def init_db() -> None:
    """创建 models.py 中已定义、但数据库中尚不存在的表。

    只执行 create_all，不做字段迁移；已有表结构变化需要单独的迁移脚本。
    导入 models 是为了让 Base.metadata 收集到表定义。
    """
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
