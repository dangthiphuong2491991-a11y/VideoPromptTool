# -*- coding: utf-8 -*-
"""
自动更新模块（基于 GitHub Releases）
============================================================
工作流程：
  1. 启动时（或点“检查更新”）访问 GitHub 的 latest release 接口；
  2. 比较版本号，发现新版本就提示用户；
  3. 用户同意后下载新版 exe，写一个临时 .bat，
     等当前程序退出后用新 exe 覆盖旧 exe 并重新启动。

说明：
  · 公开仓库无需任何令牌；
  · 只用 Python 标准库(urllib)，不引入额外依赖；
  · 仅在“已打包成 exe(frozen)”时才执行自我替换；源码运行时只做提示。
"""

import os
import sys
import json
import ssl
import tempfile
import subprocess
import urllib.request

from version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO

_API_LATEST = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
_TIMEOUT = 15


def is_frozen():
    return getattr(sys, "frozen", False)


def is_configured():
    """仓库信息是否已正确填写（未填占位符）。"""
    return bool(GITHUB_OWNER) and "__OWNER__" not in GITHUB_OWNER and bool(GITHUB_REPO)


def parse_version(s):
    """'v1.2.3' / '1.2.3' -> (1, 2, 3)。无法解析的段按 0 处理。"""
    s = (s or "").strip().lstrip("vV")
    nums = []
    for part in s.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def _http_get(url, accept="application/json"):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VideoPromptTool-Updater",
            "Accept": accept,
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
        return resp.read()


def get_latest_release():
    """返回 GitHub latest release 的 dict；失败抛异常。"""
    url = _API_LATEST.format(owner=GITHUB_OWNER, repo=GITHUB_REPO)
    data = _http_get(url)
    return json.loads(data.decode("utf-8"))


def _pick_exe_asset(release):
    """从 release 资源里挑出 .exe 下载地址。"""
    for asset in release.get("assets", []):
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe"):
            return asset.get("browser_download_url"), asset.get("name")
    return None, None


def check_for_update():
    """
    检查是否有新版本。
    返回 dict: {has_update, latest, current, url, name, notes}
    出错时抛异常，调用方自行处理（静默或提示）。
    """
    if not is_configured():
        raise RuntimeError("尚未配置 GitHub 仓库信息，无法检查更新。")
    release = get_latest_release()
    latest_tag = release.get("tag_name", "")
    url, name = _pick_exe_asset(release)
    has_update = parse_version(latest_tag) > parse_version(APP_VERSION) and bool(url)
    return {
        "has_update": has_update,
        "latest": latest_tag.lstrip("vV") or latest_tag,
        "current": APP_VERSION,
        "url": url,
        "name": name,
        "notes": release.get("body", "") or "",
    }


def download_to_temp(url, progress_cb=None):
    """下载新版 exe 到临时文件，返回临时文件路径。"""
    req = urllib.request.Request(url, headers={"User-Agent": "VideoPromptTool-Updater"})
    ctx = ssl.create_default_context()
    fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="vpt_update_")
    os.close(fd)
    with urllib.request.urlopen(req, timeout=_TIMEOUT * 4, context=ctx) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with open(tmp_path, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    try:
                        progress_cb(done, total)
                    except Exception:
                        pass
    return tmp_path


def apply_update_and_restart(new_exe_path):
    """
    用新 exe 覆盖当前 exe 并重启。仅在 frozen 时有效。
    成功返回 True（调用方随后应立即退出程序）。
    """
    if not is_frozen():
        return False
    current_exe = sys.executable
    pid = os.getpid()
    bat_path = os.path.join(tempfile.gettempdir(), "vpt_update.bat")

    bat = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        ":wait\r\n"
        'tasklist /FI "PID eq {pid}" | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >nul\r\n"
        "  goto wait\r\n"
        ")\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        'move /y "{new}" "{cur}" >nul\r\n'
        'start "" "{cur}"\r\n'
        'del "%~f0"\r\n'
    ).format(pid=pid, new=new_exe_path, cur=current_exe)

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat)

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=creationflags,
        close_fds=True,
    )
    return True
