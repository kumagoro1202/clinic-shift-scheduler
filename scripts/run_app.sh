#!/usr/bin/env bash
# 管理者UIの起動ランチャー（Linux/WSL 開発環境用。Windows 本番環境は run_app.bat を使用）。
# 初回のみ仮想環境を作成し、依存パッケージをインストールしてから起動する。
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/python" ]; then
    echo "初回セットアップを実行しています..."
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi

.venv/bin/python -m streamlit run 02-src/ui/app.py
