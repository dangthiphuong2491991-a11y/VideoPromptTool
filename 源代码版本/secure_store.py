# -*- coding: utf-8 -*-
"""
本地敏感数据加密存储（Windows DPAPI）
============================================================
用 Windows 自带的 DPAPI（数据保护接口）加密 API 密钥：
  · 加密结果与【当前 Windows 用户账户】绑定，换账户/换电脑都无法解密；
  · 不需要任何第三方库（用 ctypes 直接调用 crypt32.dll）；
  · 比原来明文存 config.json 安全得多——即使别人拷走 config.json
    也解不出你的 API 密钥。

提供：
  encrypt_str(text)  -> base64 字符串（存进 config.json）
  decrypt_str(token) -> 原文（失败返回 ""）
非 Windows 平台会自动降级为不加密（仅做 base64），保证程序仍可运行。
"""

import sys
import base64
import ctypes
from ctypes import wintypes


_IS_WINDOWS = sys.platform == "win32"
_PREFIX = "dpapi:"  # 标记“已用 DPAPI 加密”，便于兼容旧的明文配置


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob_in(data: bytes) -> "_DATA_BLOB":
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _blob_out_to_bytes(blob: "_DATA_BLOB") -> bytes:
    size = int(blob.cbData)
    out = ctypes.string_at(blob.pbData, size)
    # 释放 DPAPI 分配的内存
    ctypes.windll.kernel32.LocalFree(blob.pbData)
    return out


def _dpapi_encrypt(raw: bytes) -> bytes:
    blob_in = _blob_in(raw)
    blob_out = _DATA_BLOB()
    # CRYPTPROTECT_UI_FORBIDDEN = 0x1（不弹任何 UI）
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), u"video_prompt_tool", None, None, None, 0x01,
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("CryptProtectData failed")
    return _blob_out_to_bytes(blob_out)


def _dpapi_decrypt(raw: bytes) -> bytes:
    blob_in = _blob_in(raw)
    blob_out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0x01,
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("CryptUnprotectData failed")
    return _blob_out_to_bytes(blob_out)


def encrypt_str(text: str) -> str:
    """把明文加密成可放进 config.json 的字符串。"""
    if not text:
        return ""
    data = text.encode("utf-8")
    if _IS_WINDOWS:
        try:
            enc = _dpapi_encrypt(data)
            return _PREFIX + base64.b64encode(enc).decode("ascii")
        except Exception:
            pass  # DPAPI 失败则降级
    # 降级：仅 base64（非 Windows 或 DPAPI 不可用），不视为加密
    return "b64:" + base64.b64encode(data).decode("ascii")


def decrypt_str(token: str) -> str:
    """把 encrypt_str 的结果还原成明文；无法识别时原样返回（兼容旧明文）。"""
    if not token:
        return ""
    if token.startswith(_PREFIX):
        if not _IS_WINDOWS:
            return ""
        try:
            enc = base64.b64decode(token[len(_PREFIX):])
            return _dpapi_decrypt(enc).decode("utf-8")
        except Exception:
            return ""
    if token.startswith("b64:"):
        try:
            return base64.b64decode(token[4:]).decode("utf-8")
        except Exception:
            return ""
    # 兼容旧版本：直接存的明文
    return token
