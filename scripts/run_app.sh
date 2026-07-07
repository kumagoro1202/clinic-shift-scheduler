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

# PYTHONPATH に 02-src を追加する（ui/ 配下から scheduler 等を import するため。
# 03-tests/conftest.py と同じ sys.path 構成に合わせる。P7-2 で ui/pages が
# scheduler.staff_repository を import するようになったため必須）。
PYTHONPATH="$(pwd)/02-src${PYTHONPATH:+:$PYTHONPATH}" .venv/bin/python -m streamlit run 02-src/ui/app.py
