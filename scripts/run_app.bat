@echo off
REM 管理者UIの起動ランチャー（Windows 10/11・ダブルクリック起動用）。
REM 初回のみ仮想環境を作成し、依存パッケージをインストールしてから起動する。
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo 初回セットアップを実行しています...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

.venv\Scripts\python.exe -m streamlit run 02-src\ui\app.py

pause
