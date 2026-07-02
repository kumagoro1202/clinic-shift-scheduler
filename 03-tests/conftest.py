"""テスト共通設定。02-src をインポートパスへ追加する。"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "02-src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
