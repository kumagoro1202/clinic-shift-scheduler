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
├── 02-src/                      # 実装（Python 3.12 / ADR-008）
│   ├── cli.py                   # シフト生成CLI（バッチ実行用）
│   ├── scheduler/               # 最適化エンジン（OR-Tools CP-SAT）・設定読込
│   ├── exporters/               # CSV / Excel 出力
│   └── ui/                      # 管理者UI（Streamlit マルチページ）
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
│   ├── allowlist.txt           # False Positive除外リスト
│   ├── run_app.bat             # 管理者UI起動ランチャー（Windows）
│   └── run_app.sh              # 管理者UI起動ランチャー（Linux/WSL 開発用）
│
├── .pre-commit-config.yaml      # Pre-commitフック設定
├── .markdownlint.json           # Markdownlintルール設定
├── .gitattributes               # scripts/ のLF強制（PIIスキャナCRLF故障対策）
├── .gitignore
└── CLAUDE.md                    # プロジェクト固有ルール
```

## 管理者UIの起動

管理者UI（Streamlit）は `scripts/` の起動スクリプトから起動する。
初回実行時は仮想環境の作成・依存パッケージのインストールを自動で行う。

- **Windows 10/11（本番環境）**: `scripts\run_app.bat` をダブルクリック
- **Linux/WSL（開発環境）**: `bash scripts/run_app.sh`

起動後、`http://localhost:8501` にブラウザでアクセスする。

月次のシフト作成業務の操作手順は
[利用者マニュアル](01-docs/manual/USER_MANUAL.md) を参照する。

## 個人情報保護（PIIスキャン）

pre-commit フックと GitHub Actions CI（`pii-check.yml`）が `scripts/pii-check.sh` を
共通の検査ロジックとして参照し、日本人名（漢字+敬称・姓ブロックリスト）・電話番号・
メールアドレス・住所のパターンを検出する。誤検知の除外は `scripts/allowlist.txt` で
管理する（変更はPR必須）。

### canaryセルフテスト

CI は本スキャンの前に **canaryセルフテスト**（`scripts/pii-check.sh --self-test`）を
毎回実行し、スキャナ自体の検知能力を両方向から検証する。

- **真陽性検証**: 架空の疑似PII（疑似人名+敬称・疑似電話番号・疑似メール・疑似住所）を
  含む一時fixtureが検知されること。検知されなければ「スキャナ故障」としてCIを赤にする
- **真陰性検証**: 匿名化済みのクリーンなfixture（スタッフA 等）が素通りすること。
  誤検知過多への振れ戻りを検知する

これにより「スキャナが壊れているのにCIが緑のまま」という空回り状態
（例: パターン定義ファイルへのCRLF混入で全パターンが不一致になる故障）を構造的に排除する。
fixture は実行時に一時生成され、リポジトリにはコミットされない。文字列はすべて架空である。

### SELF-TEST FAILED が出た場合の対処

1. `scanner is broken`（真陽性失敗）: パターン定義が壊れている。
   `file scripts/*.txt` で CRLF 混入を確認し、`head -5 scripts/pii-patterns.txt | cat -A` で
   行末 `^M$` の有無を目視する。パターンを変更した直後なら正規表現の互換性を疑う
2. `over-detecting`（真陰性失敗）: パターンが過剰検知に振れている。
   直近のパターン・ブロックリスト変更をレビューし、匿名表記（スタッフA 等）が
   誤検知されない状態へ修正する
3. パターンを調整した場合は `bash scripts/pii-check.sh --self-test` をローカルで再実行し、
   両方向PASSを確認してからコミットする

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
