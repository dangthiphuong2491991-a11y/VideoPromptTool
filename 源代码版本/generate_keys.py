# -*- coding: utf-8 -*-
"""
密钥对生成器 —— 仅作者本人运行一次！
============================================================
本脚本用 Ed25519 生成一对密钥：
  · private_key.pem  —— 【签名私钥】只留在你电脑上，绝对不要上传 GitHub、
                          不要打包进 exe、不要发给任何人。keygen.py 用它来签发激活码。
  · 公钥(hex)        —— 打印在屏幕上，需要复制进 video_prompt_tool.py 和 keygen.py
                          的 PUBLIC_KEY_HEX 常量里。公钥可以公开，没有风险。

安全原理：
  程序里只有【公钥】，只能“验证”激活码，不能“伪造”。
  能伪造激活码的【私钥】永远只在你手上，别人反编译 exe 也拿不到。

运行：python generate_keys.py
如果 private_key.pem 已存在，脚本会拒绝覆盖，避免你不小心作废老用户的激活码。
"""

import os
import sys

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("缺少 cryptography 库，请先运行：python -m pip install cryptography")
    sys.exit(1)

PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_key.pem")


def main():
    if os.path.exists(PRIVATE_KEY_PATH):
        print("检测到已存在 private_key.pem，已停止。")
        print("如果你确定要换一对新密钥（会让所有老激活码失效！），请先手动删除：")
        print("   " + PRIVATE_KEY_PATH)
        return

    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(pem)

    public_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()

    print("=" * 60)
    print("私钥已保存到：" + PRIVATE_KEY_PATH)
    print("【千万不要把这个文件上传 GitHub / 打包 / 外发！】")
    print("=" * 60)
    print("请把下面这行公钥(hex) 复制到 video_prompt_tool.py 和 keygen.py 的")
    print("PUBLIC_KEY_HEX 常量里（两边必须一致）：")
    print()
    print('PUBLIC_KEY_HEX = "' + public_hex + '"')
    print()


if __name__ == "__main__":
    main()
