# -*- coding: utf-8 -*-
"""
激活码生成器 (GUI) —— 仅供作者本人使用！
============================================================
  · 用 Ed25519【私钥】(private_key.pem) 为用户机器码签发激活码。
  · 把用户发来的“机器码”粘进来，选好到期日期（或勾选永久），
    点“生成激活码”，再点“复制”发给用户即可。
  · 依赖：cryptography（pip install cryptography）。

★ 安全要点 ★
  · private_key.pem 必须和本程序放在同一文件夹（或填写其路径）。
  · 千万不要把 private_key.pem 上传 GitHub、打包进用户 exe、或发给任何人——
    谁拿到私钥谁就能签发激活码。
  · 程序(video_prompt_tool.py / licensing.py)里内置的是【公钥】，
    只能验证、不能伪造，所以可以公开。

首次使用：先运行 generate_keys.py 生成 private_key.pem 与公钥，
          把公钥填进 licensing.py 的 PUBLIC_KEY_HEX。
"""

import os
import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: F401
    from cryptography.hazmat.primitives import serialization
except ImportError:
    serialization = None

import licensing  # 复用机器码规范化 / 激活码编码，保证与主程序格式一致

DEFAULT_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_key.pem")


class KeygenApp:
    def __init__(self, root):
        self.root = root
        self.private_key = None
        self.key_path = DEFAULT_KEY_PATH

        root.title("激活码生成器（作者专用）")
        root.geometry("560x460")
        root.minsize(520, 440)

        f = ttk.Frame(root, padding=20)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="激活码生成器", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        ttk.Label(f, text="仅供作者使用 · 使用 Ed25519 私钥签发 · 私钥切勿外发",
                  foreground="#cc0000", font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(0, 12))

        # 私钥状态
        key_row = ttk.Frame(f)
        key_row.pack(fill="x", pady=(0, 10))
        self.key_status = ttk.Label(key_row, text="", font=("Microsoft YaHei UI", 9))
        self.key_status.pack(side="left")
        ttk.Button(key_row, text="选择私钥…", command=self._choose_key).pack(side="right")

        ttk.Label(f, text="① 用户机器码（粘贴用户发来的那一串）：",
                  font=("Microsoft YaHei UI", 10)).pack(anchor="w")
        self.mc = tk.StringVar()
        ttk.Entry(f, textvariable=self.mc, font=("Microsoft YaHei UI", 10)).pack(fill="x", pady=(3, 12))

        self.perm = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="永久授权（勾选后忽略下面的日期）",
                        variable=self.perm, command=self._toggle).pack(anchor="w")

        ttk.Label(f, text="② 到期日期 (格式 YYYY-MM-DD)：",
                  font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(10, 0))
        self.date = tk.StringVar(value=datetime.date.today().isoformat())
        self.date_entry = ttk.Entry(f, textvariable=self.date, width=22, font=("Microsoft YaHei UI", 10))
        self.date_entry.pack(anchor="w", pady=(3, 12))

        ttk.Button(f, text="生成激活码", command=self._gen).pack(anchor="w")

        ttk.Label(f, text="③ 激活码（发给用户）：",
                  font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(12, 0))
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(3, 0))
        self.out = ttk.Entry(row, font=("Consolas", 10))
        self.out.pack(side="left", fill="x", expand=True)
        self.out.configure(state="readonly")
        ttk.Button(row, text="复制", command=self._copy).pack(side="left", padx=6)

        self._load_key(self.key_path)

    # ---------- 私钥 ----------
    def _load_key(self, path):
        if serialization is None:
            self.key_status.configure(text="✗ 缺少 cryptography 库（pip install cryptography）",
                                      foreground="#cc0000")
            return
        if not path or not os.path.exists(path):
            self.key_status.configure(text="✗ 未找到私钥 private_key.pem，请先运行 generate_keys.py",
                                      foreground="#cc0000")
            self.private_key = None
            return
        try:
            with open(path, "rb") as fp:
                self.private_key = serialization.load_pem_private_key(fp.read(), password=None)
            self.key_path = path
            self.key_status.configure(text="✓ 已加载私钥：" + os.path.basename(path),
                                      foreground="#107c10")
        except Exception as e:  # noqa: BLE001
            self.private_key = None
            self.key_status.configure(text="✗ 私钥加载失败：" + str(e), foreground="#cc0000")

    def _choose_key(self):
        path = filedialog.askopenfilename(
            title="选择 Ed25519 私钥",
            filetypes=[("PEM 私钥", "*.pem"), ("所有文件", "*.*")],
        )
        if path:
            self._load_key(path)

    def _toggle(self):
        self.date_entry.configure(state="disabled" if self.perm.get() else "normal")

    def _gen(self):
        if self.private_key is None:
            messagebox.showwarning("缺少私钥", "未加载私钥，无法签发。请先运行 generate_keys.py，"
                                            "或点“选择私钥…”指定 private_key.pem。")
            return
        mc = self.mc.get().strip()
        if not mc:
            messagebox.showwarning("提示", "请先粘贴用户的机器码。")
            return
        if self.perm.get():
            expiry = licensing.PERMANENT_EXPIRY
        else:
            try:
                d = datetime.datetime.strptime(self.date.get().strip(), "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("提示", "日期格式不正确，应为 YYYY-MM-DD，例如 2026-12-31。")
                return
            expiry = d.strftime("%Y%m%d")

        signature = self.private_key.sign(licensing.sign_message(mc, expiry))
        code = licensing.encode_activation_code(expiry, signature)
        self.out.configure(state="normal")
        self.out.delete(0, "end")
        self.out.insert(0, code)
        self.out.configure(state="readonly")

    def _copy(self):
        code = self.out.get().strip()
        if not code:
            messagebox.showinfo("提示", "请先生成激活码。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.root.update()
        messagebox.showinfo("已复制", "激活码已复制到剪贴板，发给用户即可。")


def main():
    root = tk.Tk()
    KeygenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
