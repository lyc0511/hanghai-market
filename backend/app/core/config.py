from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录的绝对路径，保证无论从哪个目录启动都能找到 .env 和 uploads
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_HOURS: int = 24
    WECHAT_AES_KEY: str = ""
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_BASE_URL: str = "http://127.0.0.1:8000/uploads"
    MAX_UPLOAD_MB: int = 5
    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_API_BASE: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = ""
    DAILY_PUBLISH_LIMIT: int = 10

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        """UPLOAD_DIR 的绝对路径；相对路径以 backend/ 为基准。"""
        p = Path(self.UPLOAD_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()


settings = Settings()

if len(settings.JWT_SECRET.encode()) < 32:
    raise RuntimeError("JWT_SECRET 必须至少 32 字节，请用 secrets.token_hex(32) 生成")

try:
    _aes_key_ok = len(bytes.fromhex(settings.WECHAT_AES_KEY)) == 32
except ValueError:
    _aes_key_ok = False
if not _aes_key_ok:
    raise RuntimeError("WECHAT_AES_KEY 必须是 64 位十六进制（32 字节），请用 secrets.token_hex(32) 生成")
