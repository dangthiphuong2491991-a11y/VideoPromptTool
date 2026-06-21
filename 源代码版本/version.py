# -*- coding: utf-8 -*-
"""
版本与发布仓库信息（自动更新用）
============================================================
· APP_VERSION：当前程序版本号。每次要发新版时，把它 +1，
  例如 1.1.0 -> 1.2.0，然后 git tag v1.2.0 推上去，
  GitHub Actions 会自动打包并发布 Release，老用户就能收到更新。
· GITHUB_OWNER / GITHUB_REPO：你的 GitHub 用户名 / 仓库名。
  （首次配置由安装脚本/作者填写；公开仓库时自动更新无需令牌。）
"""

APP_VERSION = "1.1.4"

# GitHub 仓库（公开仓库，自动更新免令牌）
GITHUB_OWNER = "dangthiphuong2491991-a11y"
GITHUB_REPO = "VideoPromptTool"
