"""图片上传：保存到 UPLOAD_DIR/年月/随机名，返回相对路径和完整访问地址。

业务错误码：
    41301 文件超过大小限制    41501 不支持的图片格式
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import BizError
from app.models import User
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/upload", tags=["上传"])

# 按文件头的「魔数」判断真实格式，不相信客户端传来的扩展名和 Content-Type
MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
]


def detect_image_type(head: bytes) -> str | None:
    for magic, ext in MAGIC_SIGNATURES:
        if head.startswith(magic):
            return ext
    # WebP：RIFF....WEBP
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def public_url(path: str) -> str:
    """把库里存的相对路径（/uploads/...）转成前端可直接访问的完整地址。"""
    return settings.UPLOAD_BASE_URL.rstrip("/") + path.removeprefix("/uploads")


class ImageOut(BaseModel):
    path: str  # 存库用，如 /uploads/202611/ab12....jpg；发布物品时传这个
    url: str  # 预览用的完整地址


@router.post("/image", response_model=ApiResponse[ImageOut], summary="上传图片（jpg / png / webp）")
def upload_image(file: UploadFile = File(...), user: User = Depends(get_current_user)) -> ApiResponse[ImageOut]:
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    # 多读 1 字节，用来判断是否超限，避免把超大文件整个读进内存
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise BizError(41301, f"图片不能超过 {settings.MAX_UPLOAD_MB}MB")
    ext = detect_image_type(data[:12])
    if ext is None:
        raise BizError(41501, "只支持 jpg、png、webp 格式的图片")

    sub_dir = datetime.now().strftime("%Y%m")
    target_dir = settings.upload_path / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (target_dir / name).write_bytes(data)

    path = f"/uploads/{sub_dir}/{name}"
    return ok(ImageOut(path=path, url=public_url(path)), "上传成功")
