# AI 记账助手（AI Accounting Assistant）

广东金融学院第二十一组智能体项目。

面向个人记账场景的智能体：用户可以用一句话描述消费，或上传小票、支付截图；系统把内容转换为结构化账目，经确认后保存，并提供账目查询、分类统计与预算提醒。

后端接口与数据层已完成，Streamlit 前端已接入；AI 文本抽取、视觉识别和自然语言查询目前以规则实现为主，后续接入大模型替换。

## 技术栈

- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.x
- SQLite（本地开发）/ MySQL（生产环境）
- Uvicorn
- Streamlit（前端页面）

## 当前进度

版本：`v0.1.0`（2026-11）

- 已完成记账核心接口：一句话解析、保存账目、账目查询、分类统计。
- 已完成预算接口：按月设置总预算或类别预算，返回已用比例和超支状态。
- 数据层已从进程内存储迁移到 SQLAlchemy，默认使用 SQLite，预留 MySQL 连接配置。
- 接口统一使用 `snake_case`；金额以「分」为单位存储，时间统一使用 UTC。
- 错误响应统一为 `{code, message, detail}`，参数校验、404、405 使用同一结构。
- 已提供小票/支付截图上传接口，目前完成文件类型、大小校验和空草稿生成；OCR 接口留在 `backend/app/ai/receipt_ocr.py`。
- Streamlit 前端位于 `frontend/`，单文件覆盖记账、查账、统计三个功能区；预算页待补充。
- OpenAPI 契约可由 `backend/export_openapi.py` 导出；服务启动后可访问 `/docs` 查看交互式接口文档。

## 项目结构

```text
ai-Accounting-Assistant/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── main.py                 # 应用入口：初始化数据库、中间件、路由
│   │   ├── db.py                   # 数据库引擎、会话、建表
│   │   ├── models.py               # SQLAlchemy 表结构
│   │   ├── store.py                # 数据访问层：账目、草稿、预算的读写
│   │   ├── api/
│   │   │   ├── transactions.py     # 解析、保存、查询、删除账目
│   │   │   ├── receipts.py         # 小票/截图上传与草稿
│   │   │   ├── stats.py            # 分类统计
│   │   │   └── budgets.py          # 预算设置、查询与超支状态
│   │   ├── schemas/
│   │   │   ├── common.py           # 时间范围查询参数
│   │   │   ├── transaction.py      # 记账请求/响应与枚举
│   │   │   ├── stats.py            # 统计响应
│   │   │   ├── budget.py           # 预算请求/响应
│   │   │   └── meta.py             # 类别与健康检查响应
│   │   ├── ai/
│   │   │   ├── text_extract.py     # 文本抽取接口（待接入大模型）
│   │   │   └── receipt_ocr.py      # 小票 OCR 接口（待接入 OCR）
│   │   └── core/
│   │       └── errors.py           # 统一错误结构与异常处理
│   ├── export_openapi.py           # 导出 OpenAPI 契约
│   ├── requirements.txt
│   ├── .env.example                # 环境变量示例
│   └── Dockerfile
├── frontend/                       # 前端页面
│   ├── app.py                      # 单文件页面：记账、查账、统计三个功能区（预算页待补充）
│   ├── pyproject.toml              # 依赖声明（streamlit、pandas、altair、requests）
│   └── uv.lock                     # 依赖锁定
├── docs/                           # 接口文档
├── pyproject.toml                  # 后端依赖声明
└── uv.lock                         # 后端依赖锁定
```

## 启动方式

后端（端口 8000）：

```powershell
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端（端口 8501）：

```powershell
cd frontend
uv sync
uv run streamlit run app.py
```

## 待开发领域

| 领域 | 当前状态 | 计划 |
|---|---|---|
| 前端（Streamlit） | 单文件实现记账、查账、统计三个功能区；查账已接入真实接口 | 补充预算页，优化交互细节 |
| 账单删除 | 后端已提供 `DELETE /transactions/{id}`，前端暂未接入 | 前端改为调用删除接口并加二次确认 |
| 生产数据库 | 当前使用本地 SQLite，尚未接入 MySQL 实例 | 完成 MySQL 建库、字符集、索引和迁移脚本，接入生产数据库 |
| Docker 部署 | Dockerfile 已准备 | 完成镜像构建、容器编排、环境变量与数据卷联调 |
| AI 文本抽取 | 规则匹配，AI 接口已在 `ai/text_extract.py` 预留 | 接入大模型替换规则解析，补充抽取质量测试 |
| 小票/图片识别 | 上传校验与空草稿，OCR 接口已在 `ai/receipt_ocr.py` 预留 | 接入 OCR 或视觉模型，完成端到端测试 |
| 预算管理 | 后端已实现：按月设置总预算/类别预算并给出超支状态 | 前端预算页待补充，后续支持修改历史与提醒推送 |
| 自然语言查账 | 前端规则解析为类别/时间条件，再调查询与统计接口 | 接入大模型或后端自然语言端点 |
