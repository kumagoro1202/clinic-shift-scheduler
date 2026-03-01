# OSSライブラリ・フレームワーク調査
## シフトスケジューリング最適化ライブラリ比較（日勤クリニック向け）

> 作成日: 2026-02-28
> 調査者: ashigaru1 (subtask_238a)
> 前提: **対象クリニックは日勤のみ（2交代・3交代・夜勤は一切発生しない）**

---

## 前提条件の整理

本調査は、**日勤のみのクリニック**向けシフトスケジューリングを対象とする。

- シフト種別: 日勤1種類（または早番・遅番程度の2種類）
- 夜勤ローテーション・夜勤疲労計算・病棟3交代対応: **対象外**
- 複雑な夜勤専用機能は評価に影響しない（オーバースペックとして△評価）

---

## 概要・比較表

| # | ライブラリ | 言語 | 手法 | GitHub★ | ライセンス | 日勤適用 | 推奨度 |
|---|-----------|------|------|---------|-----------|---------|--------|
| 1 | **Google OR-Tools (CP-SAT)** | Python/Java/C# | CP + SAT | 13.1k | Apache-2.0 | ◎ | ★★★★★ |
| 2 | **PuLP** | Python | LP/MILP | 2.4k | MIT | ◎ | ★★★★☆ |
| 3 | **Pyomo** | Python | LP/MILP/非線形 | 2.4k | BSD-3 | ◎ | ★★★★☆ |
| 4 | **Timefold Solver** | Java/Kotlin | メタヒューリスティクス | 1.6k | Apache-2.0 | ◎ | ★★★★☆ |
| 5 | **HiGHS** | Python/C++ (ソルバー) | LP/MILP/QP | 1.5k | MIT | ○ | ★★★★☆ |
| 6 | **CVXPY** | Python | 凸最適化/MILP | 6.1k | Apache-2.0 | ○ | ★★★☆☆ |
| 7 | **CBC (COIN-OR)** | C++ (ソルバー) | MILP | 975 | EPL-2.0 | ○ | ★★★☆☆ |
| 8 | **SCIP** | C/Python | 制約整数計画 | 500+ | Apache-2.0 | ○ | ★★★☆☆ |
| 9 | **choco-solver** | Java | 制約プログラミング | 754 | BSD-4 | ○ | ★★★☆☆ |
| 10 | **python-constraint** | Python | CSP | 510 | BSD-2 | △ | ★★☆☆☆ |
| 11 | **GLPK** | C (ソルバー) | LP/MILP | — | GPL-3.0 | ○ | ★★☆☆☆ |
| 12 | **JaCoP** | Java | 制約プログラミング | 232 | 要確認 | △ | ★★☆☆☆ |
| 13 | **OptaPy** | Python(Java wrap) | メタヒューリスティクス | 307 | Apache-2.0 | △ | ★☆☆☆☆ |
| 14 | **OptaPlanner** | Java | メタヒューリスティクス | — | Apache-2.0 | ○ | ★★☆☆☆ |
| 15 | **constraint.js 系** | JavaScript | CSP | — | 各種 | × | ★☆☆☆☆ |

---

## 各ライブラリ詳細

---

### 1. Google OR-Tools（CP-SAT）

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/google/or-tools / https://developers.google.com/optimization |
| 言語 | Python / Java / C# / C++ |
| ライセンス | Apache-2.0 |
| GitHub★ | 13.1k（Fork: 2.4k） |
| 最新バージョン | v9.15（2026年1月12日） |
| 手法 | CP-SAT（制約プログラミング + SAT）、LP（Glop）、VRP |
| 更新頻度 | 非常に活発（Google継続メンテ） |

**概要**
Googleが開発する汎用オペレーションズリサーチツールスイート。CP-SATソルバーがシフトスケジューリングに最も適しており、C++実装のためPythonラッパーでも高速。

**日勤クリニックへの適用可能性: ◎**
- 公式に `shift_scheduling_sat.py`（看護師スケジュール）のサンプルを提供
- 日勤1〜2種類のシンプルなシフトから大規模まで対応
- 夜勤特化機能は不要だが影響もなし（汎用なので余計な機能はない）
- ハード制約（最低人数確保など）もソフト制約（希望休など）も統一的に扱える

**長所**
- シフト事例の公式サンプル・チュートリアルが充実
- Python APIが自然で学習コストが低い
- スケールアップ時の性能が最高水準
- Timefoldより少ないコードで制約を記述できるケースも多い

**短所**
- ドメインモデリング（どの変数をどう定義するか）の設計が重要で、初手が難しい場合がある
- 夜勤管理や複雑な要求に拡張する場合は大規模リファクタが必要になることも

---

### 2. PuLP

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/coin-or/pulp / https://coin-or.github.io/pulp/ |
| 言語 | Python |
| ライセンス | MIT |
| GitHub★ | 2.4k（Fork: 425） |
| 最新バージョン | 3.3.0（2025年9月18日） |
| 手法 | LP / MILP |
| 更新頻度 | 活発（COIN-ORプロジェクト） |

**概要**
Python向けLP/MILPモデリングライブラリ。shift-scheduler-claudeで現在使用中。バックエンドソルバー（CBC, HiGHS, CPLEX, Gurobi等）に問題を渡して解く。

**日勤クリニックへの適用可能性: ◎**
- 日勤のみのシンプルなシフト問題はLP/MILPで十分表現可能
- 「最低○人確保」「一人あたり週○時間以内」などの制約を直感的に記述
- Walmartシフト自動化など多数の実務事例あり

**長所**
- MITライセンスで商用利用自由
- 複数バックエンドソルバーに切り替え可能（無料: CBC/HiGHS → 高性能: Gurobi/CPLEX）
- 既存実装を流用できる（現行維持が最も低コスト）
- 中規模問題（〜50名、1ヶ月分）を2分以内で解いた実績あり

**短所**
- 「できれば○○したい」という軟制約の優先度付けが煩雑
- 大規模問題（100名超 × 複雑な制約）ではOR-Toolsより遅い場合がある

---

### 3. Pyomo

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/Pyomo/pyomo / http://www.pyomo.org/ |
| 言語 | Python |
| ライセンス | BSD-3-Clause |
| GitHub★ | 2.4k（Fork: 多数） |
| 最新バージョン | 6.10.0（2026年2月20日） |
| 手法 | LP / MILP / 非線形 / 確率的計画 |
| 更新頻度 | 非常に活発 |

**概要**
Pythonベースの数理計画モデリング言語。PuLPより表現力が高く、より複雑なモデルや確率的スケジューリングに対応。

**日勤クリニックへの適用可能性: ◎**
- 日勤向け週次スタッフスケジューリングのチュートリアルあり
- PuLPと同様のアプローチで、より複雑な制約に拡張しやすい

**長所**
- PuLPより柔軟、複雑なモデル構造に対応
- ソルバー非依存（GLPK/CBC/CPLEX/Gurobi/HiGHS等）
- オブジェクト指向でモデルを整理しやすい

**短所**
- PuLPより学習コストが高い
- 日勤のみ程度のシンプルな問題ではPuLPとほぼ同等

---

### 4. Timefold Solver（Java/Kotlin）

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/TimefoldAI/timefold-solver / https://solver.timefold.ai/ |
| 言語 | Java / Kotlin |
| ライセンス | Apache-2.0（Community Edition） |
| GitHub★ | 1.6k（Fork: 180） |
| 最新バージョン | v1.31.0（2026年2月11日） |
| 手法 | メタヒューリスティクス（タブーサーチ、SA等）、制約ストリーム |
| 更新頻度 | 非常に活発 |

**概要**
OptaPlannerの後継として2023年にフォーク。TimefoldAIが主導。Employee Shift Schedulingのクイックスタートを公式提供。Java 21+必須。

**日勤クリニックへの適用可能性: ◎**
- Employee Shift Schedulingの公式サンプルでスキル要件・可用性・シフトパターンに対応
- 日勤のみのシンプルなスケジュールから複雑な要件まで対応
- リアルタイム再スケジューリング（当日の急な欠勤対応）にも対応

**長所**
- シフトスケジューリング専用ドキュメント・サンプルが最も充実
- ソフト制約（希望休など）とハード制約を統一的に宣言的に記述
- 企業実績多数（医療機関・製造業）
- OR-Toolsより自然なドメインモデリング（Staff変数でシフトを直接表現）

**短所**
- Java 21+必須（Pythonプロジェクトへの統合が複雑）
- Community Editionはシングルスレッドのみ
- Pythonラッパーは2025年10月アーカイブ済みで使用不可

---

### 5. HiGHS（ソルバー）

| 項目 | 内容 |
|------|------|
| 公式URL | https://highs.dev/ / https://github.com/ERGO-Code/HiGHS |
| 言語 | C++ + Python (highspy), Fortran, C# |
| ライセンス | MIT |
| GitHub★ | 1.5k（Fork: 290） |
| 最新バージョン | 積極的に更新中（2025年以降も継続） |
| 手法 | LP / MILP / QP（シンプレックス法、内点法） |
| 更新頻度 | 活発 |

**概要**
高性能なオープンソースLP/MILPソルバー。エディンバラ大学が開発。PuLPやCVXPYのバックエンドとして使用可能。近年急速に性能向上し、商用ソルバーに匹敵するケースも。

**日勤クリニックへの適用可能性: ○**
- PuLP/PyomoのバックエンドソルバーとしてLP/MILPシフト問題を解ける
- 単体でも`pip install highspy`でPythonから使用可能
- ソルバーなので、直接使う場合はモデリング層が別途必要

**長所**
- MITライセンスで商用利用自由
- 近年の性能改善により無料ソルバーの中で最高クラスの性能
- CVXPY 1.8でデフォルトMILPソルバーに採用

**短所**
- ソルバーのみ（モデリングAPIは別途必要）
- PuLP/Pyomo経由で使うのが一般的で、単体での使用は煩雑

---

### 6. CVXPY

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/cvxpy/cvxpy / https://www.cvxpy.org/ |
| 言語 | Python |
| ライセンス | Apache-2.0 |
| GitHub★ | 6.1k（Fork: 多数） |
| 最新バージョン | 1.8.1（2026年2月3日） |
| 手法 | 凸最適化（LP/QP/SDP/SOCP）、MILP |
| 更新頻度 | 活発 |

**概要**
Stanfordが開発した凸最適化問題向けPython DSL。数学的な表現が自然でコードが読みやすい。

**日勤クリニックへの適用可能性: ○**
- LP/MILPとして定式化すれば日勤シフト問題に適用可能
- ただしシフトスケジューリング固有のサンプルは少なく、PuLP/Pyomoが先行

**長所**
- 数学的表現が自然で可読性が高い
- 学術研究での知名度が高い

**短所**
- シフト問題固有のサポートなし（PuLP/Pyomoの方が適している）
- MILP性能はPyomoより劣る場合がある

---

### 7. CBC（COIN-OR Branch-and-Cut、ソルバー）

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/coin-or/Cbc / https://coin-or.github.io/Cbc/ |
| 言語 | C++ |
| ライセンス | Eclipse Public License 2.0 |
| GitHub★ | 975（Fork: 多数） |
| 最新バージョン | 2.10.12（2024年8月） |
| 手法 | MILP（Branch-and-Cut） |
| 更新頻度 | 活発（2024年も更新） |

**概要**
COIN-ORプロジェクトが提供するオープンソースMILPソルバー。PuLPのデフォルトバックエンドとして広く使われている。

**日勤クリニックへの適用可能性: ○**
- PuLPのデフォルトバックエンドとして既にshift-scheduler-claudeで使用中
- 日勤シフトスケジューリング規模であれば十分な性能

**長所**
- PuLP利用者には透明的（設定不要で使える）
- オープンソース・無料

**短所**
- 単体では使いにくい（PuLP/Pyomo経由が一般的）
- 性能はHiGHSに劣る面がある

---

### 8. SCIP（Solving Constraint Integer Programs）

| 項目 | 内容 |
|------|------|
| 公式URL | https://www.scipopt.org/ / https://github.com/scipopt/scip |
| 言語 | C + Python (PySCIPOpt) |
| ライセンス | Apache-2.0（v8.0.3以降） |
| GitHub★ | 500+（PySCIPOpt: 700+） |
| 手法 | 制約整数計画（CIP）、MILP、MINLP |
| 更新頻度 | 活発 |

**概要**
ドイツのZuse Institute Berlinが開発。制約整数計画（MILP + 制約プログラミングの融合）に対応。PySCIPOptでPythonから使用可能。

**日勤クリニックへの適用可能性: ○**
- LP/MILP問題として定式化すれば日勤シフト問題に対応可能
- ただしシフト向けの公式サンプルは少なく、PuLP/OR-Toolsが先行

**長所**
- 学術分野での実績が豊富
- Apache-2.0ライセンス（商用利用可）

**短所**
- シフトスケジューリング向けのドキュメントが少ない
- PuLP/OR-Toolsほどシフト問題の事例が充実していない

---

### 9. choco-solver

| 項目 | 内容 |
|------|------|
| 公式URL | https://choco-solver.org/ / https://github.com/chocoteam/choco-solver |
| 言語 | Java |
| ライセンス | BSD-4-Clause |
| GitHub★ | 754（Fork: 153） |
| 最新バージョン | 5.0.0（2026年2月2日） |
| 手法 | 制約プログラミング（CP） |
| 更新頻度 | 活発 |

**概要**
JavaのオープンソースCP（制約プログラミング）ライブラリ。JaCoP・TimefoldよりもCPに特化。「Shift Minimisation Personnel Task Scheduling Problem」のケーススタディとして利用実績あり。

**日勤クリニックへの適用可能性: ○**
- CPベースでシフト最小化・スタッフ割り当て問題に適用可能
- 日勤シフトでも問題なく適用できる

**長所**
- v5.0.0（2026年2月）と最近も活発に更新
- Discordによるコミュニティサポートあり

**短所**
- Java必須でPythonプロジェクトには不向き
- TimefoldよりシフトスケジューリングのためのHigh-Level APIが少ない

---

### 10. python-constraint

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/python-constraint/python-constraint |
| 言語 | Python |
| ライセンス | BSD-2-Clause |
| GitHub★ | 510（Fork: 72） |
| 手法 | CSP（バックトラッキング、MinConflicts） |
| 更新頻度 | コミュニティが引き継ぎ、`pip install python-constraint2`を使用 |

**概要**
有限ドメインのCSPソルバー。小規模問題向け。警察官スケジューリングなどの事例あり。

**日勤クリニックへの適用可能性: △**
- 10名以下の小規模なら使用可能
- 最適化（コスト最小化）ではなく制約充足のみ
- 日勤クリニック規模（数十名）では性能が不十分

**長所**: 軽量、インストール簡単
**短所**: 大規模問題に対応不可、軟制約扱いが困難

---

### 11. GLPK（GNU Linear Programming Kit、ソルバー）

| 項目 | 内容 |
|------|------|
| 公式URL | https://www.gnu.org/software/glpk/ |
| 言語 | C（Python: PyGLPK, Pyomo/PuLP経由） |
| ライセンス | GPL-3.0（注意：商用利用は要検討） |
| GitHub★ | GNUプロジェクト（GitHubなし） |
| 手法 | LP / MILP（シンプレックス法、内点法） |
| 更新頻度 | 低め（枯れた技術） |

**概要**
GNUプロジェクトのLP/MILPソルバー。PuLPのバックエンドとして使用可能だが、HiGHSやCBCに性能で劣る。

**日勤クリニックへの適用可能性: ○**
- PuLP経由でシフト問題に適用可能だが、**HiGHSやCBCに置き換えることを推奨**

**長所**: 広く枯れた技術、動作実績豊富
**短所**: GPL-3.0ライセンス（商用組み込み時は注意必要）、性能は最新ソルバーに劣る

---

### 12. JaCoP

| 項目 | 内容 |
|------|------|
| 公式URL | https://jacop.cs.lth.se/ / https://github.com/radsz/jacop |
| 言語 | Java / Kotlin / Scala DSL |
| ライセンス | 要確認（商用ライセンスあり） |
| GitHub★ | 232（Fork: 59） |
| 最新バージョン | 4.10.0（2023年11月） |
| 手法 | 制約プログラミング（CP） |
| 更新頻度 | 低め（年数回程度） |

**概要**
ルンド大学が開発したJava CPソルバー。MiniZincフロントエンドに対応。9万行超のコード規模。

**日勤クリニックへの適用可能性: △**
- CPとして日勤スケジューリングに適用は可能
- ただしTimefold・choco-solverと比較するとシフト固有機能が少なく、コミュニティも小さい

**長所**: FlatZinc（MiniZinc）対応
**短所**: 商用ライセンスが不明確、Timefoldに比べてユーザー数が少ない

---

### 13. OptaPy（非推奨）

| 項目 | 内容 |
|------|------|
| 公式URL | https://github.com/optapy/optapy |
| 言語 | Python（内部はJava） |
| ライセンス | Apache-2.0 |
| GitHub★ | 307 |
| 最新バージョン | 9.37.0b0（2023年4月 — 更新停止） |

**概要**
OptaPlannerのPythonラッパー。内部でJVM起動。2024年のOptaPlanner EOL以降、事実上メンテナンス停止。

**日勤クリニックへの適用可能性: △**
- 技術的には適用可能だが**開発停止のため非推奨**

---

### 14. OptaPlanner（EOL）

| 項目 | 内容 |
|------|------|
| 公式URL | https://optaplanner.org/ |
| 言語 | Java |
| ライセンス | Apache-2.0 |
| EOL | 2024年5月30日（Red HatよりEOL宣言） |

**概要**
Timefold Solverの前身。Red HatがEOL宣言、後継はTimefold Solver。

**日勤クリニックへの適用可能性: ○**（技術的には可能だがEOLのため非推奨）

---

### 15. constraint.js 系（JavaScript）

| 項目 | 内容 |
|------|------|
| 代表URL | https://github.com/soney/ConstraintJS など |
| 言語 | JavaScript |
| 手法 | CSP（制約充足） |

**概要**
JavaScriptのCSPライブラリ群。npm上に複数存在するが、いずれも小規模・実績なし。

**日勤クリニックへの適用可能性: ×**
- シフト最適化のための数理計画機能が実質なし
- Pythonエコシステムと比較してライブラリ品質・実績が大幅に劣る

---

## 日勤クリニック向け推奨ライブラリ TOP3

### 🥇 第1位: Google OR-Tools（CP-SAT）

**推奨理由:**
1. **公式シフトスケジューリングサンプルあり**: 「看護師スケジューリング」の完全実装例を公式ドキュメントに提供。日勤への適用はさらにシンプル。
2. **性能**: CP-SATは業界最高水準。日勤のみのシンプルな問題から、スタッフ数十名の中規模問題まで高速に解ける。
3. **Python対応**: `pip install ortools` のみで使用開始可能。
4. **将来拡張性**: 仮に将来的に複雑な制約（スキル要件・連続勤務制限等）が追加されても、CP-SATは対応可能。
5. **ライセンス**: Apache-2.0で商用利用自由。

```python
# 例: OR-Tools CP-SAT でのシフト割り当て
from ortools.sat.python import cp_model
model = cp_model.CpModel()
# シフト変数: shifts[(n, d, s)] = 1 ならスタッフnが日付dのシフトsに勤務
shifts = {}
for n in range(num_nurses):
    for d in range(num_days):
        for s in range(num_shifts):
            shifts[(n, d, s)] = model.new_bool_var(f'shift_n{n}_d{d}_s{s}')
```

---

### 🥈 第2位: PuLP（現行維持）+ HiGHSソルバー

**推奨理由:**
1. **既存資産の活用**: shift-scheduler-claudeで現在使用中。移行コストゼロで継続利用できる。
2. **日勤専用には十分**: 2交代以下のシンプルなシフトであれば、LP/MILPで十分に表現・最適化できる。
3. **バックエンドをHiGHSに切り替えると性能向上**: PuLP 3.x では`solver=PULP_CBC_CMD()`をHiGHSに変更するだけで性能改善が見込める。
4. **MITライセンス**: 商用利用自由。

**改善提案**: 現行の CBC ソルバーを HiGHS に切り替えることで、同じコードベースでも求解速度の向上が期待できる。

```python
import pulp
# HiGHSをバックエンドに使用（PuLP 3.x）
prob = pulp.LpProblem("shift_scheduling", pulp.LpMinimize)
solver = pulp.HiGHS_CMD()
prob.solve(solver)
```

---

### 🥉 第3位: Timefold Solver（Java環境の場合）

**推奨理由:**
1. **シフトスケジューリング専用**: Employee Shift Schedulingのクイックスタートを公式提供。「スタッフの可用性・スキル・シフトパターン」を宣言的に記述。
2. **日勤クリニックへの最適マッチ**: 複雑な夜勤ローテーション機能も持つが、日勤のみの設定でも動作。リアルタイム再スケジューリング（急な欠勤対応）が強み。
3. **OptaPlanner後継で安定**: 2024年のOptaPlanner EOL後もTimefoldが積極的に開発継続中。
4. **条件**: Java 21+環境が必要。Pythonプロジェクトには不向き。

---

## まとめ

| 状況 | 推奨 |
|------|------|
| Python継続・現行コード流用 | **PuLP（現行）+ HiGHSソルバー**（低リスク・即効性） |
| Python継続・大規模化・複雑化対応 | **Google OR-Tools CP-SAT**（最高性能・拡張性） |
| Java環境への移行が可能 | **Timefold Solver**（シフト専用機能最充実） |

> **結論**: 日勤のみのクリニックシフトには、現行のPuLPを維持しつつHiGHSソルバーへ切り替えるか、
> 将来の拡張を見越してGoogle OR-Tools CP-SATへ移行するかが現実的な選択肢である。
> Java環境があればTimefold Solverが最も洗練されたシフト管理機能を提供する。

---

## 参考リンク

- [Google OR-Tools 公式](https://developers.google.com/optimization)
- [OR-Tools ナーススケジュール例](https://developers.google.com/optimization/scheduling/employee_scheduling)
- [Timefold Solver](https://github.com/TimefoldAI/timefold-solver)
- [Timefold Employee Shift Schedulingドキュメント](https://docs.timefold.ai/employee-shift-scheduling/latest/)
- [PuLP GitHub](https://github.com/coin-or/pulp)
- [HiGHS](https://highs.dev/)
- [Pyomo](https://github.com/Pyomo/pyomo)
- [CVXPY](https://github.com/cvxpy/cvxpy)
- [choco-solver](https://choco-solver.org/)
- [SCIP / PySCIPOpt](https://github.com/scipopt/PySCIPOpt)
- [python-constraint](https://github.com/python-constraint/python-constraint)
- [OR-Tools vs Timefold 比較](https://timefold.ai/alternatives/google-or-tools-versus-timefold-comparison)
