"""本地开发启动入口：python run.py（等价于 uvicorn app.main:app --reload）。"""
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(Path(__file__).resolve().parent),
    )
