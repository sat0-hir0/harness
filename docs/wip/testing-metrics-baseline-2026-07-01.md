# Harness テスト手法 / ベースライン指標 / skill 数上限の実測検証 (= WIP、 一時記録)

**Status**: WIP、 ADR 未起票
**Date**: 2026-07-01
**Scope**: 業界 eval / observability / benchmark 調査結果 + skill 数上限の実測検証 + 私たちの harness のベースライン指標設計
**Disclaimer**: AI と user の対話による一時メモ。 確定実装ではない。 前提知識の修正 (= 「10 個 cap」 の再定義) を含む。
**Related**: [compression-discussion-2026-07-01.md](./compression-discussion-2026-07-01.md) / [compression-strategies-b-to-g-2026-07-01.md](./compression-strategies-b-to-g-2026-07-01.md)

---

## 背景

戦略 A-G (= 大規模改修) 議論の途中で以下 3 点が浮上:

1. **ベースライン計測がない**: 前回 token 推定を **3.7 倍間違えた** (= 14,000 → 実測 52,356)。 判断根拠が定量化されていない。
2. **振る舞い regression の検知手段がない**: 「圧縮しても振る舞い変わらない」 の主張を verify する術なし。
3. **「10 個 cap」 の根拠が不明**: 私が memory に書いた 「10 個」 の出典が Claude 発話のみ、 業界実測との照合なし。

= 「大きめ修正の前にベースライン守れているかを常時 verify する仕組み」 が必要 (= user 発話)。

---

## Part 1: 業界の eval / test / observability 調査

### 業界の 3 分類

| 分類 | 目的 | 私たちの目的への一致度 |
|---|---|---|
| **A. Eval harness** (= behavior test) | 「振る舞い変わってない?」 を case ベースで verify | **完全一致** |
| **B. Observability** (= runtime 監視) | 本番稼働中の agent の性能 / cost / drift を trace | 中 (= 個人 harness では過剰) |
| **C. Benchmark** (= public leaderboard) | model 間比較 (= HELM / MMLU 等) | 低 |

user の 「振る舞い変わっていないか」 = **A. Eval harness** が直接該当。

### 主要 OSS Eval framework (= A 分類)

| tool | star | license | 特徴 | 私たちへの適用 |
|---|---|---|---|---|
| **DeepEval** | 15.7k | Apache 2.0 | pytest-native、 agentic eval harness 内蔵 | ○ 段階 3 で採用検討 |
| **Inspect AI** | 2.1k | MIT (UK AISI) | 200+ 事前構築 eval、 gold standard | △ overkill |
| **OpenAI Evals** | 18.5k | MIT | registry-based benchmark | △ benchmark 系 |
| **Promptfoo** | (2026-03 OpenAI 買収) | MIT | security / red-team focus | △ vendor 懸念 |
| **Phoenix (Arize)** | - | Apache 2.0 | v16.0.0 で sandboxed Code Evaluators + LLM-jury server-side | △ |
| **Langfuse** | - | Apache 2.0 | self-hostable、 framework 中立 | ○ dashboard 候補 |
| **Evalite** | - | MIT | TypeScript 軽量、 「Evaluate your LLM-powered apps」 | △ TS 混在 |

### Claude Code / skill 特化の実装事例

#### 事例 A: [Nemade Sumit の 「LLM judge なしで skill test」](https://medium.com/@nemadesumit/how-to-test-any-claude-code-skill-without-an-llm-judge-3da402de7146) (= 最も参考)

**思想**: 「Test the artifacts, not the prose」 = skill 説明ではなく、 skill が生成した artifact (= commit / file / tool sequence) を test。

**4 レベル評価**:
| Level | 何を test | data 源 |
|---|---|---|
| 1 | trigger 精度 (= 正しい skill 発火) | event log |
| 2 | 実行順序 (= tool call sequence) | event log |
| 3 | 出力 artifact 検証 | filesystem / git |
| 4 | 振る舞い invariant | event log + filesystem |

**scoring band**: ≥80% STRONG / 50-79% PARTIAL / 25-49% WEAK / <25% NONE

**基盤 (= 3 要素)**:
1. `~/.claude-events/` ディレクトリ
2. `.claude/hooks/pre-tool.sh` (= tool call を JSON log)
3. `.claude/settings.json` に hook 登録

**eval file 構造**: `.claude/skills/skill-eval/evals/<skill-name>.md`
- trigger 発火 / 非発火 patterns
- trace invariants (= 実行順)
- artifact contracts (= 出力要件)
- failure-to-fix mapping

**CLI**:
```bash
/skill-eval ci-pipeline               # full run
/skill-eval ci-pipeline --level 3     # artifacts のみ
/skill-eval ci-pipeline --baseline    # golden state 記録
/skill-eval ci-pipeline --regression  # baseline 比較
```

#### 事例 B: [MLflow による Claude Code skill eval](https://mlflow.org/blog/evaluating-skills-mlflow)

- 3-step loop: **trace 実行** → **judge trace** → **skill 自動 refine**
- 2 種類 judge: LLM judge (= 振る舞い pattern) + rule-based judge (= 具体 artifact)
- YAML config で target project / skills / setup / judge module 指定
- Claude Code 自身が SKILL.md を自動 refine する事例あり

#### 事例 C: [Anthropic 「Framework for Evaluating Agentic Skills at Scale」](https://arxiv.org/html/2606.17819v1)

- **5-stage pipeline**: Skills 分析 → environment engineering → task 生成 → task validation → eval 実行
- **2 rubric** (= 各 100 点): task-completion / instruction-following
- **skill delta (Δ)**: skill 有無での性能差
- **規模**: ~500 実世界 skill → ~1,000 task → ~38,000 trajectory
- **Opus 4.8 の instruction-following = 88.0**

### Anthropic 公式指針 (= [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents))

**5 段階 lifecycle**: Definition → Implementation → Execution → Analysis → Iteration

**推奨 metrics**:
- **Primary**: pass@k / pass^k / 試行成功率 / consistency
- **Secondary**: Latency / Token usage / Cost / Turn count / Error rate

**LLM-as-Judge 2 大 best practice**:
1. **Escape hatch**: 「Unknown」 逃げ道必須 = hallucination 防止
2. **Dimension isolation**: 各 dimension を **別々の LLM-as-judge** で採点

**rubric 設計**: 「2 人の domain expert が独立に同じ pass/fail 判定」 保証

**test case 設計**:
- 開始規模: **20-50 simple task**、 real failures から抽出
- coverage balance: 発火 / 非発火 両方
- reference solution: 「全 grader を pass する 既知の working output」

---

## Part 2: 追跡すべき指標 (= 業界基準統合)

### hard 指標 (= 定量、 決定的)

| 指標 | 業界名 | 私たちの現状 |
|---|---|---|
| Total tokens (per session / task) | Token usage & cost per task | 2026-07-01 実測 |
| Latency (end-to-end + tool call) | Response latency | 未計測 |
| Cost per task (LLM + tool) | Cost per task | 未計測 |
| Tool call count | Turn count / tool-call 頻度 | 未計測 |
| Skill 数 | (= harness 固有) | 6 個 |
| Agent 数 | (= harness 固有) | 6 個 |
| Error rate | Error rate | 未計測 |

### soft 指標 (= 質的、 LLM judge)

| 指標 | 業界名 | 意味 |
|---|---|---|
| Task completion rate | Task Completion Rate | request 通り完了したか |
| Accuracy (surface / semantic) | Accuracy | 表面 / 意味の正解率 |
| Hallucination rate | Hallucination Rate | 嘘率 |
| Tool correctness | Tool Correctness | 正しい tool 呼び出し |
| Argument correctness | Argument Correctness | tool 引数正当性 |
| Step efficiency | Step Efficiency | 不要 step の少なさ |
| Plan quality | Plan Quality Score | 計画妥当性 |
| Plan adherence | Plan Adherence | 計画通り実行 |
| Reasoning coherence | Reasoning Coherence | 論理的一貫性 |

### trend 指標 (= 時系列変動、 dashboard 向け)

| 指標 | 業界名 | 意味 |
|---|---|---|
| Behavioral drift | Drift indicator | 過去との振る舞いのずれ |
| Skill delta (Δ) | Skill delta | skill 有無での性能差 |
| pass@k / pass^k | Anthropic 公式 | k 試行成功率 |
| Token trend | Token usage over time | 消費 trend |
| Regression rate | Behavior regression rate | 劣化 case 数 |

### 業界データ ・ 3 つの重要事実

1. **benchmark と production の乖離 = 37%** (= lab と real-world で 37 pp gap)
2. **harness 自体が結果を変える = 10-20 point** (= 同じ model weights でも harness 違えば score 変動)
3. **Latency / cost は soft ではなく hard metric** (= 「30 秒での正解 = product failure」)

---

## Part 3: 「skill / agent 10 個 cap」 の実測検証結果 (= 重要修正)

### 結論

**「10 個 cap」 は Anthropic の公式定義ではなく、 私の memory が不正確だった**。 実測データは 3 種類の異なる限界を示す:

### 限界 1: 技術的 hard limit (= budget が exhaust)

- [ClaudeFast の実測](https://claudefa.st/blog/guide/mechanics/skill-listing-budget): **default 設定で ~42 skills** (= 16,000 char budget / 平均 263 char/skill)
- [alexey-pelykh gist の実測](https://gist.github.com/alexey-pelykh/faa3c304f731d6a962efc5fa2a43abe1): 「Showing 42 of 63 skills」 を system prompt で発見、 実測 42/63 = 33% hidden
- 内部 setting: `skillListingBudgetFraction` (default 0.01) と `skillListingMaxDescChars` (1536) が v2.1.129 で追加、 公式 changelog に **未掲載**
- context 別:
  - 200K Sonnet default (= 1%): **~2,000 tokens = 15-25 skills**
  - 200K Sonnet default (= 16,000 char 実測): **~42 skills**
  - 1M context (= 1%): **~10,000 tokens = 75-125 skills**

### 限界 2: 精度低下境界 (= description match precision)

- [stork.ai](https://www.stork.ai/blog/claude-code-is-secretly-disabling-you): **20-50 skills で performance degrade**
- 一般則: **project 単位で 5-8 tools が typical**、 hard 上限ではない
- [ScaleMCP 論文](https://arxiv.org/pdf/2505.06416): 100 tools 規模で tool selection 精度悪化

### 限界 3: Anthropic 推奨とされる 8-12 (= 出典疑わしい)

- ClaudeFast blog 引用: 「Anthropic's own playbook draws the line at **8-12 skills** before the cost shows up」
- 詳細 fetch で判明: **「the document does not cite an official Anthropic recommendation for 8-12 skills. ClaudeFast's own Code Kit implements 20 production skills as a practical example, not an Anthropic mandate.」**
- = **Anthropic 公式の 「8-12」 は出典確認できず**、 ClaudeFast の独自解釈の可能性

### SkillsBench 論文の重大な実測 (= 別次元)

[SkillsBench (arxiv 2602.12670)](https://arxiv.org/html/2602.12670v1) 実測:

- **84 task / 11 domain / 7,308 trajectory** の大規模実験
- **curated skill 平均 +16.2pp 向上** (= no skill 比)
- **domain 別変動**: Software Engineering +4.5pp、 Healthcare +51.9pp
- **skill 数 sweet spot**:
  - **2-3 skills 使用時: +18.6pp**
  - **4+ skills 使用時: +5.9pp** (= 効果が 1/3 以下に落ちる)
- **self-generated skill は -1.3pp** (= 自動生成 skill は逆効果、 curated 人手 skill が必須)
- **Claude Code は skill 活用能力が高い** (= +13.9pp to +23.3pp)、 Codex CLI は skill を無視することが多い
- **Claude Haiku + skill (27.7%) は Haiku 単独 (11%) を超え、 Opus 単独に近づく** = skill は model capacity gap を部分的に補償

### 「10 個 cap」 の再定義

| 限界の種類 | 数値 | 出典 | 私たちの 6 skills との関係 |
|---|---|---|---|
| 技術的 hard limit (200K default) | ~42 skills | claudefa.st / alexey-pelykh 実測 | 全然余裕 |
| 技術的 hard limit (1M default) | 75-125 skills | claudefa.st 計算 | 全然余裕 |
| 精度低下境界 | 20-50 skills | stork.ai / 一般則 | まだ緩やか |
| Anthropic 推奨? (未確認) | 8-12 skills | ClaudeFast 引用 (= 公式出典なし) | 範囲内 |
| **SkillsBench sweet spot (= 1 task で使う数)** | **2-3 skills** | arxiv 2602.12670 | **既に超過** |

= 「10 個」 は 3 種類の限界のどれかを示す近似値、 それぞれの数値・意味が違う。

### 私たちの harness の description 実測

description 長さ (= frontmatter):

| skill | description 長さ | 業界推奨 (= 130 char) 比 |
|---|---:|---:|
| task-routing | **1,388 chars** | 10.7 倍 |
| intent-clarify | **916 chars** | 7.0 倍 |
| finish-task | **775 chars** | 6.0 倍 |
| task-slicing | **763 chars** | 5.9 倍 |
| wave-status | **544 chars** | 4.2 倍 |
| commit-message | 168 chars | 1.3 倍 |
| **合計** | **4,554 chars** | budget 16,000 の 28% |

**重要**:
- 6 skills しかないが description 合計で **hard limit budget の 28% 消費**
- task-routing 単独で **1,388 chars = 業界推奨 130 char の 10.7 倍**
- Sonnet 200K default (= 2,000 token ≈ 8,000 char) 換算で **57% 消費 = 危険水域**

= skill 数の話ではなく、 **description が過剰に長い** ことが真の制約。

### SkillsBench sweet spot との照合

私たちの harness で 1 task が使う skill 数:

| task 例 | 使用 skill |
|---|---|
| 「typo 直して」 (= Lead-direct) | task-routing のみ (= 1) |
| 「commit message 作って」 | commit-message (= 1) |
| 「Wave 完了報告」 | wave-status → finish-task (= 2) |
| 「実装して、 backlog Issue で」 | task-routing → task-slicing → wave-status → finish-task (= 4) |
| 「相談したい」 | intent-clarify → task-routing → task-slicing → wave-status → finish-task (= 5) |

= **平均 3-4 skills、 大 task で 5 skills**。 SkillsBench の sweet spot **2-3 を超過**。 「4+ で benefit +5.9pp に落ちる」 の該当ゾーン。

---

## Part 4: ベースライン指標の設計 (= 統合案)

### 私たちの harness に固有 (= 業界にない) の meta metric

| 指標 | 意味 | 現状 | 目標 |
|---|---|---|---|
| **Skill 数** | description-match 精度 / cognitive load | 6 個 | hard limit 42 まで OK、 sweet spot 2-3、 現状は妥協点 |
| **Agent 数** | (同上) | 6 個 | 具体的 upper bound は業界データなし、 現状維持 |
| **Skill description 合計 char** | skill listing budget 消費率 | **4,554 chars** | 業界推奨 780 chars (= 130×6) |
| **Skill description 個別 char** | 個別 skill の description 質 | 168-1,388 chars | 業界推奨 130 chars/skill |
| **Skill body token (per skill)** | 業界 2,000 token 上限比 | 4,123-13,616 tokens | 業界推奨 2,000 tokens/skill |
| **Skill body token (合計)** | 全 skill load 時の負荷 | 52,356 tokens | 業界推奨 12,000 tokens (= 2,000×6) |
| **Skill 起動頻度** | dead skill 検出 | 未計測 | log で trend 追跡 |
| **Skill 間重複率** | fresh context の帰結、 削減可能部分 | 未計測 (= grep 可) | 定期監査 |
| **description-match precision/recall** | 「〜したい」 で正しい skill 発火 | 未計測 | 段階 2 test で計測 |
| **1 task で使用する skill 数** | SkillsBench sweet spot 監視 | 平均 3-4、 最大 5 | 業界推奨 2-3 |

### Anthropic 公式指針の secondary metrics も追加

- Latency (= end-to-end + tool call)
- Cost per task
- Turn count
- Tool-call 頻度
- Error rate

### 3 種類の限界を明示的に管理

| 限界 | 監視値 | 現状 | alert 閾値 |
|---|---|---|---|
| hard limit | skill 数 (default 42) | 6 | 30 で warning |
| description budget | 合計 char (= 16,000) | 4,554 (28%) | 50% で warning |
| SkillsBench sweet spot | 1 task 使用数 (= 2-3) | 平均 3-4 | 5+ で warning |

---

## Part 5: 実装段階 (= 業界事例 A 移植ベース)

### 段階 1: baseline metrics 収集 (= 今すぐ着手可、 cost 低)

**目的**: 戦略 A-G 判断の定量根拠獲得

**実装**:
1. **token 計測 script**: 今日の scratchpad の `count_tokens.py` を harness/scripts/ に配置
2. **description 実測 script**: frontmatter description の char / token 計測
3. **skill 起動頻度 log**: dotconfig の hook で SessionStart / skill invocation を log
4. **skill 間重複 grep 自動化**: 「4 skill 横断で同一 pattern」 を script 化 (= 「投稿フロー」 等)
5. **1 task 使用 skill 数の集計**: session log から 「同 session で load された skill」 を集計

**追加 cost**: 1-2 時間
**配置**: harness/scripts/ + dotconfig/dot_local/share/scripts/

### 段階 2: snapshot test (= Layer 1、 戦略 A 前に整備)

**目的**: 振る舞い regression 検知

**実装** (= 事例 A 移植):

構造:
```
~/code/harness/eval/
  ├─ cases/
  │   ├─ task-routing.yaml    # 各 skill 5-10 case
  │   ├─ task-slicing.yaml
  │   ├─ wave-status.yaml
  │   ├─ finish-task.yaml
  │   ├─ intent-clarify.yaml
  │   └─ commit-message.yaml
  ├─ baseline/
  │   └─ <case-id>.snapshot.yaml
  ├─ scripts/
  │   ├─ eval-run.py           # case を順に実行、 出力保存
  │   ├─ eval-baseline.py      # 現状を baseline として記録
  │   └─ eval-regression.py    # baseline vs 最新 diff
  └─ README.md
```

case format (= 事例 A 準拠):
```yaml
- id: 1
  input: "README L42 の typo を直して"
  expected_trigger: task-routing
  expected_output:
    verdict: Lead-direct
    qualitative_gate:
      public_behaviour_changed: no
      harness_verifiable: yes
      design_judgement_needed: no
    scope_estimate: XS
  expected_no_trigger: [task-slicing, wave-status]
```

case 集: 6 skill × 5-10 case = 30-60 case。 既存 SKILL.md の Worked example から抽出可能 = 追加創作低い。

**追加 cost**: 半日 - 1 日 (= case 集めと runner script 実装)
**配置**: harness/eval/

### 段階 3: LLM judge (= Layer 2、 戦略 A-G 後、 optional)

**目的**: semantic regression 検知 (= 段階 2 で拾えない質的劣化)

**実装候補**: DeepEval (= pytest 互換、 agentic eval harness 内蔵)

**追加 cost**: 数日
**判断**: 段階 1-2 の運用結果次第で導入 or 見送り

### 段階 4: dashboard (= 継続 observability、 段階 1-2 の accumulate 後)

**目的**: trend 可視化 / drift 監視

**候補**:
- 個人 harness では **CLI table 出力で十分の可能性**
- Langfuse (= self-hostable、 framework 中立、 OpenTelemetry 準拠) が最有力
- Braintrust / LangSmith は commercial、 過剰

**追加 cost**: 数日〜週単位
**判断**: 段階 1-2 の data 蓄積後

---

## Part 6: 3 layer 検証手法 (= Anthropic 公式 + 事例 A 統合)

### Layer 1: 決定的 test (= LLM 不要)

- **snapshot test**: 出力 YAML / verdict を保存、 diff で regression 即検知
- **rule-based judge**: file 存在 / regex / exit code 検証
- **trace test**: tool call 順序 (= event log)
- 特徴: **LLM cost ゼロ、 高速、 false-positive 低い**

### Layer 2: LLM-as-judge (= 質的判定)

- 事例 A の Level 4、 MLflow 事例、 Anthropic 公式指針
- 「pass / fail / Unknown」 で dimension isolation
- rubric per dimension
- 特徴: **cost 高い、 但し judgement 系 case で不可避**

### Layer 3: Human calibration (= 定期的)

- LLM judge の calibration 用に定期 human review
- 「LLM の pass 判定」 と 「human の pass 判定」 の一致率追跡
- 特徴: **cost 最高、 但し LLM judge の信頼性維持に必須**

事例 A / Anthropic 公式が共通に推奨: **Layer 1 主体、 Layer 2 は最小限、 Layer 3 は定期 calibration**。

---

## Part 7: 私たちの harness 診断 (= 業界基準統合)

### 業界基準と現状 (= 実測ベース)

| 観点 | 業界基準 | 私たちの現状 | 診断 |
|---|---|---|---|
| **description length (個別)** | 130-263 chars 推奨 | 168-1,388 chars | task-routing は 5-10 倍過剰 |
| **description 総 char** | 16,000 budget、 130×6=780 char 目安 | 4,554 chars | 5.8 倍過剰、 budget 28% |
| **skill count** | hard 42、 推奨 8-12、 sweet 2-3 | 6 skills | 数は OK |
| **skill body token (個別)** | 2,000 tokens/skill | 4,123-13,616 tokens | 2-6.8 倍過剰 |
| **skill body token (合計)** | 12,000 tokens 目安 | 52,356 tokens | 4.4 倍過剰 |
| **1 task 使用 skill 数** | sweet 2-3 | 平均 3-4、 最大 5 | sweet 超過 |

### 圧縮の優先順位 (= 実測ベース更新)

前回議論の 「戦略 A-G」 は **body token 圧縮の話が中心**。 今回検証で **別次元の圧縮軸** が浮上:

1. **description の圧縮** (= 業界推奨 130 char に近づける) = **新規追加軸**、 前回議論では抜けていた
2. **body token 圧縮** (= 戦略 A-G) = 議論済
3. **1 task 使用 skill 数の削減** (= sweet spot 2-3 に近づける) = **新規追加軸**、 skill 統合の再検討要
4. **skill count 削減** = 現状 6 で OK、 触る必要なし

= **前回の戦略 A-G は body token 圧縮に focus していたが、 description 圧縮 + 1 task 使用数削減 の 2 軸が漏れていた**。

---

## Part 8: 次のアクション

### 即着手可 (= cost 低)

1. **memory の 「10 個 cap」 修正** (= 実測ベース 3 種類の限界に分解)
2. **段階 1 (= baseline metrics 収集) 実装** (= 1-2 時間)
   - token / description 計測 script を harness/scripts/ に追加
   - skill 起動頻度 log (= dotconfig hook)
   - skill 間重複 grep 自動化
3. **description 圧縮の pilot** (= task-routing 1,388 → 300 char 目標で試行、 振る舞い変わらないか確認)

### 戦略 A-G 議論の再開時に反映

1. 戦略 A-G の削減目標に **description 圧縮軸** を追加
2. 戦略 A-G の削減目標に **1 task 使用 skill 数の削減軸** を追加 (= 例えば task-slicing と wave-status の統合検討)
3. 戦略 A の shared state で **skill 起動頻度追跡** を実装

### 中長期 (= 段階 2-4)

1. 段階 2 (= snapshot test) を戦略 A 実装前に整備
2. 段階 3 (= LLM judge) は段階 2 運用結果次第
3. 段階 4 (= dashboard) は段階 1-2 の data 蓄積後

---

## Sources (= 参照ソース)

### Anthropic 公式 / 準公式

- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — 5 段階 lifecycle、 pass@k / pass^k、 LLM-as-judge の 2 大 best practice
- [Anthropic: Framework for Evaluating Agentic Skills at Scale (arxiv 2606.17819)](https://arxiv.org/html/2606.17819v1) — 500 skill / 1000 task の内部 framework 論文
- [Claude Code Docs - Extend Claude with skills](https://code.claude.com/docs/en/skills) — 公式仕様

### skill 数上限の技術根拠

- [Claude Code's Hidden Skill Budget Setting - claudefa.st](https://claudefa.st/blog/guide/mechanics/skill-listing-budget) — 16,000 char budget、 42 skills 実測、 `skillListingBudgetFraction` (= v2.1.129)
- [claude-code-skill-budget-research gist by alexey-pelykh](https://gist.github.com/alexey-pelykh/faa3c304f731d6a962efc5fa2a43abe1) — 42 of 63 skills visible の実測、 description length と収容数の関係
- [SkillsBench (arxiv 2602.12670)](https://arxiv.org/html/2602.12670v1) — 84 task / 7,308 trajectory、 2-3 sweet spot / 4+ で benefit 急落
- [Why Claude Code Disables Skills - stork.ai](https://www.stork.ai/blog/claude-code-is-secretly-disabling-you) — 20-50 skills で degrade
- [Claude Code Skills Common Mistakes - MindStudio](https://www.mindstudio.ai/blog/claude-code-skills-common-mistakes-guide) — description 設計 mistakes
- [ScaleMCP - arxiv 2505.06416](https://arxiv.org/pdf/2505.06416) — 100 tools 規模での tool selection 精度
- [Learning to Rewrite Tool Descriptions - arxiv 2602.20426](https://arxiv.org/pdf/2602.20426) — tool description 長さと精度の関係

### Claude Code / skill test 実装事例

- [How to Test Any Claude Code Skill (Without an LLM Judge) - Nemade Sumit](https://medium.com/@nemadesumit/how-to-test-any-claude-code-skill-without-an-llm-judge-3da402de7146) — 事例 A、 4 レベル評価 + `--baseline/--regression` 実装、 hook 経由 event log
- [Testing and Refining Claude Code Skills with MLflow - mlflow.org](https://mlflow.org/blog/evaluating-skills-mlflow) — MLflow で trace ベース judge + Claude Code 自動 refine

### OSS eval framework

- [DeepEval (github)](https://github.com/confident-ai/deepeval) — pytest 互換 agentic eval harness、 Apache 2.0
- [Inspect AI (github)](https://github.com/UKGovernmentBEIS/inspect_ai) — UK AISI 内製、 200+ 事前構築 eval、 MIT
- [Awesome AI Evaluations Tools (github)](https://github.com/danielrosehill/Awesome-AI-Evaluations-Tools) — OSS フレームワーク list

### 業界比較 / 買い手ガイド

- [AI Agent Eval Frameworks 2026 - Digital Applied](https://www.digitalapplied.com/blog/ai-agent-eval-frameworks-testing-guide-2026) — 2026 業界 OSS 比較
- [LLM Agent Evaluation Metrics 2026 - Confident AI](https://www.confident-ai.com/blog/llm-agent-evaluation-complete-guide) — Tool calling / task completion / trace-based metrics 定義
- [Top AI Agent Evaluation & Observability Harnesses 2026 - MCPlato](https://mcplato.com/en/blog/top-ai-agent-evaluation-observability-harnesses-2026/) — top 10 tool 比較
- [AI Agent Observability Guide - groundcover](https://www.groundcover.com/learn/observability/ai-agent-observability) — observability 全体像
- [AI observability tools buyer's guide 2026 - Braintrust](https://www.braintrust.dev/articles/best-ai-observability-tools-2026) — production 監視 tool 一覧

### subagent 関連

- [Claude Code Subagents Guide 2026 - Nimbalyst](https://nimbalyst.com/blog/claude-code-subagents-guide/) — 7x token 倍率、 200-500% overhead

---

## 注記

このドキュメントは ADR ではなく **議論の WIP 記録**。 前提知識 (= 「10 個 cap」) の再定義を含む。 memory の該当箇所は次回の議論再開時に修正すること。

数値は cl100k_base 概算 (= ASCII chars/4 + 日本語 chars×1.5)、 tiktoken 正確計測ではない。 char 数は生 char count。
