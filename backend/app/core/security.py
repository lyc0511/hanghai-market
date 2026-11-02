"""密码哈希与 JWT 工具：直接使用 bcrypt 库（不使用 passlib）和 PyJWT。"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """生成 bcrypt 哈希，结果形如 $2b$12$...，长度 60。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配；哈希格式非法时返回 False。"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> tuple[str, int]:
    """签发访问令牌，返回 (token, 有效秒数)。sub 只放用户 id，角色每次请求从库里读。"""
    expires_in = settings.JWT_EXPIRE_HOURS * 3600
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=expires_in)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM), expires_in


def decode_access_token(token: str) -> int | None:
    """解析令牌，返回用户 id；签名错误、过期或格式不对时返回 None。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
