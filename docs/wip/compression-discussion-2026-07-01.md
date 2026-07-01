# Harness 圧縮 / 最適化議論 (= WIP、 一時記録)

**Status**: WIP、 ADR 未起票 (= harness に ADR 体系がまだない)
**Date**: 2026-07-01
**Scope**: harness skill 6 個 / 1,948 行の圧縮 + アーキテクチャ最適化議論の途中記録
**Disclaimer**: AI と user の対話による一時メモ。 確定実装ではない。

---

## 議論の経緯

### 起点

backlog にダッシュボード追加 issue / スクリプト化検討 issue を作りたい、 ただし harness 自身の開発体験が薄い問題があるので相談したい、 という user 発話から始まった議論。

### 確定したこと

- dashboard はメタ harness ではなく ow / limn 等の別 project 側で扱う
- メタ harness の真の課題は **skill 肥大化と 10 個 cap 制約下での機能 / 品質維持**

---

## 現状診断

### 現状の数字 (= 2026-07-01 実測、 cl100k_base 概算)

**skill 6 個 / 1,954 行 / 約 52,356 token** (= 全 skill 起動時に load される総量):

| skill | 行数 | ~tokens | 業界上限 (= 2,000) 比 |
|---|---:|---:|---|
| task-slicing | 497 | 13,616 | **+581%** |
| finish-task | 434 | 12,074 | **+504%** |
| task-routing | 322 | 10,730 | **+436%** |
| intent-clarify | 224 | 6,269 | +213% |
| wave-status | 219 | 5,544 | +177% |
| commit-message | 258 | 4,123 | +106% |

**agent 6 個 / 321 行 / 約 10,606 token** (= 各 1,514-2,283 token、 業界 role-based budget 範囲内):

| agent | 行数 | ~tokens |
|---|---:|---:|
| architect | 44 | 1,810 |
| fullstack-engineer | 67 | 2,283 |
| performance-engineer | 55 | 1,731 |
| qa-expert | 45 | 1,514 |
| security-auditor | 55 | 1,687 |
| technical-writer | 55 | 1,581 |

**docs 2 個 / 515 行 / 約 15,215 token**:
- docs/harness-design.md: 383 行 / ~12,252 token
- docs/script-placement.md: 132 行 / ~2,963 token

**scripts 1 個 / 323 行 / 約 3,370 token** (= check-future-plans.py)

**総計: 3,113 行 / 約 81,547 token**

上限制約: skill 数 10 個前後 (= description match 精度 / cognitive load)

### 業界知見との照合

| 観点 | 業界の現在地 | 私たちの現状 |
|---|---|---|
| skill 1 個の上限 | 2,000 token (= 約 1,500 語) | **全 skill 超過、 最大 task-slicing 13,616 token = +581%** |
| role-based budget | research 2-4k / coding 4-8k token | 役割別 budget なし (= ただし agent は各 1.5-2.3k で範囲内) |
| multi-agent token 倍率 | 3 agent 並列 = 7x token | budget 制御なし |
| subagent overhead | single-agent 比 200-500% | overhead 制御なし |
| shared structured state | 2-4x 高速化、 業界 de facto standard | 半分実装 (= YAML chat 出力のみ、 永続なし) |
| context rot 4 症状 | 指示無視 / generic 化 / 長 session 劣化 / 片方向累積 | 症状 4 該当 (= 半年累積、 削除なし) |

### token 推定の注記

- 数値は **cl100k_base 概算** (= ASCII chars/4 + 日本語 chars×1.5)、 tiktoken での正確計測ではない
- 実 tiktoken 値は ±10% 程度の誤差の可能性
- 前回本 doc 初版に記載した 「約 14,000 token」 は英語基準の粗い近似で誤り、 2026-07-01 に実測値で修正済

### 既存重複の根本原因

skill 4 件 (= task-routing / task-slicing / wave-status / finish-task) に 「投稿フロー 1-5」 「題材 Issue 同定」 「無人 Lead 独断禁止」 等が重複している件は **fresh context per iteration 原則の帰結** (= 各 skill が単独完結する必要があるため defensive に全部書く)。 doc 化や 1 skill 集約は原則違反。

---

## 議論済の最適化戦略

### 当初検討した 4 戦略 (= 旧)

| 戦略 | 内容 | 判定 |
|---|---|---|
| A. docs/ に抽出 + skill から参照リンク | 設計背景 / why / decision table を docs 化 | 後に却下 (= AI が doc 読みに行く分相殺、 効果薄い) |
| B. 共通 skill 切り出し | 共通 phase を mini skill 化 | 不採用 (= 10 個 cap 違反) |
| C. skill 責務再分割 | 6 skill の責務境界引き直し | 保留 (= 大改造) |
| D. skill 内冗長表現を圧縮 | 「説明過多」 → 「指示文」 化 | 採用検討 |

### 業界調査後に追加した 7 戦略 (= 新)

| 戦略 | 削減 | 配置 | 4 軸 | 難度 | ADR |
|---|---|---|---|---|---|
| A. Shared Structured State | 300 行 | harness 共通 | common standard | 高 | 最重要 |
| B. Role-Specific Budget | 50-80 行 | agent.md | common standard | 中 | 中 |
| C. Visibility Boundary | 70-100 行 | shared state schema | common standard | 中 | 中 |
| D. Condensed Summary Protocol | 50-100 行 | agent output schema | common standard | 中 | 中 |
| E. SkillOpt 導入 | 300-400 行 | tooling | personal exp → common | 低 | 軽 |
| F. JIT injection (hook) | 200 行 | hook + state | common standard | 中 | 中 |
| G. JIT retrieval (tool/script) | 150 行 | script | common standard | 低 | 軽 |

合計削減ポテンシャル: 1,100-1,400 行 (= 1,948 から 55-70%)、 ただし戦略 A が他 6 戦略の前提。

---

## 戦略 A の詳細設計 (= 議論で深掘りされたもの)

### 思想の核

既存 harness の YAML output 思想 + Fresh Eye (= State on disk, not in context / Fresh context per iteration) 原則の完成版。 既存 YAML を schema として保存し、 場所を chat → Issue コメント / local file の永続層に移す。

### state backend の決定

| 条件 | backend |
|---|---|
| Issue 番号あり | **Issue コメント** (= GitHub が SSOT) |
| Issue 番号なし (= chat-direct) | **local file** (= `~/.claude/state/local-<sid>.yaml`) |
| R/W 共通 | **必ず script 経由** (= AI は直接 gh / file 操作しない) |

### script 構成

```
~/code/harness/scripts/state/
  ├─ read-state.py        # 最新 state を取得 (= Issue or local 自動切替)
  ├─ write-decision.py    # decision を 1 件追加
  ├─ write-plan.py        # slice-plan / verdict 等の大 entry を追加
  ├─ write-progress.py    # wave 進捗 mark + Layer 1.5 検査統合
  ├─ verify-wave.py       # Tier 1 機械検証
  └─ _backend/
      ├─ issue.py         # gh issue 経由の R/W
      ├─ local.py         # ~/.claude/state/local-<sid>.yaml 経由の R/W
      └─ schema.py        # yaml-state block の validation / migration
```

### Issue コメント schema (= yaml-state fenced block)

markdown 表記 (= 人間用) + YAML block (= AI 用) の二重表記:

```markdown
📋 着手 Plan (slice)

(= 人間が読む markdown)

` ` `yaml-state
schema_version: 1
session_id: <session 識別子>
backend: issue | local
created_at: <ISO8601>

task_framing:
  invoked_from: backlog-issue | chat-direct | cron-heartbeat
  issue_number: <int | null>
  issue_repo: <string | null>
  execution_mode: ultra-autonomous | step-by-step | autonomous
  autonomy_level: human-present | unattended
  branch: <git branch>

decisions:                # append-only history
  - timestamp: ...
    session_id: ...
    agent: ...
    type: verdict | slice-plan | wave-mark | ...
    judgement_steps: {...}
    conclusion: {...}

prior_outputs:            # agent ごとに最新 1 件
  <agent_name>:
    summary: <500 token 以内>
    artifacts: [...]

formatting_rules:
  pr_language: ja | en
  commit_style: en-conventional

references:               # source of truth への path
  wave_status_file: <path | null>
  adr_dir: <path>
` ` `
```

### Fresh Eye 整合

| 観点 | 整合 |
|---|---|
| State on disk, not in context | GitHub Issue / local file が disk |
| Fresh context per iteration | 毎 skill 起動で read-state.py で fetch |
| append-only history | コメントは編集前提でない |
| 過去 state は履歴扱い | 各 entry の timestamp + session_id で区別 |

---

## Forced reasoning (= anti-rationalization 思想)

### 既存 harness で実装済

- task-routing qualitative_gate (= 3 質問 → verdict 機械的導出)
- finish-task spec_coverage (= status + evidence 同時要求)
- Y-trace 1 行 (= 結論 + 棄却 + trade-off)
- check-future-plans.py (= 機械 grep)
- agent_confidence + uncertainty_notes (= 不確実性開示強制)

### 観察された失敗パターン

AI に結論 field だけ持たせると 「やりたい方の結論」 を入れる。 「True にしないと進めないところを False にして後から言い訳する」 を防ぐため、 思考過程を step として強制構造化する。

### 戦略 A schema に統合

```yaml
decisions:
  - timestamp: ...
    agent: task-routing
    type: verdict
    judgement_steps:                    # 強制 field
      step_1_public_behaviour:
        answer: yes | no
        evidence: "<file:line | grep result>"
        confidence: high | medium | low
      step_2_harness_verifiable: {...}
      step_3_design_judgement: {...}
      step_4_file_count: {...}
    conclusion:
      verdict: Lead-direct | delegate-single | delegate-slice
    derived_correctly: yes              # script auto-validate
    rewrite_attempts: <int>             # 言い訳検出
    dissenting_views: [...]             # 不同意 (= 該当時)
    requires_user_check: yes | no       # confidence: low で auto-set
```

write-decision.py が:
1. judgement_steps と conclusion の機械的整合を検証
2. 既存 decision の上書きを拒否 (= reversal entry のみ許可)
3. confidence: low で自動 user surface flag

---

## 検査階層 (= 嘘 / 漏れの fail-fast)

### 確定した layer 構造

```
[Layer 0] AI が judgement_steps を埋める (= forced reasoning)
   ↓
[Layer 1] script schema validation (= 全 write 時、 blocking)
   - schema 充足 / judgement_steps と conclusion の整合 / 既存 state 矛盾
   ↓
[Layer 1.5a] Tier 1 = wave 完了時 同 session script (= 新規、 blocking)
   - 機械検証のみ:
     * git push 済み確認
     * UAT command 実 run + exit code
     * file 実在 / line 一致
     * Phase 4 grep (= check-future-plans 拡張)
   - exit 非ゼロ → wave done 拒否
   ↓
[Layer 1.5b] Tier 2a = completion-auditor subagent (= 新規)
   - 完了承認 + プロセス健全性 + リスク判断
   - 既存 review 群とは責務分離
   ↓
[Layer 2] $prepare-uat Step 1-3 (= 既存)
   ↓
[Layer 3] completion-check-routine cron (= 既存、 task 全体、 不変)
   - 4 証跡を task 単位で再 check + dry-run 安全装置
   ↓
[Layer 4] 人間 UAT (= 既存、 最終 gate)
```

### Tier 1 (= 同 session script) の選択理由

「外部 supervisor 原則 (= Maker-Checker)」 への抵触を最小化するため、 機械検証 (= AI judgement なし) のみ同 session script で blocking。 これは bias なしと判断。

### Tier 2 別 session semantic 検証は保留

実装コスト / token cost / catch 率 / false positive 率が判断できない、 既存 Layer 3 で十分かも未確定なので **将来余地として記載、 現時点未採用**。

### hook 連携 (= belt-and-suspenders)

- skill 文面で `verify-wave.py` 呼び出しを明示 = AI が事前把握
- PostToolUse hook で asyncRewake 経由の機械強制を併用 = AI が呼び忘れても自動発火
- hook 配置は dotconfig (= 個人マシン)、 設定例は harness/docs/ に置く
- **`claude -p` は使わない** (= session context 喪失リスク回避)

---

## completion-auditor agent (= 新規 subagent)

### 役割

**完了承認 + プロセス健全性 + リスク判断**

これ以上の詳細化は user の中でも分解されていないため、 実運用しながら確定する。

### 既存 review 群との分離

| 役割 | 何をする | 何をしない |
|---|---|---|
| reviewer / qa-expert / security-auditor / architect / technical-writer | 質評価 / 改善提案 / 脆弱性発見 | reconciliation (= 主張と実体の照合) |
| completion-auditor | 完了承認 / プロセス健全性 / リスク判断 / 主張と実体の乖離検出 | 個別技術判断 / 設計品質 / test 質判定 / security 脅威分析 |

review sign が schema にあれば中身は信頼。 ただし sign 欠落 / 飛ばしは検出対象。

### 設計の核

| 観点 | 設計 |
|---|---|
| 既存 cron との関係 | `completion-check-routine` の wave 単位版 |
| 起動方式 | Agent tool で同 session に subagent spawn |
| 監査内容 | 既存 Layer 3 cron の 4 証跡 + EM 視点の 「プロセス遵守 / リスク反映 / 引き継ぎ」 |
| 能動性 | passive judgement ではなく、 必要なら踏み込んで実体確認 / 詳細要求 / 差し戻し |
| tool | Read / Bash (= 読み取り系のみ) / Grep / Glob (= 書き込み系禁止) |
| verdict | pass / bounce / escalate (+ 「request-clarification」 検討中) |
| downstream_impact | 後続 wave / task への影響を判定、 再 slice / task 差し戻し triggers 可 |
| dry-run 安全装置 | 既存 cron 思想を継承、 初期 default は dry-run、 信頼化後 flip |
| cycle 制限 | max 3 (= 無限ループ防止) |
| 再監査 | auditor_session_id 重複禁止 (= cycle ごとに新 subagent) |
| 自己監査禁止 | main session と同 session_id なら schema validation で reject |

### 監査の判定領域 (= 暫定 6 領域)

1. phase gate 通過
2. プロセス遵守 (= review sign の完備性)
3. claim 実体整合 (= 主張と実体の乖離検出)
4. 引き継ぎ整合 (= prior_outputs と次 wave 前提の dependency)
5. リスク統治 (= 事前リスクの対処状況)
6. 後続影響評価 (= downstream impact、 task-slicing 再 slice / task 差し戻し triggers)

### schema の核 field

```yaml
prior_outputs:
  fullstack-engineer:
    wave_id: 1
    ...
    review_history:           # 既存 review 工程の sign 記録
      - role: reviewer
        sign: ...
      - role: qa-expert
        sign: ...
    completion_audit:         # 新規
      auditor: completion-auditor
      auditor_session_id: subagent-abc123
      audited_at: ...
      dry_run: no
      cycle_count: 1
      em_explanation:
        can_explain: yes | no  # 「自分が user に説明できる」 を強制宣言
        explanation_summary: ...
        open_questions: []
      evidence_checks:        # Layer 3 cron 流用 + EM 視点
        wave_checkbox: pass | fail
        commit_present: ...
        push_status: ...
        scope_alignment: ...
        uat_passage: ...
        review_sign_presence: ...
        risk_handling: ...
        downstream_implications: ...
      verdict: pass | bounce | escalate
      downstream_impact:
        severity: none | minor | major
        affected_waves: [3, 4]
        affected_tasks: []
        action_needed: [...]
        recommendation: continue | replan-downstream | bounce-task
      bounce_reasons: []
      escalate_reasons: []
      fix_hints: []
      sign: completion-auditor-subagent-abc123
```

---

## 削減効果 (= 戦略 A 単独で見たもの)

| 項目 | 削減 (行) | 削減 (~tokens) |
|---|---:|---:|
| Issue 投稿フロー 4 skill 重複 (= write-*.py に集約) | 約 245 行 | 約 6,500 token |
| Tier 1 検査 logic の script 化 (= wave-status / finish-task) | 約 30-50 行 | 約 900 token |
| completion-auditor 強制で wave-status の verbose 手続き説明削減 | 約 20-30 行 | 約 700 token |
| Worked example の docs/examples/ 外出し | 約 70 行 | 約 1,900 token |
| 戦略 A 全体合計 | **約 365 行** | **約 10,000 token** |

行数比: 1,954 → 1,589 行 = **19% 削減**
token 比: 52,356 → 42,356 token = **19% 削減**

**注記**: 日本語 skill では 「1 行 ≈ 27 token」 (= 平均)、 日本語重複部分 (= 投稿フロー等) は 1 行 40-50 token になるため、 重複削減の効果は token ベースでより大きい可能性あり (= 上記は保守的見立て)。

ここに戦略 B-G が乗ると 40-50% 圧縮見込み (= 21,000-26,000 token 削減)。

---

## やらないこと / 棄却したこと

### 完全撤回された案

| 案 | 棄却理由 |
|---|---|
| ローカル state file 案 (= 戦略 A v1) | Issue コメントで持つべき (= 既存 harness 思想と整合) |
| `claude -p` で hook から agent spawn | session context 喪失リスク |
| 監査役の動的選択 / additional_auditors | completion-auditor は単一固定で十分 (= YAML 完了品の精査だから役割固定 OK) |
| 監査役 = reviewer / qa-expert 等 既存 review agent 流用 | review (= 質評価) と監査 (= 完了承認 + プロセス + リスク) は別物 |
| 50% 圧縮目標 (= 当初想定) | fresh context per iteration 原則を破らないと不能、 現実的には 15-20% (= 戦略 D 単独) / 40-50% (= 戦略 A-G 統合) |

### 保留 (= 将来判断)

- Tier 2 別 session cron 監査 (= wave 単位の semantic 検証、 cost / 効果不明)
- 戦略 B-G (= 戦略 A 確定後に順次議論)

### 触らない判定

- task-slicing / finish-task / task-routing の肥大自体は問題ではない (= 「肥大 = 悪」 と短絡しない)
- agent markdown 均一 (= 43-66 行) は意図的
- skillshare drift (= Windows) は既知問題

---

## 次のアクション

1. **戦略 A の段階導入 Phase 詳細** = Phase 1-10 を Issue level に展開 (= 実装に着手するなら)
2. **戦略 B-G の説明** = 戦略 A 確定後に 1 つずつ深掘り (= 未着手)
3. **既存 skill の before/after 例** = 戦略 A 後の具体像 (= 未着手)
4. **検査階層の図解** = SVG で 5 layer 可視化 (= 未着手)

---

## 参考 path

- harness repo: `~/code/harness/`
- 設計思想: `docs/harness-design.md`
- skill 配置原則: `docs/script-placement.md`
- 既存 skills: `skills/{task-routing, task-slicing, wave-status, finish-task, intent-clarify, commit-message}/SKILL.md`
- 既存 agents: `agents/{architect, fullstack-engineer, reviewer, qa-expert, security-auditor, technical-writer, performance-engineer}.md`
- ai-memory (= 個人 user-model): `~/code/ai-memory/user-model/collaboration-preferences.md`
- backlog repo: `sat0-hir0/backlog`

---

## 業界調査の出典

戦略立案時に参照した主要 source:

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — JIT loading / Progressive disclosure
- [Cognition Devin Playbook 2026 - Digital Applied](https://www.digitalapplied.com/blog/context-engineering-agent-reliability-playbook-2026) — role-based token budget / condensed summary
- [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt) — skill 半自動最適化 OSS、 +19.1 point 改善実証
- [Multi-Agent Context Sharing Patterns - Fastio](https://fast.io/resources/multi-agent-context-sharing-patterns/) — shared workspace、 2-4x 高速化
- [Building Multi-Agent Systems Part 3 - sshh blog](https://blog.sshh.io/p/building-multi-agent-systems-part-c0c) — context indirection / progressive disclosure
- [Multi-Agent Systems with Context Engineering - Vellum](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering) — shared memory schema 4 element
- [Context Rot in Claude Code Skills - MindStudio](https://www.mindstudio.ai/blog/context-rot-claude-code-skills-bloated-files) — 2,000 token 上限 / 4 症状
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) — UserPromptSubmit / SessionStart で additionalContext inject
- [Issue #64898: hook が agent spawn 不可](https://github.com/anthropics/claude-code/issues/64898) — claude -p workaround の制約
- [Managing AI agent skills at scale - Rajiv Pant](https://rajiv.com/blog/2026/03/23/managing-ai-agent-skills-at-scale-three-repo-architecture/) — three-repo architecture

---

## 注記

このドキュメントは ADR ではなく **議論の WIP 記録**。 確定実装ではない。 ADR 体系を harness に導入してから正式な ADR として書き起こすか、 issue 起票して進める。
