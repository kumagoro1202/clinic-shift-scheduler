# 設計書インデックス

開発ロードマップ P4 の成果物。読み順は上から。

## アーキテクチャ概要

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — システム全体構成・データフロー・
  UI 技術選定・モジュール分割方針・依存ライブラリ・実装順序リスト（P6 / P7）

## 外部設計（external/）

- [`external/input-design.md`](external/input-design.md) — 入力データ設計
  （設定 YAML スキーマ・スタッフマスタ・診療カレンダー）
- [`external/output-design.md`](external/output-design.md) — 出力設計
  （画面表示・CSV・Excel 印刷レイアウト仮案・勤務記号）

## 内部設計（internal/）

- [`internal/data-model.md`](internal/data-model.md) — データモデル設計
  （入力側・月次拡張・出力側エンティティと関係）
- [`internal/engine-design.md`](internal/engine-design.md) — 最適化エンジン設計
  （CP-SAT 決定変数・HC/SC 実装方針・重みプリセット・性能）
