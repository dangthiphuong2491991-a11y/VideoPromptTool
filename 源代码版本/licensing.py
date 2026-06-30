# -*- coding: utf-8 -*-
"""
授权与机器码模块（Ed25519 非对称签名）
============================================================
安全模型：
  · 程序里只内置【公钥】(PUBLIC_KEY_HEX)，只能“验证”激活码；
  · 能签发激活码的【私钥】只在作者手里(private_key.pem)，
    别人反编译 exe 也拿不到私钥，因此无法伪造激活码。
  · 这是比原来 HMAC（密钥写死在程序里）安全得多的方案。

激活码格式： 到期日(YYYYMMDD) + "-" + base64url(Ed25519签名)
  签名内容 = 规范化机器码 + "|" + 到期日

注意：PUBLIC_KEY_HEX 必须与 keygen.py 里的私钥配对；
      换了密钥对，所有老激活码都会失效。
"""

import base64
import hashlib
import platform
import datetime

# ============================================================
# 公钥（由 generate_keys.py 生成；可以公开，没有安全风险）
# 注意：必须和 keygen.py 使用的 private_key.pem 是同一对密钥！
# ============================================================
PUBLIC_KEY_HEX = "aeb1fa37e0280daf4ff58aa4713075bedb7061014525189a501dad5ab8e327bd"

PERMANENT_EXPIRY = "20991231"


# ==================== 机器码 ====================
def _win_machine_guid():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        val, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(val)
    except Exception:
        return ""


def get_machine_code():
    """生成【稳定】的机器码（16 位十六进制，分 4 组显示）。

    只用 Windows 注册表的 MachineGuid —— 它跨重启、换网卡 / 插拔 VPN、
    改主机名都不会变。
    ⚠️ 不再使用 uuid.getnode()(MAC 地址) 和 platform.node()(主机名)：
        多网卡 / 虚拟网卡环境下 getnode() 拿到的 MAC 会变，主机名也可改，
        都会导致机器码漂移、把已激活用户挡在门外。
    """
    parts = []
    if platform.system() == "Windows":
        guid = _win_machine_guid()
        if guid:
            parts.append("winguid:" + guid)
    if not parts:
        # 回退：非 Windows 或拿不到 GUID 时（稳定性不如 GUID）
        parts = [platform.machine(), platform.node()]
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    code = h[:16]
    return "-".join(code[i:i + 4] for i in range(0, 16, 4))


def normalize_machine_code(machine_code):
    return (machine_code or "").replace("-", "").upper().strip()


def sign_message(machine_code, expiry_yyyymmdd):
    """供 keygen / 签名使用：返回待签名的消息字节。"""
    norm = normalize_machine_code(machine_code)
    return (norm + "|" + expiry_yyyymmdd).encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    s = s.strip()
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def encode_activation_code(expiry_yyyymmdd: str, signature: bytes) -> str:
    return expiry_yyyymmdd + "-" + _b64url_encode(signature)


# ==================== 校验（客户端用公钥验证）====================
def _load_public_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX))


def verify_activation_code(machine_code, code):
    """
    校验激活码。返回 (是否有效, 到期 date 或 None, 失败原因)。
    """
    code = (code or "").strip()
    if not code or "-" not in code:
        return (False, None, "激活码格式不正确")
    expiry, sig_part = code.split("-", 1)
    expiry = expiry.strip()
    if len(expiry) != 8 or not expiry.isdigit():
        return (False, None, "激活码格式不正确")

    # 1) 验证签名（公钥）
    try:
        from cryptography.exceptions import InvalidSignature
        public_key = _load_public_key()
        signature = _b64url_decode(sig_part)
        public_key.verify(signature, sign_message(machine_code, expiry))
    except InvalidSignature:
        return (False, None, "激活码无效（与本机不匹配或已被篡改）")
    except Exception:
        return (False, None, "激活码无效（格式或签名错误）")

    # 2) 验证到期日
    try:
        exp = datetime.datetime.strptime(expiry, "%Y%m%d").date()
    except ValueError:
        return (False, None, "激活码日期不正确")
    if datetime.date.today() > exp:
        return (False, exp, "授权已过期")
    return (True, exp, "")


def expiry_text(exp):
    if exp is None:
        return ""
    if exp >= datetime.date(2099, 1, 1):
        return "永久授权"
    return "授权至 " + exp.isoformat()
