# 新規参画者向けガイド

## はじめに

このリポジトリは **将軍システム（org-shogun）経由** で開発します。
このディレクトリでClaude Codeを直接立ち上げることはしません。

## 開発体制

```text
副院長（要求提供）→ 殿（最終意思決定）→ 将軍システム（org-shogun）→ このリポジトリ
```

## 必ず読むべき文書

1. `CLAUDE.md` — プロジェクト固有ルール（Gitアカウント・個人情報保護等）
2. `01-docs/DEVELOPMENT_WORKFLOW.md` — 開発ワークフロー
3. `01-docs/adr/README.md` — アーキテクチャ決定記録一覧

## Gitアカウント確認

```bash
git config user.name   # → kumagoro1202
git config user.email  # → kumagoro1202@users.noreply.github.com
```

## 個人情報保護の徹底

スタッフ名・患者情報・クリニック連絡先は絶対に記載禁止。
匿名表記を使用する: スタッフA / 看護師A / 受付A / リハA

詳細は `CLAUDE.md` の「個人情報保護ルール」を参照。
