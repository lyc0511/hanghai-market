r"""一次性迁移：把 users.wechat_id_enc 里遗留的明文微信号加密。可重复执行，已加密的会跳过。

用法：.venv\Scripts\python scripts\encrypt_wechat.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.crypto import PREFIX, encrypt_text  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.wechat_id_enc.is_not(None))).all()
        todo = [u for u in users if not u.wechat_id_enc.startswith(PREFIX)]
        for u in todo:
            u.wechat_id_enc = encrypt_text(u.wechat_id_enc)
        db.commit()
        print(f"共 {len(users)} 个用户填写了微信号，本次加密 {len(todo)} 个")


if __name__ == "__main__":
    main()
