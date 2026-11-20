"""密码哈希与 JWT 工具：直接使用 bcrypt 库（不使用 passlib）和 PyJWT。"""
from datetime import datetime, timedelta, timezone
import hmac
from uuid import uuid4

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


def session_stamp(password_hash: str) -> str:
    """绑定当前密码版本，令牌不包含可用于校验密码的 bcrypt 哈希。"""
    return hmac.digest(settings.JWT_SECRET.encode(), b"session-version:" + password_hash.encode(), "sha256").hex()


def create_access_token(user_id: int, password_hash: str) -> tuple[str, int]:
    """签发访问令牌，返回 (token, 有效秒数)。sub 只放用户 id，角色每次请求从库里读。"""
    expires_in = settings.JWT_EXPIRE_HOURS * 3600
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=expires_in),
               "jti": uuid4().hex, "ver": session_stamp(password_hash)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM), expires_in


def decode_access_token(token: str) -> tuple[int, str] | None:
    """返回用户 id 和密码版本标记；旧格式及无效令牌都需重新登录。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]})
        stamp = payload.get("ver")
        if not isinstance(stamp, str) or not stamp.isascii() or len(stamp) != 64:
            return None
        return int(payload["sub"]), stamp
    except (jwt.PyJWTError, ValueError):
        return None
