# crypto_processor.py
import pyffx
import secrets
import numpy as np

def fpeEncrypt(text, key=None):
    """
    使用纯 Python 的 FPE 加密文本。
    key: bytes 或 None，None 则自动生成随机 key
    """
    if key is None:
        key = secrets.token_bytes(16)  # 生成随机 key
    # 构建数字字母表 FPE
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
    fpe = pyffx.String(key, alphabet=alphabet, length=len(text))
    return fpe.encrypt(text)

def encryptROI(image, mask, key=b"ascon_key_16byte"):
    """
    示例：对非 ROI 区域简单加密处理
    image: np.array 或 None
    mask: np.array 的布尔 mask
    """
    if image is None or mask is None:
        return None
    encrypted_image = image.copy()
    encrypted_image[~mask] = (encrypted_image[~mask] + 123) % 256
    return encrypted_image

def protectData(ingest_id, policy=None):
    """
    整合文本和影像保护
    ingest_id: 对应输入 ID
    policy: 可选策略
    """
    # 示例数据
    text, image, mask = "Patient Name: Tom", None, None

    # 文本加密
    protected_text = fpeEncrypt(text)

    # 图像加密
    protected_image = encryptROI(image, mask)

    return {
        "artifact_id": f"artifact_{ingest_id}",
        "protected_text": protected_text,
        "protected_image": protected_image,
        "status": "ok"
    }
