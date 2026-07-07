#!/bin/bash
# 個人情報パターン検出スクリプト（Layer 2: Pre-commit Hook）
# 使用方法: scripts/pii-check.sh <ファイル1> [ファイル2] ...
set -e

FAIL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 定義ファイルは環境変数で差し替え可能にする（--self-test の故意破壊テストが
# 空のパターン定義で本体を再帰呼び出しし、canary機構の健全性を検証するため）
PATTERNS_FILE="${PII_PATTERNS_FILE:-$SCRIPT_DIR/pii-patterns.txt}"
BLOCKLIST_FILE="${PII_BLOCKLIST_FILE:-$SCRIPT_DIR/names-blocklist.txt}"
ALLOWLIST_FILE="${PII_ALLOWLIST_FILE:-$SCRIPT_DIR/allowlist.txt}"

check_allowlist() {
  local content="$1"
  if [ -z "$content" ] || [ ! -s "$ALLOWLIST_ACTIVE" ]; then
    echo "$content"
    return
  fi
  echo "$content" | grep -v -f "$ALLOWLIST_ACTIVE" || true
}

# セルフテスト（canary test）: スキャナ自体の検知能力を両方向から検証する。
#   真陽性: 疑似PIIを含む一時fixtureが「検知されて失敗する」こと。検知しなければ
#           スキャナが壊れている（パターン不一致・CRLF混入等）ため exit 1 で CI を落とす
#   真陰性: 匿名化済みのクリーンなfixtureが「素通りする」こと。誤検知過多への
#           振れ戻り（オオカミ少年化）を検知する
# 疑似PII文字列は \u エスケープ・文字列連結で組み立て、本スクリプト自身が
# スキャン対象になっても誤検知しないようにしている。実在の個人情報は不使用。
# fixture は mktemp で実行時生成し trap で削除する（リポジトリにはコミットしない）。
if [ "$1" = "--self-test" ]; then
  CANARY_FILE=$(mktemp /tmp/pii-canary.XXXXXX.md)
  CLEAN_FILE=$(mktemp /tmp/pii-clean.XXXXXX.md)
  trap 'rm -f "$CANARY_FILE" "$CLEAN_FILE"' EXIT

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

  # 真陰性fixture: CLAUDE.md 準拠の匿名表記のみ（検知されてはならない）
  {
    printf '\u30b9\u30bf\u30c3\u30d5A\u306f9\u6642\u9593\u52e4\u52d9\n'
    printf '\u770b\u8b77\u5e2bB\u3068\u53d7\u4ed8C\u306e\u30b7\u30d5\u30c8\u3092\u8abf\u6574\n'
  } > "$CLEAN_FILE"

  echo "=== PII scanner self-test (canary) ==="
  if bash "$0" "$CANARY_FILE"; then
    echo "❌ SELF-TEST FAILED: canary pseudo-PII was NOT detected. Scanner is broken."
    exit 1
  fi
  echo "--- true positive OK: canary pseudo-PII was correctly detected ---"
  if ! bash "$0" "$CLEAN_FILE"; then
    echo "❌ SELF-TEST FAILED: clean (anonymized) fixture was falsely flagged. Scanner is over-detecting."
    exit 1
  fi
  echo "--- true negative OK: clean fixture passed without false positives ---"

  # 内部用語（組織ロール名・内部ID）canary: 追加パターンの検知能力をパターン系統ごとに
  # 個別検証する。用語は \u エスケープ・文字列連結で実行時に組み立て、本スクリプト自身が
  # スキャン対象になっても自己検知しないようにしている（既存 canary と同じ方針）。
  # 子プロセスの検知出力は /dev/null へ捨て、CIログに用語が残らないようにする。
  TERM_FILE=$(mktemp /tmp/pii-term.XXXXXX.md)
  ALLOWED_FILE=$(mktemp /tmp/pii-term-allowed.XXXXXX.md)
  EMPTY_PATTERNS=$(mktemp /tmp/pii-empty.XXXXXX)
  trap 'rm -f "$CANARY_FILE" "$CLEAN_FILE" "$TERM_FILE" "$ALLOWED_FILE" "$EMPTY_PATTERNS"' EXIT

  TERM_JA=$(printf '\u8ecd\u5e2b')             # 組織ロール名（日本語・コードポイント組み立て）
  TERM_ROMAJI=$(printf '%s%s' 'gun' 'shi')     # 組織ロール名（ローマ字・単語境界確認）
  TERM_CMD=$(printf '%s%s' 'cmd' '_123')       # 内部タスクID
  TERM_AGENT=$(printf '%s%s' 'ashi' 'garu5')   # 内部エージェントID（ロール名+号数字）
  for term in "$TERM_JA" "$TERM_ROMAJI" "$TERM_CMD" "$TERM_AGENT"; do
    printf 'internal term canary: %s\n' "$term" > "$TERM_FILE"
    if bash "$0" "$TERM_FILE" > /dev/null; then
      echo "❌ SELF-TEST FAILED: an internal-term canary was NOT detected. Scanner is broken."
      exit 1
    fi
  done
  echo "--- true positive OK: all internal-term canaries were correctly detected ---"

  # 真陰性: allowlist 済みの正規参照（リポジトリ名）を含む行は素通りすること
  printf 'see the %s%s repository for details\n' 'org-sho' 'gun' > "$ALLOWED_FILE"
  if ! bash "$0" "$ALLOWED_FILE" > /dev/null; then
    echo "❌ SELF-TEST FAILED: allowlisted repository reference was falsely flagged. Scanner is over-detecting."
    exit 1
  fi
  echo "--- true negative OK: allowlisted internal-term reference passed ---"

  # 故意破壊テスト: パターン定義を空に差し替えると canary が検知されなくなる
  # （=検知が本当にパターン定義に依存している）ことを確認する。ここで検知が
  # 発生する場合、真陽性テストがパターン以外の要因で通っており、canary 機構
  # 自体が壊れを検知できない状態にある。
  printf 'internal term canary: %s\n' "$TERM_JA" > "$TERM_FILE"
  if ! PII_PATTERNS_FILE="$EMPTY_PATTERNS" PII_BLOCKLIST_FILE="$EMPTY_PATTERNS" bash "$0" "$TERM_FILE" > /dev/null; then
    echo "❌ SELF-TEST FAILED: detection fired even with patterns disabled. Breakage test cannot validate the canary."
    exit 1
  fi
  echo "--- breakage-detection OK: canary goes undetected when patterns are disabled, so a broken scanner would be caught ---"

  echo "✅ SELF-TEST PASSED: true positive + true negative + breakage detection all as expected."
  exit 0
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
