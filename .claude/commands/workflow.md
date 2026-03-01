# /workflow — 7ステップAI自律開発ワークフロー

## サブコマンド

| コマンド | 説明 |
|---------|------|
| `start <説明>` | 新規ワークフロー開始（Step 1: 要件確認から） |
| `status` | 現在の状態・進捗確認 |
| `next` | 次のステップを自動実行 |
| `auto` | Step 2〜6を自動連続実行（要件確定後に使用） |
| `resume <id>` | 中断から再開 |
| `approve` | Step 7: 最終承認（マージ実行） |
| `reject <理由>` | Step 7: 差戻し（Step 3に戻る） |
| `report` | 全レポートのサマリー表示 |
| `skip-code` | ドキュメントのみ変更時にコード実装をスキップ |

## 使用例

```bash
# 新機能の開発を開始
/workflow start "シフト自動割当機能の実装"

# Step 1で要件を確認した後、Step 2-6を自動実行
/workflow auto

# 最終承認（殿が実行）
/workflow approve

# 差戻し（殿が実行）
/workflow reject "スタッフの連続勤務制限が考慮されていない"
```

## 状態ファイル

`.claude/workflow-state/current.json` に現在の状態を保存。

## 詳細

`01-docs/DEVELOPMENT_WORKFLOW.md` を参照。
