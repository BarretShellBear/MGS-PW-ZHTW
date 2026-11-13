#!/usr/bin/env bash
# MGS Peace Walker 繁體中文化 — SteamOS / Linux 啟動腳本（未經實機測試）
# 用法：在「桌面模式」開終端機，進入本資料夾後執行  bash steamos_install.sh
# 完整手把手步驟請看同資料夾的 SteamOS教學.md；加 --cli 可強制用文字模式，--jppack 路徑 指定日文包。
# 需要 python3（SteamOS 內建）；有 tkinter 會開視窗，沒有則自動改用命令列。
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "找不到 python3，請先安裝。"; exit 1
fi
if python3 -c "import numpy" >/dev/null 2>&1; then :; else
  echo "提示：影片中文化需要 python3 的 numpy 套件；只安裝漢化檔可忽略。"
fi
exec python3 zhtw_installer.py "$@"
