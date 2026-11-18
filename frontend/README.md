# 前端（Streamlit）

单文件页面，对接 `backend/` 的 FastAPI 服务。

## 启动

先起后端（端口 8000）：

```powershell
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

再起页面（端口 8501）：

```powershell
cd frontend
uv sync
uv run streamlit run app.py
```

后端地址写在 `app.py` 顶部的 `API_URL`，默认 `http://127.0.0.1:8000`；
换地址时改这一处即可。

## 目录结构

```text
frontend/
├── app.py          # 单文件：侧边栏菜单 + 三个功能区
├── pyproject.toml  # 依赖：streamlit / pandas / altair / requests
└── uv.lock         # 依赖锁定
```

`app.py` 内部按功能区划分：

| 功能区 | 作用 |
|---|---|
| 一句话记账 | 文字解析、小票上传、预览确认后写入后端 |
| 自然语言查账 | 本地规则解析类别与时间范围，再调查询/统计接口 |
| 账单与统计 | 账目列表、格式校验、分类柱状图与饼图 |

预算管理页尚未实现，后端接口已就绪，待补充。

## 页面与接口

| 功能区 | 调用 |
|---|---|
| 一句话记账 | `POST /transactions/parse`、`POST /receipts/parse`、`POST /transactions` |
| 自然语言查账 | 前端规则解析后调 `GET /transactions` 或 `GET /stats/category` |
| 账单与统计 | `GET /transactions`、`GET /stats/category` |
| 类别下拉框 | 内置 7 个类别，与后端枚举保持一致 |

## 数据约定

- 页面按「元」输入和展示，提交时转成整数「分」；
- 消费日期提交为当天 0 点 +08:00，后端统一转 UTC 存储；
- 查账列表把后端返回的 UTC 时间转成 `Asia/Shanghai` 再显示日期；
- 后端未启动时页面显示本地演示数据，接口恢复后自动读取真实数据。

## 当前状态

- 记账、查账、统计三个功能区可用；查询页已接真实接口。
- 删除账单目前只删本地列表，后端已提供 `DELETE /transactions/{id}`，待接入。
- 小票 OCR 与 AI 文本抽取的接口定义在 `backend/app/ai/`，尚未实现，小票上传后返回空草稿，需手动补全。
