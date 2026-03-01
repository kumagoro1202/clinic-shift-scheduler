# 個人情報インシデント対応手順

> **重要度**: 【MANDATORY】パブリックリポジトリへの個人情報コミット時は即時対応が必要

## 事故パターンと判断フロー

```text
個人情報コミットを検知
  ├── まだpushしていない場合 → Section 1: ローカル修正
  └── push済みの場合
        ├── コミットが古い（他のコミットが積み重なっている）→ Section 2: 履歴浄化
        └── 最新コミット → Section 1: ローカル修正 → push
```

## Section 1: ローカル修正（push前）

```bash
# 1. 該当ファイルを修正して個人情報を削除
# 2. 最新コミットを修正する場合
git commit --amend

# 3. 修正済みを確認してからpush
git log --oneline -5
git push origin <branch>
```

## Section 2: 履歴浄化（push済みの場合）

**⚠️ この操作は取り消し不可。必ず全員に連絡してから実施する。**

### Step 1: リポジトリを即時プライベートに変更

1. GitHub → Settings → Danger Zone → Change repository visibility
2. **Private** に変更（これにより一般公開を即時停止）

### Step 2: 影響確認

```bash
# 個人情報がどのコミットに含まれるか確認
git log --all --full-history -- <ファイルパス>
git log -S "個人情報の文字列" --all
```

### Step 3: BFG Repo-Cleaner で履歴浄化

```bash
# BFGのダウンロード
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar -O bfg.jar

# ミラーリング
git clone --mirror https://github.com/kumagoro1202/clinic-shift-scheduler.git clinic-shift-scheduler.git

# 特定ファイルを全履歴から削除する場合
java -jar bfg.jar --delete-files <ファイル名> clinic-shift-scheduler.git

# 特定文字列を全履歴から削除する場合
echo "個人情報の文字列" > strings.txt
java -jar bfg.jar --replace-text strings.txt clinic-shift-scheduler.git

# 履歴の最終化
cd clinic-shift-scheduler.git
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# force push
git push --force
```

### Step 4: パブリックに戻す

BFG完了を確認してから：

1. GitHub → Settings → Danger Zone → Change repository visibility
2. **Public** に変更

### Step 5: 事後対応

- プロジェクトオーナーに報告
- 本事故の根本原因をADRに記録
- pii-check.shのパターンを強化（もし検出漏れが原因の場合）

## 連絡先

| 役割 | 対応 |
|------|------|
| プロジェクトオーナー（エンジニア） | 即時報告。すべての技術的判断を委ねる |
| AIエージェントシステム | inbox_write.sh で報告 |

## 予防策

本事故が発生した場合は、以下を必ず見直す:

1. `scripts/pii-patterns.txt` — パターンに抜け穴がなかったか
2. `scripts/names-blocklist.txt` — ブロックリストに不足がなかったか
3. CLAUDE.md の匿名化ルール — ルールが明確か
4. pre-commit hook の設定 — 正しく動作しているか
