# 設定スキーマ定義（schema_version: 1）

シフト作成エンジンが読み込む YAML 設定ファイルのスキーマ定義。
設計方針は要求事項定義書（`01-docs/spec/REQUIREMENTS.md` 3章「設定駆動」）に基づき、
診療所固有の値はすべて本設定ファイルで定義する（ソースコードへのハードコード禁止）。

サンプル設定: [`config/samples/sample_clinic.yaml`](samples/sample_clinic.yaml)
（テスト専用・架空スタッフA〜E。実運用値は要確認事項の回答後に別ファイルとして作成する）

## 全体構造

```yaml
schema_version: 1
work_rules: { ... }      # 勤務体系
options: { ... }         # オプション機能の ON/OFF
slot_minutes: 30         # 時間解像度
day_types: { ... }       # 曜日別の日種別
clinic_hours: { ... }    # 曜日別の診療時間（参考情報）
shift_patterns: [ ... ]  # 勤務パターン
areas: [ ... ]           # 業務エリアと必要人数
staff: [ ... ]           # スタッフ定義
```

## work_rules（勤務体系）

要求事項定義書 4章「新勤務体系の定義【確定】」に対応する。

| キー | 型 | 説明 | サンプル値 |
|------|-----|------|-----------|
| `binding_hours` | int | 終日勤務の拘束時間（時間） | 9 |
| `break_minutes` | int | 休憩時間（分・1回） | 60 |
| `working_hours` | int | 実働時間（時間） | 8 |
| `break_window.start` | "HH:MM" | 休憩を開始できる最早時刻（暫定値・Q-04） | "12:00" |
| `break_window.end` | "HH:MM" | 休憩が終了していなければならない時刻 | "15:30" |

検証ルール: `binding_hours * 60 == working_hours * 60 + break_minutes` であること。

## options（オプション機能）

| キー | 型 | 説明 | 初期値 |
|------|-----|------|--------|
| `weekly_hours_check.enabled` | bool | 週労働時間チェックの ON/OFF（FR-07） | false |
| `weekly_hours_check.limit_hours` | int | 週の上限労働時間 | 40 |
| `strict_single_break.enabled` | bool | HC-006 厳格形（同時複数名休憩の一律禁止）の ON/OFF | false |

## slot_minutes（時間解像度）

制約計算の時間刻み（分）。診療時間・必要人数・勤務パターンの時刻境界は
すべてこの値の倍数に揃えること（揃っていない場合は設定エラー）。

## day_types（曜日別の日種別）

キーは `mon`〜`sun`。値は以下のいずれか。

| 値 | 意味 | サンプルでの該当曜日 |
|----|------|--------------------|
| `full` | 終日診療日 | 月・火・金 |
| `short` | 午後短縮日 | 水 |
| `half` | 午前のみ診療日 | 木・土 |
| `closed` | 休診日 | 日 |

## clinic_hours（診療時間）

曜日別の午前・午後診療時間（要求事項定義書 5.1節）。
現バージョンでは参考情報（表示・文書化用）であり、制約計算は
`areas.requirements` の時間帯定義を使用する。

```yaml
clinic_hours:
  mon: { am: ["09:00", "12:30"], pm: ["15:30", "18:30"] }
  sun: { am: null, pm: null }   # 休診は null
```

## shift_patterns（勤務パターン）

スタッフが 1 日に選択できる勤務パターン。時差出勤（Q-05）はパターンの
追加のみで表現できる。

| キー | 型 | 説明 |
|------|-----|------|
| `name` | str | パターン名（一意） |
| `day_types` | list | このパターンを選択できる日種別 |
| `start` / `end` | "HH:MM" | 出勤・退勤時刻（拘束時間の範囲） |
| `break_minutes` | int | 休憩時間（分）。0 = 休憩なし（半日勤務） |

検証ルール: `break_minutes > 0` のパターンは
「拘束時間（end - start）が `work_rules.binding_hours` と一致」かつ
「休憩が `work_rules.break_minutes` と一致」すること。

## areas（業務エリアと必要人数）

要求事項定義書 5.2節に対応する。必要人数は曜日ごとに時間帯（band）の
リストで定義する（YAML アンカーで同種の曜日を共通化できる）。

| キー | 型 | 説明 |
|------|-----|------|
| `name` | str | エリア名（一意）。例: `rehab`, `reception` |
| `required_skills` | list | 配置に必要なスキルキー。いずれか 1 つ以上のスコアが 1 以上であれば配置可能 |
| `requirements.<weekday>` | list | その曜日の必要人数の時間帯リスト |
| `requirements.<weekday>[].start` / `end` | "HH:MM" | 時間帯 |
| `requirements.<weekday>[].headcount` | int | 必要人数（下限） |

## staff（スタッフ定義）

| キー | 型 | 説明 |
|------|-----|------|
| `name` | str | スタッフ名（テストデータは架空名のみ） |
| `employment` | str | `full_time` / `part_time` |
| `weekly_workdays` | int | 週の勤務日数上限 |
| `skills` | map | スキルスコア（0〜100）。キー: `rehab` / `reception_am` / `reception_pm` / `general` |
| `vacations` | list | 休暇。`{ weekday: mon〜sun, kind: full/am/pm }` |

スキルスコアは要求事項定義書 6.2節の 4 項目（リハ室・受付午前・受付午後・
総合対応力）に対応する。バッチ1（本バージョン）では「スコア 0 = 配置不可、
1 以上 = 配置可能」の資格フラグとしてのみ使用し、スコアの大小を用いた
スキルバランス最適化（ソフト制約）は後続フェーズで実装する。

## 制約エンジンとの対応（バッチ1で実装済みのハード制約）

| ID | 内容 | 参照する設定 |
|----|------|-------------|
| HC-001 | 各エリア・各時間帯の必要人数を満たす | `areas.requirements` |
| HC-002 | 同一時刻に複数エリアへ配置しない | （設定不要・常時適用） |
| HC-003 | 勤務時間制約（拘束9h・休憩1h・実働8h・週勤務日数） | `work_rules` / `shift_patterns` / `staff.weekly_workdays` |
| HC-004 | 休暇・休日の制約 | `staff.vacations` / `day_types` |

## 未確定事項（要求事項定義書 10章）との対応

未確定の値は設定項目の暫定初期値として保持しており、回答確定後は
**設定ファイルの更新のみ**で反映できる（コード変更不要）。

| 要確認 ID | 対応する設定 | サンプルでの暫定値 |
|-----------|-------------|-------------------|
| Q-03（半日勤務） | `shift_patterns`（half） | 08:30〜13:30・休憩なし |
| Q-04（休憩時間帯） | `work_rules.break_window` | 12:00〜15:30 |
| Q-05（時差出勤） | `shift_patterns`（early / late） | 08:30 出勤と 09:30 出勤の 2 種 |
| Q-06（受付必要人数） | `areas.requirements` | テスト用縮小値（受付 2 名） |
| Q-08（パート勤務） | `staff.employment` / `weekly_workdays` | パート 2 名・週 5 日 |
