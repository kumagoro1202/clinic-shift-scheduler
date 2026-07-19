# リリースノート

## v2.1.0-mvp（2026-07-19）

### 変更内容

- MVP 完成（ROADMAP P1〜P7 完遂・2026-07-08 PR #34 で機能実装完了）
  - 最適化エンジン（OR-Tools CP-SAT）による1ヶ月分シフト自動生成（CLI/UI）
  - 管理者UI（Streamlit）: スタッフ管理・休暇入力・シフト生成・手動編集・Excel 出力
  - Excel 出力・印刷レイアウト（A4 横 1 ページ・SC-003 週40時間警告の注記付き）
  - E2E テスト（Playwright 実ブラウザ）を含む全 179 テスト PASS
- 依存関係更新（dependabot PR #2〜#3・#35〜#40）
  - actions/checkout 4→7, markdownlint-cli2-action 19→24, actions/setup-python 5→6
  - pyyaml >=6.0.3, ruff >=0.15.21, streamlit >=1.59.1, ortools >=9.15.6755,
    pytest-playwright >=0.8.0
- 開発環境（WSL/Linux）でのフル動作確認を実施（シフト生成 OPTIMAL・UI 全画面一巡・Excel 出力）

### 注意事項

- 実データ投入・配布形態（Q-09）の確定は次フェーズとして別途計画する

## v2.0.0-initial（2026-03-01）

### 変更内容

- シフト作成システムv2 リポジトリ初期構成
- 7ステップAI自律開発ワークフロー設計
- 個人情報保護多層防御（3層）実装
- ADR-001〜ADR-007 策定

### 注意事項

- 実装言語・アーキテクチャは別cmdで選定予定
- `02-src/` 配下は言語選定後に充実する
