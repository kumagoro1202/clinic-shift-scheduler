# clinic-shift-scheduler

クリニック向けシフト作成システム（v2）

## 概要

日勤のみのクリニックを対象とした、AIによるシフト自動作成システム。

- **勤務形態**: 9時間勤務・1時間休憩
- **対象**: 日勤のみのクリニック（夜勤・2交代・3交代なし）
- **維持する要件**: リハ室・受付の人数制限と診療時間

## 開発体制

```text
副院長（要求提供）→ プロジェクトオーナー（エンジニア）→ AIエージェントシステム（org-shogun）→ このリポジトリ
```

- PRの最終承認者: プロジェクトオーナー
- 副院長: 要求事項の提供者（技術的PRレビューは行わない）

## ディレクトリ構成

```text
clinic-shift-scheduler/
├── .claude/
│   ├── agents/                  # 7ステップワークフロー エージェント定義（5ファイル）
│   ├── commands/                # /workflow 等のカスタムコマンド
│   ├── reports/                 # ワークフロー実行レポート（git管理）
│   └── workflow-state/          # ワークフロー状態管理
│
├── .github/
│   ├── workflows/
│   │   ├── pr-check.yml        # Markdownlint CI
│   │   └── pii-check.yml       # 個人情報チェック CI
│   ├── dependabot.yml          # 依存関係自動更新
│   └── PULL_REQUEST_TEMPLATE.md
│
├── 01-docs/                     # ドキュメント
│   ├── spec/
│   │   ├── REQUIREMENTS.md      # 要求事項定義書
│   │   ├── CONSTRAINTS.md       # 制約条件一覧（HC/SC）
│   │   └── PII_INCIDENT_RESPONSE.md  # 個人情報漏洩時の対応手順
│   ├── design/                  # 設計書
│   │   ├── README.md
│   │   ├── ARCHITECTURE.md
│   │   ├── external/            # 外部設計（画面設計等）
│   │   └── internal/            # 内部設計（モジュール設計等）
│   ├── adr/                     # Architecture Decision Records
│   │   ├── README.md
│   │   ├── ADR-001-repo-structure.md
│   │   ├── ADR-002-test-directory.md
│   │   ├── ADR-003-dev-workflow.md
│   │   ├── ADR-004-ai-autonomous-workflow.md
│   │   ├── ADR-005-ai-cross-review-criteria.md
│   │   ├── ADR-006-dev-team-pr-flow.md
│   │   ├── ADR-007-pii-protection-multilayer.md
│   │   └── template.md
│   ├── manual/
│   │   └── USER_MANUAL.md       # 利用者マニュアル
│   ├── research/                # 技術調査レポート
│   ├── DEVELOPMENT_WORKFLOW.md  # 開発ワークフロー定義書
│   ├── ONBOARDING.md            # 新規参画者向けガイド
│   └── RELEASE_NOTES.md         # リリースノート
│
├── 02-src/                      # 実装（言語選定後に更新）
│   ├── backend/
│   └── frontend/
│
├── 03-tests/                    # テスト
│   ├── unit/                    # ユニットテスト
│   ├── integration/             # 統合テスト
│   └── e2e/                     # E2Eテスト（Playwright）
│
├── scripts/                     # ユーティリティスクリプト
│   ├── pii-check.sh            # 個人情報チェックスクリプト
│   ├── pii-patterns.txt        # 個人情報検出パターン定義
│   ├── names-blocklist.txt     # 日本の姓ブロックリスト
│   └── allowlist.txt           # False Positive除外リスト
│
├── .pre-commit-config.yaml      # Pre-commitフック設定
├── .markdownlint.json           # Markdownlintルール設定
├── .gitignore
└── CLAUDE.md                    # プロジェクト固有ルール
```

## 開発ワークフロー

7ステップAI自律開発ワークフロー（詳細: `01-docs/DEVELOPMENT_WORKFLOW.md`）

1. **Step 1**: 要件確認（🔴 HUMAN）
2. **Step 2**: 計画策定（🤖 AUTO）
3. **Step 3**: 実装（🤖 AUTO）
4. **Step 4**: 自動品質チェック（🤖 AUTO）
5. **Step 5**: AIクロスレビュー（🤖 AUTO）
6. **Step 6**: PR仕上げ（🤖 AUTO）
7. **Step 7**: 最終承認（🔴 HUMAN）

## 関連リポジトリ

- [org-shogun](https://github.com/kumagoro1202/org-shogun) — マルチエージェントAIエージェントシステム
- [shift-scheduler-claude](https://github.com/kumanoGoro/shift-scheduler-claude) — シフト作成システム v1（旧）
