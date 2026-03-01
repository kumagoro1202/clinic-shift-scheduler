# Finalizer Agent — Step 6: PR仕上げ

## 役割

コミット整理・プッシュ・PR説明文の更新・PR Ready化を行う。

## 実行手順

1. **コミット整理**: 作業コミットをまとめて意味のあるコミットに整理
2. **プッシュ**: `git push origin <branch>`
3. **PR説明文更新**:
   - AIクロスレビュー結果（YAML出力のサマリ）を記載
   - 自動品質チェック結果（全PASS確認）を記載
4. **PR Ready化**: Draft → Ready for Review に変更

## コミットメッセージ規約

```text
<type>: <日本語の説明>

Co-Authored-By: Claude claude-sonnet-4-6 <noreply@anthropic.com>
```

type: feat / fix / docs / refactor / test / chore

## 個人情報チェック（最終確認）

コミットメッセージ・PR説明文に個人情報が含まれていないことを確認する。

## 出力

- Ready for Review 状態のPR
- AIレビューサマリ付きのPR説明文
- `.claude/reports/<workflow-id>.md` にレポート保存
