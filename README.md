# 视频提示词反推工具 (Qwen)

上传本地视频或视频 URL，调用通义千问多模态模型，反推出可直接用于 AI 视频生成的提示词。
简约 UI（浅色 / 深色可切换）、可自定义提示词与预设、激活码授权、自动更新。

## ✨ 功能
- 🎬 视频 → 提示词反推（本地视频 ≤100MB 或 URL）
- 📝 自定义提示词，支持预设保存 / 选择 / 删除 / 恢复默认
- 💾 一键保存设置，下次启动自动带出
- 🔒 安全：Ed25519 非对称签名授权（程序只内置公钥，无法伪造）+
  API 密钥用 Windows DPAPI 加密存储
- 🎨 简约界面，浅色 / 深色一键切换
- ⬆️ 自动更新：从 GitHub Releases 检查 / 下载 / 自我替换

## 🚀 使用（普通用户）
1. 下载最新 [Release](../../releases/latest) 里的 `VideoPromptTool.exe`。
2. 双击运行，首次会要求激活：把窗口里的“机器码”发给作者获取激活码。
3. 填入激活码 → 激活 → 进入主界面。
4. 填 API 密钥、选视频、点“开始生成”。
5. 有新版本时软件会自动提示更新。

## 🛠 开发 / 打包（作者）
详见 [`源代码版本/使用与授权说明.md`](源代码版本/使用与授权说明.md)。

```bash
cd 源代码版本
python -m pip install dashscope ttkbootstrap cryptography pyinstaller
python video_prompt_tool.py        # 源码运行
build_exe.bat                       # 打包成 exe
```

## 📦 发布新版本
改 `源代码版本/version.py` 的 `APP_VERSION`，然后：

```bash
git tag v1.2.0 && git push --tags
```

GitHub Actions 自动打包并发布 Release，老用户即可自动更新。

## ⚠️ 安全须知
- `private_key.pem`（签名私钥）**绝不能**上传仓库或外发，已在 `.gitignore` 中排除。
- 仓库内置的是**公钥**，公开无风险。
