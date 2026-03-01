# シフトスケジューリング 学術・技術参考資料集

> **調査日**: 2026-02-28（cmd_238更新版）
> **タスクID**: subtask_238e_academic_references（cmd_237旧版を差し替え）
> **対象**: 日勤のみクリニック向けシフトスケジューリングシステム
>
> **🔴 重要前提**: 対象クリニックは「**日勤のみ**」（夜勤・2交代・3交代なし）。
> 夜勤特化論文も参考として収録するが、各資料に **「日勤適用可能性」★〜★★★★★で評価** している。

---

## 1. 重要論文一覧

### 1.1 ナーススケジューリング問題（NSP）代表的論文

| # | タイトル | 著者 | 年 | 日勤適用可能性 | URL |
|---|----------|------|----|----------------|-----|
| 1 | Staff scheduling and rostering: A review of applications, methods and models | Ernst, Jiang, Krishnamoorthy, Sier | 2004 | ★★★★☆ | https://www.sciencedirect.com/science/article/abs/pii/S0377221709003968 |
| 2 | The state of the art of nurse rostering | Burke, De Causmaecker, Vanden Berghe, Van Landeghem | 2004 | ★★★★☆ | https://link.springer.com/article/10.1007/s10732-008-9099-6 |
| 3 | A Survey of the Nurse Rostering Solution Methodologies: The State-of-the-Art and Emerging Trends | 複数著者 | 2022 | ★★★★☆ | https://www.researchgate.net/publication/360821639 |
| 4 | Machine Learning and Constraint Programming for Efficient Healthcare Scheduling | 複数著者 | 2024 | ★★★☆☆ | https://arxiv.org/pdf/2409.07547 |
| 5 | Integrating Nurse Preferences Into AI-Based Scheduling Systems | 複数著者 | 2025 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC12157959/ |
| 6 | Optimizing Nurse Rostering: A Case Study Using Integer Programming | 複数著者 | 2024 | ★★★★☆ | https://pmc.ncbi.nlm.nih.gov/articles/PMC11675476/ |
| 7 | Solving Nurse Scheduling Problem Using Constraint Programming Technique | 複数著者 | 2019 | ★★★★☆ | https://arxiv.org/abs/1902.01193 |
| 8 | A multi-objective approach to nurse scheduling with both hard and soft constraints | Azaiez, Al Sharif | 1996 | ★★★★☆ | https://www.sciencedirect.com/science/article/abs/pii/0038012196000109 |
| 9 | Nurse scheduling using integer linear programming and constraint programming | 複数著者 | 2014 | ★★★★☆ | https://www.researchgate.net/publication/269267836 |
| 10 | A Constraint Satisfaction Problem (CSP) Approach for the Nurse Scheduling Problem | Shobaki, Jaradat | 2023 | ★★★★☆ | https://ieeexplore.ieee.org/document/10022250 |

#### 各論文の日勤適用可能性 詳細評価

**[1] Staff scheduling and rostering (Ernst et al. 2004)** — ★★★★☆（高）
スタッフスケジューリング全般の基礎サーベイ。NSP手法・モデルを包括的に整理。夜勤制約を除外すれば、制約定義・目的関数設計の枠組みはそのまま日勤シフトに適用可能。

**[2] The state of the art of nurse rostering (Burke et al. 2004)** — ★★★★☆（高）
メタヒューリスティクスを含む解法を体系的に整理した定番サーベイ。GA・TS・SAなどアルゴリズム選択の参考として、夜勤/日勤問わず活用できる。

**[3] Survey of NSP Solution Methodologies (2022)** — ★★★★☆（高）
ML・AIとの融合を含む最新トレンドを網羅。日勤への適用では夜勤インターバル制約を除去するだけで手法はそのまま使える。

**[4] ML and CP for Healthcare Scheduling (2024)** — ★★★☆☆（中）
強化学習＋シミュレーテッドアニーリングで82%の解品質改善を実証。ML部分は夜勤ダイナミクスに依存するが、CP部分の設計パターンは日勤に適用可能。

**[5] Integrating Nurse Preferences Into AI-Based Scheduling (2025)** — ★★★★★（最高）
AI・NLP・RLを組み合わせた希望統合手法。「希望をAIが吸い上げる」フレームワークは夜勤不在の日勤クリニックにそのまま適用できる。将来拡張に最も有益。

**[6] Optimizing Nurse Rostering with Integer Programming (2024)** — ★★★★☆（高）
Branch & Bound・Branch & Cutで最適・近似最適解を探索。実例研究なので制約モデリングの参考として優れる。夜勤分の変数・制約を削除するだけでシンプルに適用可能。

**[7] Solving NSP Using Constraint Programming (2019)** — ★★★★☆（高）
CPでNSPを解く手法の詳細。ハード制約（1日1シフト、最大連続勤務日数）とソフト制約（希望、公平性）のモデリングを詳説。日勤シフト種別への置き換えが容易。

**[8] A multi-objective approach to NSP (Azaiez & Al Sharif 1996)** — ★★★★☆（高）
ハード・ソフト制約双方を扱う多目的アプローチの先駆的論文。日勤・夜勤問わず使える制約分類フレームワークを提供。

**[9] Nurse scheduling using ILP and CP (2014)** — ★★★★☆（高）
ILPとCPを比較した実用的な研究。スタッフ規模ごとに有利な手法が異なるという知見（小規模→IP、大規模→メタヒューリスティクス）は日勤クリニックに直接参考になる。

**[10] CSP Approach for NSP (2023)** — ★★★★☆（高）
IEEE発表の最新CSP実装例。制約充足問題としてのモデリングパターンを参照可能。

---

### 1.2 外来クリニック・日勤特化研究

| # | タイトル | 年 | 日勤適用可能性 | URL |
|---|----------|----|----------------|-----|
| 11 | Healthcare Scheduling in Optimization Context: A Review | 2021 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC8035616/ |
| 12 | Development of a New Personalized Staff-Scheduling Method with a Work-Life Balance Perspective | 2023 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC9972317/ |
| 13 | A Heuristic Algorithm for Medical Staff Scheduling with Multi-skills and Vacation Control | 2023 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC10454947/ |
| 14 | A Scheduling Optimization Approach to Reduce Outpatient Waiting Times | 2025 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC11988311/ |
| 15 | Resource Allocation and Outpatient Appointment Scheduling Using Simulation Optimization | 2017 | ★★★★★ | https://pmc.ncbi.nlm.nih.gov/articles/PMC5635465/ |

**[11] Healthcare Scheduling in Optimization Context: A Review (PMC 2021)** — ★★★★★（最高）
外来クリニック含む医療スケジューリングの包括的レビュー。日勤シフト文脈での制約・目標の整理に直接役立つ。最も重要な参考資料の一つ。

**[12] Personalized Staff-Scheduling with Work-Life Balance (PMC 2023)** — ★★★★★（最高）
個人希望×ワークライフバランスの設計思想が日勤クリニックと完全一致。夜勤なし環境でのパーソナライズドスケジューリングに直接適用可能。

**[13] Medical Staff Scheduling with Multi-skills (PMC 2023)** — ★★★★★（最高）
マルチスキル・休暇制御を含む医療スタッフスケジューリング。「スキル × シフト」の組み合わせ制約モデリングが外来クリニックに直接応用可能。

**[14] Outpatient Waiting Times Optimization (PMC 2025)** — ★★★★★（最高）
外来クリニック向けの最新研究。スタッフスケジュールと患者待ち時間の連動最適化。

**[15] Resource Allocation and Outpatient Appointment Scheduling (PMC 2017)** — ★★★★★（最高）
外来クリニックの患者予約・スタッフ配置の多目的最適化。シミュレーション最適化手法。

---

### 1.3 公平性・多目的最適化研究

| # | タイトル | 年 | 日勤適用可能性 | URL |
|---|----------|----|----------------|-----|
| 16 | Fairness and Decision-making in Collaborative Shift Scheduling Systems (CHI 2020) | 2020 | ★★★★★ | https://dl.acm.org/doi/fullHtml/10.1145/3313831.3376656 |
| 17 | Pareto-Optimal Workforce Scheduling with Worker Skills and Preferences | 2025 | ★★★★★ | https://link.springer.com/article/10.1007/s12351-025-00903-7 |
| 18 | A Review of Multi-Objective Optimization Methods for Personnel Rostering | 2025 | ★★★★☆ | https://link.springer.com/article/10.1007/s10951-025-00845-0 |
| 19 | Towards Fairness-Aware Multi-Objective Optimization | 2024 | ★★★★☆ | https://link.springer.com/article/10.1007/s40747-024-01668-w |

**[16] Fairness and Decision-making in Collaborative Shift Scheduling (CHI 2020)** — ★★★★★（最高）
4次元の公平性フレームワーク（分配的・手続き的・情報的・対人的）を定義。参加型スケジューリングのUI/UX設計にも活用可能。日勤クリニックに完全適用可能。

**[17] Pareto-Optimal Workforce Scheduling with Skills and Preferences (2025)** — ★★★★★（最高）
スキル制約と希望充足の多目的最適化。過剰配置・不足配置のPareto frontierで管理者が選択できる設計。日勤クリニックの「誰がどの業務を担当できるか」モデリングに直接応用可能。

---

## 2. ベンチマーク問題（INRC）

### INRC-I（第1回国際ナーススケジューリングコンペティション）
- **開催**: PATAT-2010スポンサー
- **形式**: 週単位の静的問題。複数病棟、複数シフトタイプ
- **特徴**: 最も広く使われているベンチマークデータセット
- **参照**: https://www.schedulingbenchmarks.org/
- **日勤適用可能性**: ★★★☆☆（中）夜勤シフトのベンチマークだが、制約の多様性・評価方法の参考になる

### INRC-II（第2回国際ナーススケジューリングコンペティション）
- **形式**: 動的ローリングホライズン型。複数週にわたる計画
- **特徴**: 週をまたぐ制約（連続勤務日数等）の扱いが複雑
- **日勤適用可能性**: ★★★★☆（高）ローリングホライズン手法は日勤シフト管理にも有効

---

## 3. 制約定義のベストプラクティス

### 3.1 ハード制約 vs ソフト制約の分類

| 制約種別 | 定義 | 日勤クリニック例 |
|---------|------|-----------------|
| **ハード制約** | 違反した場合に解が無効となる絶対制約 | 1日1シフトまで、最低出勤人数確保、労働基準法遵守 |
| **ソフト制約** | 違反時にペナルティコストが発生する希望制約 | 連続勤務日数の希望、休暇希望、担当業務の希望 |

### 3.2 ハード制約の典型パターン（日勤適用）

```
HC-001: 各スタッフは1日最大1シフト
HC-002: 各日・各時間帯に必要最低人数を確保（受付・診察・処置等の業務別）
HC-003: 週労働時間の上限（労働基準法：40時間/週）
HC-004: 特定業務にはスキル保有者のみ割り当て可（例：採血は看護師のみ）
HC-005: 法定休日・有給の保証
HC-006: 連続勤務日数の上限（例：5日以内）
HC-007: 最低連続休日数（例：週2日の休み保証）
```

### 3.3 ソフト制約の典型パターン（日勤クリニック）

```
SC-001: スタッフの出勤希望日・休暇希望日の充足（重み: HIGH）
SC-002: 連続勤務日数の希望（例：3日以上連続は避けたい）（重み: MEDIUM）
SC-003: 特定業務担当の希望（重み: MEDIUM）
SC-004: 週単位での勤務時間公平分散（重み: HIGH）
SC-005: 月曜・繁忙日の公平割り当て（重み: LOW）
SC-006: 昼休憩のローテーション公平性（重み: MEDIUM）
SC-007: 長期的な希望充足率の均等化（重み: HIGH）
```

### 3.4 目的関数の設計パターン

```
minimize: F(schedule) = Σ(ペナルティ × ソフト制約違反数) + λ × G(過不足コスト)

- F: スタッフ不満度の線形関数
- G: クリニック運営コスト（業務カバー不足）の関数
- λ: 重み付けパラメータ（管理者が調整可能に設計する）
- ハード制約違反には巨大ペナルティを付与（実質的に排除）
```

### 3.5 重み付けの考え方

- **アバーションインデックス方式**（Miller et al. 1976）: 過去の不公平扱いの累積に基づくペナルティ重み付け
- **スタッフパワースコア**: 過去の希望充足率が低いスタッフに次回の優先権を付与
- **推奨アプローチ**: 重みをパラメータ化し、クリニック管理者が調整可能にする

### 3.6 局所探索の改善手法

| 手法 | 特徴 | 適用規模 |
|------|------|---------|
| タブー探索 (Tabu Search) | 局所最適を脱出。訪問済み解をタブーリストで管理 | 中〜大 |
| 焼きなまし法 (Simulated Annealing) | 確率的に悪化を許容しながら大域最適に収束 | 中〜大 |
| 遺伝的アルゴリズム (Genetic Algorithm) | 解の集団を進化演算子で改善。多様性維持に優れる | 中〜大 |
| 大近傍探索 (LNS) | 解の大部分を再生成することで大域的改善 | 大 |
| CP-SAT（制約プログラミング） | 厳密解に近い解を高速に探索 | 小〜中 |

---

## 4. 解の評価指標

### 4.1 公平性（Fairness）の測定方法

| 評価軸 | 指標 | 計算方法 |
|-------|------|---------|
| 勤務時間の分散 | 標準偏差 | std(h_i) を最小化 |
| 希望充足の公平性 | 個人別充足率の均一性 | max(\|r_i - r̄\|) を最小化 |
| 繁忙シフトの公平分配 | 人気のないシフトの割り当て分散 | 特定シフト担当回数の平準化 |
| 長期的公平性 | 複数期間での累積充足率 | 直近N期間の充足率移動平均 |

```python
# 公平性スコアの計算例
import numpy as np

hours_per_staff = [40, 38, 42, 39, 41]  # 各スタッフの週労働時間
fairness_score = 1 - (np.std(hours_per_staff) / np.mean(hours_per_staff))
# 1.0に近いほど公平。目標: 0.95以上
```

### 4.2 希望充足率の計算

```python
# 個人別希望充足率
fulfillment_rate_personal = sum(satisfied_requests[i]) / sum(total_requests[i])

# 全体希望充足率
fulfillment_rate_overall = total_satisfied / total_requested * 100
# 例: 30リクエスト中25件充足 → 83.3%

# 長期公平性（移動平均）
rolling_avg = pd.Series(weekly_rates).rolling(window=4).mean()
```

### 4.3 多目的最適化のアプローチ

| 手法 | 説明 | 推奨シーン |
|------|------|-----------|
| 加重和法 | Σ(w_i × 目的関数_i) を最大化 | 重みの直感的設定が可能 |
| Pareto最適解法 | 全目的で非劣解（パレート解）の集合を列挙。管理者が選択 | 多数の目的を同時考慮 |
| ε-制約法 | 一つの目的を最適化しつつ、他の目的に下限制約を設ける | 希望充足率に最低保証を設ける |

**推奨（日勤クリニック向け）**: 加重和法 + 希望充足率の下限εを設定（例: 各スタッフ最低70%充足保証）

### 4.4 計算時間 vs 解品質のトレードオフ

| 手法 | 解品質 | 計算時間 | 適用規模 |
|------|--------|----------|---------|
| 整数計画法（厳密解） | 最良（最適解保証） | 長（数時間〜） | 小〜中（〜50人） |
| 制約プログラミング（CP-SAT） | 良（準最適） | 中（数分〜） | 中（〜100人） |
| メタヒューリスティクス | 実用的 | 短（数秒〜分） | 大（100人〜） |
| ハイブリッド（ML+最適化） | 良〜最良 | 短〜中 | 中〜大 |

---

## 5. GitHub参考実装

| # | リポジトリ | 言語・技術 | スター | URL |
|---|-----------|---------|--------|-----|
| 1 | **google/or-tools** (employee_scheduling) | Python, CP-SAT | 公式 | https://developers.google.com/optimization/scheduling/employee_scheduling |
| 2 | **or-tools shift_scheduling_sat.py** | Python | 公式 | https://github.com/google/or-tools/blob/stable/examples/python/shift_scheduling_sat.py |
| 3 | **weiran-aitech/shift_schedule** | Python, CP | - | https://github.com/weiran-aitech/shift_schedule |
| 4 | **ordenador/genetic-shift-scheduler** | Python, GA + Flask | - | https://github.com/ordenador/genetic-shift-scheduler |
| 5 | **lbiedma/shift-scheduling** | Python, PuLP+MIP | - | https://github.com/lbiedma/shift-scheduling |
| 6 | **dwave-examples/employee-scheduling** | Python, 量子ハイブリッド | D-Wave公式 | https://github.com/dwave-examples/employee-scheduling |
| 7 | **staffjoy** | Go/Python | - | https://github.com/staffjoy |
| 8 | **OptaPlanner (nurse-rostering)** | Java, OptaPlanner | 公式 | https://www.optaplanner.org/ |
| 9 | **unsharot/kinmu_rs** | Rust | ⭐6 | https://github.com/unsharot/kinmu_rs |
| 10 | **j3soon/nurse-scheduling** | Python, Web | ⭐5 | https://github.com/j3soon/nurse-scheduling |

---

## 6. 日本語技術資料

### 6.1 Qiita記事

| タイトル | URL |
|----------|-----|
| シフトスケジューリング問題を解いてみた | https://qiita.com/SaitoTsutomu/items/4278871ab4ce2be17752 |
| 組合せ最適化でナーススケジューリング問題を解く | https://qiita.com/SaitoTsutomu/items/a33aba1a95828eb6bd3f |
| シフト・スケジューリング問題をいろいろな手法で解いてみた | https://qiita.com/tail-island/items/c786d8b1bc5ccf3b5d53 |
| Python＋PuLPを使ってシフト表を自動作成 | https://qiita.com/ookamikujira/items/862ec78914d5deb549c1 |
| Pulp 組み合わせ最適化でシフト表作成 可能な限り2連休を作る | https://qiita.com/ookamikujira/items/eccf65cfe89176b8c468 |

### 6.2 Zenn記事

| タイトル | URL |
|----------|-----|
| 整数計画ソルバーでシフトスケジューリング問題を解いてみた | https://zenn.dev/umepon/articles/5aef89c5c348de |
| 制約最適化モデリングでシフトスケジューリング最適化 | https://zenn.dev/fusic/articles/06b524105ec899 |

### 6.3 企業技術ブログ

| タイトル | URL |
|----------|-----|
| 数理最適化によって訪問介護のシフトスケジューリングモデルを作ってみた話 | https://tech.bm-sms.co.jp/entry/2023/03/28/120000 |
| 最適化勉強会 ～数理最適化を使用してシフトスケジューリング問題を解く～ | https://www.nri-digital.jp/tech/20240919-18835/ |
| シフト最適化への応用が期待される強化学習を用いた組合せ最適化の解法 | https://www.chowagiken.co.jp/blog/combinatorial_optimization |
| シフトスケジューリング問題 (opt100) | https://scmopt.github.io/opt100/81shift-minimization.html |

---

## 7. 主要ライブラリ・ツール

| ツール | 言語 | 特徴 | URL |
|--------|------|------|-----|
| **OR-Tools (CP-SAT)** | Python, C++, Java | Googleが開発。制約プログラミング・線形最適化を統合 | https://developers.google.com/optimization |
| **PuLP** | Python | 線形計画・整数計画のモデリング言語。CBC/Gurobiに接続 | https://coin-or.github.io/pulp/ |
| **OptaPlanner / Timefold** | Java/Python | エンタープライズ向けソルバー。NSPのサンプルデモ内蔵 | https://www.optaplanner.org/ |
| **Gurobi** | Python, Java, C++ | 商用最適化ソルバー。大規模問題に高性能。学術利用は無償 | https://www.gurobi.com/ |

---

## 8. 日勤シフトに特化した知見

### 8.1 外来クリニック固有の課題

外来クリニックの日勤シフト管理には以下の特性がある：

1. **時間帯別需要変動**: 受付・診察は午前中ピーク、午後閑散の傾向
2. **スキルの多様性**: 医師・看護師・受付・検査技師等の異なるスキル要件
3. **予約連動型スタッフ需要**: 患者予約数に基づく動的スタッフ配置
4. **非夜勤のシンプルさ**: 夜勤手当・夜勤疲労・夜勤インターバルの考慮不要
5. **昼休憩管理**: 全員が同時間帯に存在するため、ローテーション管理が必要

### 8.2 日勤特化のモデル簡略化（NSPとの比較）

```
除去可能な夜勤制約:
  ✖ 夜勤→日勤間の最低インターバル（通常11時間）
  ✖ 夜勤手当計算
  ✖ 夜勤専従スタッフの処遇
  ✖ 夜勤明けの翌日休暇

追加が必要な日勤特有制約:
  ✅ 昼食休憩のカバー（誰かが常に受付をカバー）
  ✅ 午前・午後の需要差に基づく時間帯別人数制約
  ✅ 当日キャンセル・急な欠員への対応（フレキシブル要員）
  ✅ クリニックの開院・閉院時間に合わせた勤務時間設定
```

### 8.3 A Review within Canadian Healthcare Centres（MDPI 2022）からの知見

外来クリニックのスタッフスケジューリングにおける公平性確保のポイント：

- **事前申請ウィンドウ**: スタッフが最低X日前に希望申請（推奨: 2〜4週前）
- **ローリングホライゾン**: 1〜2ヶ月先まで計画し、週次で更新
- **透明性**: スコアリング根拠をスタッフに開示

---

## 9. 調査サマリー

| 項目 | 件数 | 完了状況 |
|------|------|---------|
| 学術論文・調査報告 | 19件 | ✅ |
| 日勤適用可能性評価 | 全19件 | ✅ |
| GitHub実装参考 | 10件 | ✅ |
| OR-Tools公式サンプル | 2件 | ✅ |
| Qiita記事 | 5件 | ✅ |
| Zenn記事 | 2件 | ✅ |
| 企業技術ブログ | 4件 | ✅ |

**重要知見**:
1. **NSPはNP困難**: 実用規模では厳密解法より近似・ヒューリスティクスが主流
2. **ハード/ソフト制約の分離が設計の核心**: 違反コストをペナルティ関数に組み込む手法が標準
3. **最新トレンド（2020-2025）**: ML（強化学習・深層学習）と従来最適化手法のハイブリッドが主流に
4. **公平性指標**: 勤務時間の標準偏差・ワークロードバランスのジニ係数が定量評価に多用
5. **日本語コミュニティ**: PuLP + OR-Toolsの実装記事が豊富

---

## 🏆 実装時に最も参考になる資料 TOP10（日勤観点で選定）

**選定基準**: 実装直結度・日勤適用可能性・情報密度・最新性の総合評価

| 順位 | 資料名 | URL | 選定理由 |
|-----|--------|-----|---------|
| **1** | Google OR-Tools: Employee Scheduling (公式) | https://developers.google.com/optimization/scheduling/employee_scheduling | CP-SATソルバーの実装起点。最も実践的なチュートリアル。日勤シフト変数への置き換えが容易 |
| **2** | shift_scheduling_sat.py (OR-Tools GitHub) | https://github.com/google/or-tools/blob/stable/examples/python/shift_scheduling_sat.py | 本番レベルのPython実装。制約モデリングのベストプラクティスが凝縮 |
| **3** | Pareto-Optimal Workforce Scheduling (Springer 2025) | https://link.springer.com/article/10.1007/s12351-025-00903-7 | スキル×希望の多目的最適化。日勤クリニックの業務割り当てに直接適用可能な最新論文 |
| **4** | Healthcare Scheduling in Optimization Context: A Review (PMC 2021) | https://pmc.ncbi.nlm.nih.gov/articles/PMC8035616/ | 外来クリニック含む医療スケジューリングの包括的レビュー。設計全体像の把握に最適 |
| **5** | Fairness and Decision-making in Collaborative Shift Scheduling (CHI 2020) | https://dl.acm.org/doi/fullHtml/10.1145/3313831.3376656 | 公平性の4次元フレームワーク。UI/UX設計にも活用可能。日勤クリニックに完全適用可能 |
| **6** | 整数計画ソルバーでシフトスケジューリング問題を解いてみた (Zenn) | https://zenn.dev/umepon/articles/5aef89c5c348de | 日本語で読める最も実践的な実装記事。PuLPで即実行可。制約モデリングを日本語で解説 |
| **7** | Personalized Staff-Scheduling with Work-Life Balance (PMC 2023) | https://pmc.ncbi.nlm.nih.gov/articles/PMC9972317/ | 個人希望×ワークライフバランスの研究。日勤クリニックの設計思想と完全一致 |
| **8** | Medical Staff Scheduling with Multi-skills (PMC 2023) | https://pmc.ncbi.nlm.nih.gov/articles/PMC10454947/ | マルチスキル制約の実装パターン。外来クリニックの業務別スキル管理に直接応用可能 |
| **9** | Integrating Nurse Preferences Into AI-Based Scheduling (JMIR 2025) | https://pmc.ncbi.nlm.nih.gov/articles/PMC12157959/ | AI×NLPでスタッフ希望を吸い上げる最新アプローチ。将来のAI統合拡張に有用 |
| **10** | 数理最適化によって訪問介護のシフトスケジューリングモデルを作った話 | https://tech.bm-sms.co.jp/entry/2023/03/28/120000 | 日本の医療・介護業界での実務事例。日本の法規制・文化的文脈（有給・労基）が参考になる |

---

*作成: ashigaru5 / subtask_238e_academic_references（cmd_237旧版を差し替え）*
