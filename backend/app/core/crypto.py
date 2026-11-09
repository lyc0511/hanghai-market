"""微信号等敏感字段的加密存储：AES-256-GCM。

与密码不同：密码用哈希（不可逆，只需要比对）；微信号要在交易意向被接受后展示给对方，
所以必须可解密，用对称加密。GCM 模式同时校验完整性，密文被篡改时解密会失败。

密文格式：v1:<base64(12 字节随机 nonce + 密文 + 16 字节校验标签)>
"v1:" 前缀用来区分明文旧数据和以后可能的换算法。
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

PREFIX = "v1:"
_aes = AESGCM(bytes.fromhex(settings.WECHAT_AES_KEY))


def encrypt_text(plain: str) -> str:
    nonce = os.urandom(12)  # 每次加密都用新的随机数，同一个微信号两次加密结果也不同
    data = _aes.encrypt(nonce, plain.encode("utf-8"), None)
    return PREFIX + base64.b64encode(nonce + data).decode("ascii")


def decrypt_text(token: str | None) -> str | None:
    """解密；空值返回 None。格式不对或被篡改时抛 ValueError。"""
    if not token:
        return None
    if not token.startswith(PREFIX):
        raise ValueError("不是本系统加密的数据")
    raw = base64.b64decode(token.removeprefix(PREFIX))
    try:
        return _aes.decrypt(raw[:12], raw[12:], None).decode("utf-8")
    except Exception as e:  # cryptography 抛 InvalidTag，统一转成 ValueError
        raise ValueError("解密失败，数据可能被篡改或密钥不一致") from e
