"""记账助手后端。

分层结构：
    api/      路由层，负责参数校验与响应组装
    schemas/  Pydantic 模型，同时作为 OpenAPI 契约来源
    core/     错误处理等横切逻辑
    db.py     数据库连接与会话
    models.py 数据库表结构
    store.py  数据访问层
"""
