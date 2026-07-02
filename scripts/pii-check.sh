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
  if [ -z "$content" ] || [ ! -s "$ALLOWLIST_ACTIVE" ]; then
    echo "$content"
    return
  fi
  echo "$content" | grep -v -f "$ALLOWLIST_ACTIVE" || true
}

# セルフテスト（canary test）: 疑似PIIを一時ファイルに書き、スキャナが
# 検知できること（真陽性）を確認する。検知できなければスキャナが壊れて
# いる（パターン不一致・CRLF混入等）ため exit 1 で CI を落とす。
# 疑似PII文字列は \u エスケープ・文字列連結で組み立て、本スクリプト自身が
# スキャン対象になっても誤検知しないようにしている。実在の個人情報は不使用。
if [ "$1" = "--self-test" ]; then
  CANARY_FILE=$(mktemp /tmp/pii-canary.XXXXXX.md)
  trap 'rm -f "$CANARY_FILE"' EXIT

  {
    # 疑似人名 + 敬称（架空）: U+5C71 U+672C U+5148 U+751F
    printf '\u5c71\u672c\u5148\u751f\n'
    # 疑似電話番号（連結で組み立て）
    printf '%s%s%s\n' "090" "-0000" "-0000"
    # 疑似メールアドレス（連結で組み立て）
    printf '%s%s%s\n' "pii-canary" "@" "example.invalid"
    # 疑似住所: 都道府県+区（個人特定情報ではない）: U+6771 U+4EAC U+90FD U+5343 U+4EE3 U+7530 U+533A
    printf '\u6771\u4eac\u90fd\u5343\u4ee3\u7530\u533a\n'
  } > "$CANARY_FILE"

  echo "=== PII scanner self-test (canary) ==="
  if bash "$0" "$CANARY_FILE"; then
    echo "❌ SELF-TEST FAILED: canary pseudo-PII was NOT detected. Scanner is broken."
    exit 1
  else
    echo "✅ SELF-TEST PASSED: canary pseudo-PII was correctly detected."
    exit 0
  fi
fi

# 前処理: allowlist / blocklist からコメント行・空行・CR（CRLF対策）を除去して
# 一時ファイルに展開する。CRLF混入でパターンが不一致になる事故の根本対策であり、
# grep を1ファイルあたり1回に抑える性能対策でもある。
ALLOWLIST_ACTIVE=$(mktemp)
BLOCKLIST_ACTIVE=$(mktemp)
trap 'rm -f "$ALLOWLIST_ACTIVE" "$BLOCKLIST_ACTIVE"' EXIT
[ -f "$ALLOWLIST_FILE" ] && sed -e 's/\r$//' -e '/^#/d' -e '/^[[:space:]]*$/d' "$ALLOWLIST_FILE" > "$ALLOWLIST_ACTIVE"
[ -f "$BLOCKLIST_FILE" ] && sed -e 's/\r$//' -e '/^#/d' -e '/^[[:space:]]*$/d' "$BLOCKLIST_FILE" > "$BLOCKLIST_ACTIVE"

for file in "$@"; do
  # バイナリファイルはスキップ
  if ! file "$file" | grep -q text; then
    continue
  fi

  # pii-patterns.txt からパターンを読み込み検査
  if [ -f "$PATTERNS_FILE" ]; then
    while IFS= read -r pattern || [ -n "$pattern" ]; do
      pattern="${pattern%$'\r'}"
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

  # 姓ブロックリスト照合（全姓を grep -f で一括照合）
  if [ -s "$BLOCKLIST_ACTIVE" ]; then
    result=$(grep -nf "$BLOCKLIST_ACTIVE" "$file" 2>/dev/null || true)
    result=$(check_allowlist "$result")

    if [ -n "$result" ]; then
      echo "⚠️  Blocklisted surname detected in $file:"
      echo "$result"
      FAIL=1
    fi
  fi
done

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "❌ Personal information detected! Please anonymize before committing."
  echo "   See CLAUDE.md '個人情報保護ルール' for anonymization rules."
  echo "   匿名表記例: スタッフA / 看護師A / 受付A / リハA"
  exit 1
fi
