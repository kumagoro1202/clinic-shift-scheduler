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

REM PYTHONPATH に 02-src を追加する（ui\ 配下から scheduler 等を import するため。
REM 03-tests\conftest.py と同じ sys.path 構成に合わせる。P7-2 で ui\pages が
REM scheduler.staff_repository を import するようになったため必須）。
set "PYTHONPATH=%CD%\02-src;%PYTHONPATH%"
.venv\Scripts\python.exe -m streamlit run 02-src\ui\app.py

pause
