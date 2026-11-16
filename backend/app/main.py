import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import activities, admin, admin_system, assistant, auth, clubs, intents, items, meta, notifications, posts, reports, upload
from app.core.config import settings
from app.core.exceptions import register_exception_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="校园二手交易与社团活动平台 API", version="0.1.0", docs_url="/docs")

register_exception_handlers(app)

# 静态上传目录：不存在时自动创建，否则 StaticFiles 会在启动时报错
upload_dir = settings.upload_path
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

app.include_router(meta.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(intents.router, prefix="/api")
app.include_router(clubs.router, prefix="/api")
app.include_router(clubs.application_router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(activities.club_router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(posts.admin_router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(reports.admin_router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_system.router, prefix="/api")


@app.get("/", tags=["系统"], summary="服务信息")
def root() -> dict[str, str]:
    return {"service": "campus-platform", "docs": "/docs"}
