"""导出 OpenAPI 契约文件，供 Apifox 导入。

用法（backend 目录）：
    python export_openapi.py

输出：docs/api/openapi.json
"""

import json
import os
from pathlib import Path

# db.py 在模块导入时读取 DATABASE_URL；这里兜底成内存 SQLite，
# 避免执行导出脚本时在 backend/data 下创建数据库文件。
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.main import app  # noqa: E402

# 相对 backend/export_openapi.py 定位到仓库的 docs/api 目录。
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.json"


def main() -> None:
    """调用 app.openapi() 生成契约并写入 OUTPUT。

    app.openapi() 只遍历已注册的路由和 Pydantic 模型，不连接数据库，
    因此导出结果只反映接口定义，不依赖当前数据库里有没有数据。
    """
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
