# -*- coding: utf-8 -*-
"""
视频提示词反推工具 (Qwen) —— 安全增强 / 简约 UI 版
============================================================
功能：
  1. 上传本地视频(≤100MB) 或 粘贴视频 URL，调用通义千问多模态模型反推提示词
  2. 自定义提示词，支持“预设”保存 / 选择 / 删除，并自动记住上次内容
  3. 保存 API 密钥 / 地址 / 模型 / fps 到本地（API 密钥用 Windows DPAPI 加密）
  4. 简约现代 UI（ttkbootstrap），支持浅色 / 深色一键切换
  5. 授权：Ed25519 非对称签名校验激活码——程序只内置公钥，无法伪造；
     启动即校验，未激活则停在激活界面；含系统时间回拨检测
  6. 一键导出 txt
  7. 自动更新：从 GitHub Releases 检查 / 下载 / 自我替换新版本

依赖：dashscope、ttkbootstrap、cryptography（build_exe.bat 会自动安装）
配置文件：用户目录下 ~/.video_prompt_tool/config.json
          （API 密钥为 DPAPI 加密，绑定当前 Windows 账户）
"""

import os
import json
import datetime
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import licensing
import secure_store
import updater
from version import APP_VERSION

APP_FONT = ("Microsoft YaHei UI", 10)
TITLE_FONT = ("Microsoft YaHei UI", 17, "bold")
SMALL_FONT = ("Microsoft YaHei UI", 9)

# 简约主题：浅色 / 深色
THEMES = {"light": "litera", "dark": "darkly"}

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_MODEL = "qwen3.7-plus"
DEFAULT_PROMPT = (
    "请仔细观看这段视频，反推出可直接用于 AI 视频生成的提示词(prompt)。"
    "要求尽量详细地描述：画面主体与场景、整体风格与画质、镜头运动与构图、"
    "光线与色调、人物或物体的动作与表情、氛围与情绪。"
    "请直接输出提示词文本本身，不要额外解释。"
)

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".video_prompt_tool")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


# ==================== 配置读写 ====================
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ==================== 接口逻辑 ====================
def normalize_sdk_base_url(url):
    url = (url or "").strip().rstrip("/")
    if not url:
        return DEFAULT_BASE_URL
    if "/compatible-mode/v1" in url:
        url = url.replace("/compatible-mode/v1", "/api/v1")
    return url


def build_video_ref(local_path, online_url):
    if online_url:
        return online_url.strip()
    p = local_path.strip().replace("\\", "/")
    return "file://" + p


def call_qwen_sdk(base_url, api_key, model, video_ref, fps, prompt):
    try:
        import dashscope
        from dashscope import MultiModalConversation
    except ImportError:
        raise RuntimeError(
            "缺少 dashscope 库。请运行：python -m pip install dashscope，或重新打包。"
        )
    dashscope.base_http_api_url = normalize_sdk_base_url(base_url)
    messages = [{
        "role": "user",
        "content": [
            {"video": video_ref, "fps": fps},
            {"text": prompt},
        ],
    }]
    resp = MultiModalConversation.call(api_key=api_key, model=model, messages=messages)
    status = getattr(resp, "status_code", 200)
    if status != 200:
        raise RuntimeError(
            "接口返回错误 (HTTP {})：\ncode = {}\nmessage = {}".format(
                status, getattr(resp, "code", ""), getattr(resp, "message", "")
            )
        )
    try:
        content = resp.output.choices[0].message.content
    except Exception:
        raise RuntimeError("无法解析接口返回内容：\n" + str(resp))
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


# ==================== UI 组件 ====================
def make_scrolled_text(parent, tb, style, height):
    frame = tb.Frame(parent)
    txt = tk.Text(
        frame, height=height, wrap="word", font=APP_FONT,
        relief="flat", borderwidth=0, highlightthickness=1,
        padx=12, pady=10,
    )
    sb = tb.Scrollbar(frame, orient="vertical", command=txt.yview, bootstyle="round")
    txt.configure(yscrollcommand=sb.set)
    txt.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    _style_text(txt, style)
    return frame, txt


def _style_text(txt, style):
    """让 tk.Text 跟随当前 ttkbootstrap 主题配色（浅/深都好看）。"""
    c = style.colors
    txt.configure(
        background=c.inputbg, foreground=c.inputfg,
        insertbackground=c.inputfg,
        highlightbackground=c.border, highlightcolor=c.primary,
        selectbackground=c.selectbg, selectforeground=c.selectfg,
    )


class App:
    def __init__(self, root, tb, expiry):
        self.root = root
        self.tb = tb
        self.style = root.style
        self.busy = False
        self.cfg = load_config()
        self.presets = dict(self.cfg.get("presets", {}))
        self.theme_mode = self.cfg.get("theme", "light")
        if self.theme_mode not in THEMES:
            self.theme_mode = "light"
        self._texts = []  # 跟随主题重新着色的 Text 列表

        root.title("视频提示词反推工具 (Qwen)")
        root.geometry("880x900")
        root.minsize(800, 760)

        outer = tb.Frame(root, padding=22)
        outer.pack(fill="both", expand=True)

        # ---- 标题栏 ----
        header = tb.Frame(outer)
        header.pack(fill="x", pady=(0, 16))
        tb.Label(header, text="🎬 视频提示词反推工具", font=TITLE_FONT,
                 bootstyle="primary").pack(side="left")

        # 右侧：主题切换 + 版本 + 授权
        right = tb.Frame(header)
        right.pack(side="right")
        self.theme_btn = tb.Button(right, text="", width=4, bootstyle="secondary-outline",
                                   command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=(8, 0))
        self._refresh_theme_btn()
        info = tb.Frame(right)
        info.pack(side="right")
        self.lic_label = tb.Label(info, text=licensing.expiry_text(expiry),
                                  font=SMALL_FONT, bootstyle="secondary")
        self.lic_label.pack(anchor="e")
        tb.Label(info, text="v" + APP_VERSION, font=SMALL_FONT,
                 bootstyle="secondary").pack(anchor="e")

        # ---- ① 接口配置 ----
        cfgf = tb.Labelframe(outer, text="  ① 接口配置  ", padding=16)
        cfgf.pack(fill="x", pady=8)

        tb.Label(cfgf, text="API 地址").grid(row=0, column=0, sticky="w", pady=6)
        self.base_url = tk.StringVar(value=self.cfg.get("base_url", DEFAULT_BASE_URL))
        tb.Entry(cfgf, textvariable=self.base_url).grid(row=0, column=1, columnspan=2, sticky="we", padx=10, pady=6)

        tb.Label(cfgf, text="API 密钥").grid(row=1, column=0, sticky="w", pady=6)
        self.api_key = tk.StringVar(value=self._load_api_key())
        self.key_entry = tb.Entry(cfgf, textvariable=self.api_key, show="●")
        self.key_entry.grid(row=1, column=1, sticky="we", padx=10, pady=6)
        self.show_key = tk.BooleanVar(value=False)
        tb.Checkbutton(cfgf, text="显示", variable=self.show_key, command=self._toggle_key,
                       bootstyle="round-toggle").grid(row=1, column=2, sticky="w", pady=6)

        tb.Label(cfgf, text="模型名称").grid(row=2, column=0, sticky="w", pady=6)
        self.model = tk.StringVar(value=self.cfg.get("model", DEFAULT_MODEL))
        tb.Entry(cfgf, textvariable=self.model, width=26).grid(row=2, column=1, sticky="w", padx=10, pady=6)
        tb.Label(cfgf, text="🔒 密钥已用 Windows 账户级加密(DPAPI)保存", font=SMALL_FONT,
                 bootstyle="secondary").grid(row=3, column=1, columnspan=2, sticky="w", padx=10)
        cfgf.columnconfigure(1, weight=1)

        # ---- ② 选择视频 ----
        vid = tb.Labelframe(outer, text="  ② 选择视频（本地 ≤100MB，或填 URL）  ", padding=16)
        vid.pack(fill="x", pady=8)

        self.video_path = tk.StringVar()
        tb.Button(vid, text="选择本地视频", bootstyle="secondary-outline",
                  command=self._choose_video).grid(row=0, column=0, pady=6)
        tb.Entry(vid, textvariable=self.video_path).grid(row=0, column=1, sticky="we", padx=10, pady=6)

        tb.Label(vid, text="视频 URL").grid(row=1, column=0, sticky="w", pady=6)
        self.video_url = tk.StringVar()
        tb.Entry(vid, textvariable=self.video_url).grid(row=1, column=1, sticky="we", padx=10, pady=6)

        tb.Label(vid, text="抽帧 fps").grid(row=2, column=0, sticky="w", pady=6)
        self.fps = tk.StringVar(value=str(self.cfg.get("fps", "2")))
        tb.Entry(vid, textvariable=self.fps, width=8).grid(row=2, column=1, sticky="w", padx=10, pady=6)
        vid.columnconfigure(1, weight=1)

        # ---- ③ 自定义提示词 + 预设 ----
        pr = tb.Labelframe(outer, text="  ③ 自定义提示词  ", padding=16)
        pr.pack(fill="both", expand=False, pady=8)

        bar = tb.Frame(pr)
        bar.pack(fill="x", pady=(0, 10))
        tb.Label(bar, text="预设：").pack(side="left")
        self.preset_var = tk.StringVar()
        self.preset_box = tb.Combobox(bar, textvariable=self.preset_var, state="readonly", width=26)
        self.preset_box.pack(side="left", padx=6)
        self.preset_box.bind("<<ComboboxSelected>>", self._load_preset)
        tb.Button(bar, text="另存为预设", bootstyle="success-outline",
                  command=self._save_preset).pack(side="left", padx=4)
        tb.Button(bar, text="删除预设", bootstyle="danger-outline",
                  command=self._delete_preset).pack(side="left", padx=4)
        tb.Button(bar, text="恢复默认", bootstyle="secondary-outline",
                  command=self._reset_prompt).pack(side="left", padx=4)

        pf, self.prompt_box = make_scrolled_text(pr, tb, self.style, height=5)
        pf.pack(fill="both", expand=True)
        self.prompt_box.insert("1.0", self.cfg.get("last_prompt", DEFAULT_PROMPT))
        self._texts.append(self.prompt_box)
        self._refresh_presets()

        # ---- ④ 操作 ----
        act = tb.Frame(outer)
        act.pack(fill="x", pady=12)
        self.gen_btn = tb.Button(act, text="🚀 开始生成", bootstyle="primary",
                                 command=self._on_generate, width=16)
        self.gen_btn.pack(side="left")
        self.export_btn = tb.Button(act, text="导出 TXT", bootstyle="secondary",
                                    command=self._on_export, width=12)
        self.export_btn.pack(side="left", padx=8)
        tb.Button(act, text="💾 保存设置", bootstyle="info-outline",
                  command=self._save_settings, width=12).pack(side="left")
        tb.Button(act, text="检查更新", bootstyle="secondary-outline",
                  command=lambda: self._check_update(silent=False), width=10).pack(side="left", padx=8)
        self.status = tk.StringVar(value="就绪")
        tb.Label(act, textvariable=self.status, bootstyle="secondary").pack(side="left", padx=14)

        # ---- ⑤ 结果 ----
        res = tb.Labelframe(outer, text="  ④ 反推结果（可编辑后导出）  ", padding=16)
        res.pack(fill="both", expand=True, pady=8)
        rf, self.result_box = make_scrolled_text(res, tb, self.style, height=10)
        rf.pack(fill="both", expand=True)
        self._texts.append(self.result_box)

        root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 启动后台静默检查更新
        if updater.is_configured():
            self.root.after(1500, lambda: self._check_update(silent=True))

    # ---------- API 密钥（加密存储）----------
    def _load_api_key(self):
        enc = self.cfg.get("api_key_enc")
        if enc:
            return secure_store.decrypt_str(enc)
        # 兼容旧版本明文
        return self.cfg.get("api_key", "")

    # ---------- 主题 ----------
    def _refresh_theme_btn(self):
        # 显示“切到另一个主题”的图标
        self.theme_btn.configure(text="🌙" if self.theme_mode == "light" else "☀️")

    def _toggle_theme(self):
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        self.style.theme_use(THEMES[self.theme_mode])
        self._refresh_theme_btn()
        for t in self._texts:
            _style_text(t, self.style)
        self.cfg["theme"] = self.theme_mode
        save_config(self.cfg)

    # ---------- 预设 ----------
    def _refresh_presets(self):
        names = ["默认提示词"] + sorted(self.presets.keys())
        self.preset_box.configure(values=names)

    def _load_preset(self, *_):
        name = self.preset_var.get()
        text = DEFAULT_PROMPT if name == "默认提示词" else self.presets.get(name, "")
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", text)

    def _reset_prompt(self):
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", DEFAULT_PROMPT)
        self.preset_var.set("默认提示词")

    def _save_preset(self):
        name = simpledialog.askstring("保存预设", "给这个提示词起个名字：", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name or name == "默认提示词":
            messagebox.showwarning("提示", "名字不能为空，也不能叫“默认提示词”。")
            return
        self.presets[name] = self.prompt_box.get("1.0", "end").strip()
        self._refresh_presets()
        self.preset_var.set(name)
        self._save_settings(silent=True)
        messagebox.showinfo("已保存", "预设“{}”已保存。".format(name))

    def _delete_preset(self):
        name = self.preset_var.get()
        if not name or name == "默认提示词":
            messagebox.showwarning("提示", "请选择一个自定义预设再删除。")
            return
        if name in self.presets and messagebox.askyesno("删除", "确定删除预设“{}”？".format(name)):
            del self.presets[name]
            self._refresh_presets()
            self.preset_var.set("")
            self._save_settings(silent=True)

    # ---------- 设置持久化 ----------
    def _collect_settings(self):
        self.cfg["base_url"] = self.base_url.get().strip()
        self.cfg["api_key_enc"] = secure_store.encrypt_str(self.api_key.get().strip())
        self.cfg.pop("api_key", None)  # 移除可能存在的旧明文
        self.cfg["model"] = self.model.get().strip()
        self.cfg["fps"] = self.fps.get().strip()
        self.cfg["last_prompt"] = self.prompt_box.get("1.0", "end").strip()
        self.cfg["presets"] = self.presets
        self.cfg["theme"] = self.theme_mode

    def _save_settings(self, silent=False):
        self._collect_settings()
        save_config(self.cfg)
        if not silent:
            messagebox.showinfo("已保存", "设置已保存到本地，下次启动自动带出。\n"
                                        "（API 密钥已加密存储）")

    def _on_close(self):
        self._collect_settings()
        save_config(self.cfg)
        self.root.destroy()

    # ---------- 小工具 ----------
    def _toggle_key(self):
        self.key_entry.configure(show="" if self.show_key.get() else "●")

    def _choose_video(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm"), ("所有文件", "*.*")],
        )
        if path:
            self.video_path.set(path)

    def _set_busy(self, busy, text):
        self.busy = busy
        self.status.set(text)
        self.gen_btn.configure(state="disabled" if busy else "normal")

    # ---------- 生成 ----------
    def _on_generate(self):
        if self.busy:
            return
        api_key = self.api_key.get().strip()
        base_url = self.base_url.get().strip()
        model = self.model.get().strip()
        prompt = self.prompt_box.get("1.0", "end").strip()
        local_path = self.video_path.get().strip()
        online_url = self.video_url.get().strip()

        if not api_key:
            messagebox.showwarning("缺少信息", "请填写 API 密钥。")
            return
        if not model or not base_url or not prompt:
            messagebox.showwarning("缺少信息", "请填写地址、模型和提示词。")
            return
        if not local_path and not online_url:
            messagebox.showwarning("缺少信息", "请选择本地视频或填写视频 URL。")
            return
        if local_path and not online_url and not os.path.isfile(local_path):
            messagebox.showerror("文件错误", "找不到所选视频文件：\n" + local_path)
            return
        try:
            fps = float(self.fps.get().strip())
        except ValueError:
            messagebox.showwarning("参数错误", "抽帧 fps 必须是数字。")
            return

        self._collect_settings()
        save_config(self.cfg)
        self.result_box.delete("1.0", "end")
        self._set_busy(True, "正在上传视频并生成中…请耐心等待")

        threading.Thread(
            target=self._worker,
            args=(base_url, api_key, model, local_path, online_url, fps, prompt),
            daemon=True,
        ).start()

    def _worker(self, base_url, api_key, model, local_path, online_url, fps, prompt):
        try:
            video_ref = build_video_ref(local_path, online_url)
            text = call_qwen_sdk(base_url, api_key, model, video_ref, fps, prompt)
            self.root.after(0, self._on_success, text)
        except Exception as e:  # noqa: BLE001
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, text):
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self._set_busy(False, "完成")

    def _on_error(self, msg):
        self._set_busy(False, "出错")
        messagebox.showerror("生成失败", msg)

    # ---------- 导出 ----------
    def _on_export(self):
        content = self.result_box.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("没有内容", "结果为空，请先生成。")
            return
        path = filedialog.asksaveasfilename(
            title="导出为 TXT", defaultextension=".txt",
            initialfile="视频提示词.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            messagebox.showerror("保存失败", str(e))
            return
        messagebox.showinfo("已导出", "已保存到：\n" + path)

    # ---------- 自动更新 ----------
    def _check_update(self, silent=True):
        if not updater.is_configured():
            if not silent:
                messagebox.showinfo("检查更新", "当前版本尚未配置更新仓库信息。")
            return
        if not silent:
            self.status.set("正在检查更新…")
        threading.Thread(target=self._update_worker, args=(silent,), daemon=True).start()

    def _update_worker(self, silent):
        try:
            info = updater.check_for_update()
        except Exception as e:  # noqa: BLE001
            self.root.after(0, lambda: self._update_check_done(None, silent, str(e)))
            return
        self.root.after(0, lambda: self._update_check_done(info, silent, ""))

    def _update_check_done(self, info, silent, err):
        if not silent:
            self.status.set("就绪")
        if err:
            if not silent:
                messagebox.showwarning("检查更新失败", "无法连接 GitHub：\n" + err)
            return
        if not info or not info["has_update"]:
            if not silent:
                messagebox.showinfo("检查更新", "当前已是最新版本 v{}。".format(info["current"] if info else APP_VERSION))
            return
        notes = (info.get("notes") or "").strip()
        if len(notes) > 600:
            notes = notes[:600] + "…"
        msg = "发现新版本 v{}（当前 v{}）。\n\n{}\n\n是否现在更新？".format(
            info["latest"], info["current"], notes or "（无更新说明）")
        if not messagebox.askyesno("发现新版本", msg):
            return
        if not updater.is_frozen():
            messagebox.showinfo(
                "前往下载",
                "检测到新版本 v{}。\n源码运行模式不支持自动替换，请到 GitHub 下载最新 exe。".format(info["latest"]),
            )
            return
        self._do_update(info["url"])

    def _do_update(self, url):
        self._set_busy(True, "正在下载更新…")

        def work():
            try:
                def prog(done, total):
                    pct = int(done * 100 / total)
                    self.root.after(0, lambda: self.status.set("正在下载更新… {}%".format(pct)))
                tmp = updater.download_to_temp(url, prog)
                self.root.after(0, lambda: self._apply_update(tmp))
            except Exception as e:  # noqa: BLE001
                self.root.after(0, lambda: (self._set_busy(False, "更新失败"),
                                            messagebox.showerror("更新失败", str(e))))

        threading.Thread(target=work, daemon=True).start()

    def _apply_update(self, tmp_path):
        self.status.set("准备重启以完成更新…")
        ok = updater.apply_update_and_restart(tmp_path)
        if ok:
            self._collect_settings()
            save_config(self.cfg)
            messagebox.showinfo("更新", "新版本已下载，程序将关闭并自动重启完成更新。")
            self.root.destroy()
        else:
            self._set_busy(False, "更新失败")
            messagebox.showerror("更新失败", "无法应用更新（请确认以 exe 方式运行）。")


# ==================== 激活流程 ====================
def clear_window(root):
    for w in list(root.winfo_children()):
        try:
            w.destroy()
        except Exception:
            pass


def _bring_to_front(win):
    try:
        win.lift()
        win.attributes("-topmost", True)
        win.after(400, lambda: win.attributes("-topmost", False))
        win.focus_force()
    except Exception:
        pass


def build_main(root, tb, expiry):
    """激活通过后，在同一个窗口上构建主界面。"""
    clear_window(root)
    App(root, tb, expiry)
    _bring_to_front(root)


def build_activation(root, tb, machine_code, cfg, expired):
    """启动后必须先通过激活校验，才能进入主界面。"""
    clear_window(root)
    root.title("软件激活")
    root.geometry("600x440")
    try:
        root.place_window_center()
    except Exception:
        pass

    box = tb.Frame(root, padding=28)
    box.pack(fill="both", expand=True)

    tb.Label(box, text="🔐 软件激活", font=("Microsoft YaHei UI", 17, "bold"),
             bootstyle="primary").pack(anchor="w")
    tb.Label(box, text="本软件需要激活后使用（启动时自动校验）",
             font=SMALL_FONT, bootstyle="secondary").pack(anchor="w", pady=(2, 0))
    if expired:
        tb.Label(box, text="（原授权已过期，请重新激活）", bootstyle="warning",
                 font=APP_FONT).pack(anchor="w", pady=(6, 0))
    tb.Label(box, text="请把下面的“机器码”发给作者，获取专属激活码：",
             font=APP_FONT).pack(anchor="w", pady=(16, 4))

    row = tb.Frame(box)
    row.pack(fill="x")
    mc_entry = tb.Entry(row, font=("Consolas", 11))
    mc_entry.pack(side="left", fill="x", expand=True)
    mc_entry.insert(0, machine_code)
    mc_entry.configure(state="readonly")

    def copy_mc():
        root.clipboard_clear()
        root.clipboard_append(machine_code)
        root.update()
        messagebox.showinfo("已复制", "机器码已复制到剪贴板。")

    tb.Button(row, text="复制", bootstyle="secondary-outline", command=copy_mc).pack(side="left", padx=6)

    tb.Label(box, text="输入激活码：", font=APP_FONT).pack(anchor="w", pady=(18, 4))
    code_var = tk.StringVar()
    code_entry = tb.Entry(box, textvariable=code_var, font=("Consolas", 10))
    code_entry.pack(fill="x")

    msg = tb.Label(box, text="", bootstyle="danger", font=SMALL_FONT)
    msg.pack(anchor="w", pady=8)

    def do_activate():
        ok, exp, reason = licensing.verify_activation_code(machine_code, code_var.get())
        if ok:
            cfg["activation_code"] = code_var.get().strip()
            save_config(cfg)
            build_main(root, tb, exp)
        else:
            msg.configure(text="激活失败：" + reason)

    code_entry.bind("<Return>", lambda *_: do_activate())

    btns = tb.Frame(box)
    btns.pack(fill="x", pady=(8, 0))
    tb.Button(btns, text="激活", bootstyle="primary", width=12, command=do_activate).pack(side="left")
    tb.Button(btns, text="退出", bootstyle="secondary-outline", width=10,
              command=root.destroy).pack(side="left", padx=8)

    _bring_to_front(root)


def main():
    try:
        import ttkbootstrap as tb
    except ImportError:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(
            "缺少组件",
            "缺少 ttkbootstrap 库。\n请运行：python -m pip install ttkbootstrap\n或重新运行 build_exe.bat 打包。",
        )
        return

    cfg = load_config()
    theme_mode = cfg.get("theme", "light")
    themename = THEMES.get(theme_mode, THEMES["light"])
    root = tb.Window(themename=themename)
    try:
        root.style.configure(".", font=APP_FONT)
    except Exception:
        pass

    machine_code = licensing.get_machine_code()

    # 系统时间回拨检测
    today = datetime.date.today()
    last_seen = cfg.get("last_seen", "")
    rollback = False
    if last_seen:
        try:
            rollback = today < datetime.date.fromisoformat(last_seen)
        except Exception:
            rollback = False
    if rollback:
        root.withdraw()
        messagebox.showerror("时间异常", "检测到系统时间被回拨，授权校验失败。\n请把系统时间调整正确后重试。")
        root.destroy()
        return
    cfg["last_seen"] = max(today.isoformat(), last_seen or "")
    save_config(cfg)

    # 启动即校验：已激活进主界面，否则停在激活界面
    code = cfg.get("activation_code", "")
    expired = False
    if code:
        ok, exp, reason = licensing.verify_activation_code(machine_code, code)
        if ok:
            build_main(root, tb, exp)
            root.mainloop()
            return
        expired = (reason == "授权已过期")

    build_activation(root, tb, machine_code, cfg, expired)
    root.mainloop()


if __name__ == "__main__":
    main()
