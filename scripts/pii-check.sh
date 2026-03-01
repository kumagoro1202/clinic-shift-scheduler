#!/bin/bash
# 個人情報パターン検出スクリプト（Layer 2: Pre-commit Hook）
# 使用方法: scripts/pii-check.sh <ファイル1> [ファイル2] ...
set -e

FAIL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_FILE="$SCRIPT_DIR/pii-patterns.txt"
BLOCKLIST_FILE="$SCRIPT_DIR/names-blocklist.txt"
ALLOWLIST_FILE="$SCRIPT_DIR/allowlist.txt"

check_allowlist() {
  local content="$1"
  if [ -f "$ALLOWLIST_FILE" ]; then
    while IFS= read -r allowed || [ -n "$allowed" ]; do
      [[ "$allowed" =~ ^#.*$ ]] && continue
      [[ -z "$allowed" ]] && continue
      content=$(echo "$content" | grep -v "$allowed" || true)
    done < "$ALLOWLIST_FILE"
  fi
  echo "$content"
}

for file in "$@"; do
  # バイナリファイルはスキップ
  if ! file "$file" | grep -q text; then
    continue
  fi

  # pii-patterns.txt からパターンを読み込み検査
  if [ -f "$PATTERNS_FILE" ]; then
    while IFS= read -r pattern || [ -n "$pattern" ]; do
      [[ "$pattern" =~ ^#.*$ ]] && continue
      [[ -z "$pattern" ]] && continue

      result=$(grep -Pn "$pattern" "$file" 2>/dev/null || true)
      result=$(check_allowlist "$result")

      if [ -n "$result" ]; then
        echo "⚠️  PII detected in $file (pattern: $pattern):"
        echo "$result"
        FAIL=1
      fi
    done < "$PATTERNS_FILE"
  fi

  # 姓ブロックリスト照合
  if [ -f "$BLOCKLIST_FILE" ]; then
    while IFS= read -r surname || [ -n "$surname" ]; do
      [[ "$surname" =~ ^#.*$ ]] && continue
      [[ -z "$surname" ]] && continue

      result=$(grep -n "$surname" "$file" 2>/dev/null || true)
      result=$(check_allowlist "$result")

      if [ -n "$result" ]; then
        echo "⚠️  Surname detected in $file: $surname"
        echo "$result"
        FAIL=1
      fi
    done < "$BLOCKLIST_FILE"
  fi
done

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "❌ Personal information detected! Please anonymize before committing."
  echo "   See CLAUDE.md '個人情報保護ルール' for anonymization rules."
  echo "   匿名表記例: スタッフA / 看護師A / 受付A / リハA"
  exit 1
fi
