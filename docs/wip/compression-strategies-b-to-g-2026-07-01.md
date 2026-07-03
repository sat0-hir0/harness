# Harness 圧縮 / 最適化議論 ・ 戦略 B-G (= WIP、 一時記録)

**Status**: WIP、 ADR 未起票
**Date**: 2026-07-01
**Scope**: 戦略 A (= shared structured state) 以外の 6 戦略の設計記録
**Disclaimer**: AI と user の対話による一時メモ。 確定実装ではない。 戦略 A を前提とした派生戦略を含む。
**Related**: [compression-discussion-2026-07-01.md](./compression-discussion-2026-07-01.md) (= 戦略 A 本体 + 議論経緯)

---

## 注意

戦略 A 以外の 6 戦略は **業界調査と粗い設計まで進んでいるが、 user との詳細議論は未実施**。 戦略 A 同様の深さで詰めるべきかは未確定。 本ドキュメントは **戦略 A 確定後の議論再開時の出発点** として保存する。

各戦略は **戦略 A (= shared structured state) が前提**。 戦略 A がないと B-G は個別最適化で終わる。

---

## 戦略 B: Role-Specific Context Injection

### 思想

agent (= architect / fullstack-engineer / reviewer / qa-expert / security-auditor / technical-writer / performance-engineer / completion-auditor) ごとに **token budget と inject context を分離**。 「必要な人に必要なだけ」 を構造化する。

### 業界根拠

- [Cognition Devin Playbook 2026](https://www.digitalapplied.com/blog/context-engineering-agent-reliability-playbook-2026) — 「research agent 2-4k token / coding agent 4-8k token」 の role 別 budget
- 「Coding agent (file-heavy) は glob/grep JIT」 = role ごとに異なる context 戦略

### 私たちの現状

agent 6 個 / 315 行 = 各 50 行程度で **均一**。 役割別 budget なし、 全 agent に同じ context を渡す前提。

### 提案する budget table

| agent | budget | inject すべき context |
|---|---|---|
| architect (= read-only 設計) | 4-6k | shared state.task_framing + 該当 ADR + 関連 file path 一覧 (= 中身ではない) |
| fullstack-engineer (= 実装) | 6-8k | architect output + diff スコープ + verifier 一覧 |
| reviewer (= 敵対的 review) | 3-4k | diff + ADR 引用 + 「将来予定」 ルール抜粋 |
| qa-expert (= test 検証) | 2-3k | test command + 期待 output |
| security-auditor (= 脅威分析) | 3-4k | diff の入力境界 + 該当 security policy |
| technical-writer (= doc) | 2-3k | diff + 既存 doc 構造 |
| performance-engineer (= 性能) | 3-4k | benchmark target + 既存 baseline |
| completion-auditor (= 監査) | 4-6k | wave goal + diff + state.review_history + ADR 関連 |

### 期待効果

- 各 agent が **自分の判断に必要な context だけ受け取る** = hallucination 減 / 速度向上
- agent.md の重複説明削減 = **50-80 行**
- shared state (= 戦略 A) の visibility filter で 「他 agent の context」 が混入しない

### 実装

戦略 A の shared state schema に **role 別 inject 制御 field** を追加:

```yaml
agent_invocation_policy:
  architect:
    budget_max: 6000
    inject_fields: [task_framing, references.adr_dir, file_path_listing]
    inject_state_filter: agent==architect
  fullstack-engineer:
    budget_max: 8000
    inject_fields: [prior_outputs.architect, task_framing.branch, verifier_list]
  ...
```

agent spawn 時に shared state から **policy に該当する subset だけ抽出** して prompt に inject。

### 削減見込み

50-80 行 (= agent.md の重複説明 / 暗黙 inject の明示化)

### 議論未確定

- budget 数値の根拠 (= Cognition の 2-4k / 4-8k はベンチマーク値、 私たちの実態に合うか未検証)
- inject_fields の確定 (= 業界 best practice はあるが私たちの skill schema に合わせた再設計要)
- 「budget 超過時の挙動」 (= truncate / 別 subagent spawn / 失敗)

### 4 軸分類

common standard (= 全 agent 横断、 標準化価値あり)

### ADR レベル

中

---

## 戦略 C: Visibility Boundary の明示化

### 思想

Cognition ACP (= Agent Communication Protocol) 思想を採用、 shared state の **各 field に visibility tag** を付けて agent ごとに見える範囲を制御。 1 つの shared context を **agent ごとに違う view で提供**。

### 業界根拠

- Cognition Devin: 「visibility boundaries for sub-agents (= which slice of the shared context each one sees)」
- shared state を全 agent に open すると **token 7x 倍率** に直撃 (= [Nimbalyst](https://nimbalyst.com/blog/claude-code-subagents-guide/))

### 私たちの現状

shared state (= 戦略 A) の概念はあるが、 全 agent が同じ schema 全部を読む前提。 visibility 制御なし。

### 提案する visibility schema

shared state の各 field に `visible_to` を付与:

```yaml
decisions:
  - visible_to: [architect, reviewer, completion-auditor]
    # qa-expert / security-auditor は見ない (= test / security に無関係)
    ...

formatting_rules:
  pr_language: "ja"
  visible_to: [technical-writer, fullstack-engineer]
  # security-auditor は formatting 知る必要なし

review_history:
  visible_to: [completion-auditor]
  # 他 agent は review 履歴を知る必要なし、 知ると干渉する
```

### 動作

```python
# agent spawn 時の logic
def filter_state_for_agent(state, agent_name):
    filtered = {}
    for field, value in state.items():
        if isinstance(value, dict) and 'visible_to' in value:
            if agent_name in value['visible_to']:
                filtered[field] = value
        else:
            filtered[field] = value  # visibility tag なし = 全 agent 可視
    return filtered
```

### 期待効果

- agent ごとの context 量を **構造的に最小化** = token 7x 倍率を 3-4x に抑制
- security boundary (= 各 agent の knowledge を分離) と整合
- 「他 agent の判断を見て自分の判断を変える」 干渉を防ぐ

### 削減見込み

70-100 行 (= shared state inject の手動制御を schema で機械化)

### 議論未確定

- visibility tag の **付与責任** (= AI か script か)
- default visibility (= tag なし field の扱い)
- visibility 違反検出 (= AI が tag を無視して読みに行く対策)

### 4 軸分類

common standard (= 戦略 A の上に乗る、 同じく標準化価値)

### ADR レベル

中 (= 戦略 A の延長線上)

---

## 戦略 D: Condensed Summary Protocol

### 思想

subagent return を **prose ではなく構造化 schema** で固定。 main agent (= Lead) が **1 subagent あたり 1,000-2,000 token の condensed summary** だけ読む。

### 業界根拠

- [Cognition Devin Playbook 2026](https://www.digitalapplied.com/blog/context-engineering-agent-reliability-playbook-2026): subagent は full context ではなく **1,000-2,000 token の condensed summary** を返す
- [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents): 「tool 結果削除 (= 深い履歴の tool 呼び出し結果をクリア)」

### 私たちの現状

subagent (= architect / fullstack-engineer 等) は自由文 (= prose) で結果を返す。 main agent が再パースして context 圧迫。

### 提案する出力 schema

各 agent の出力に強制 schema:

```yaml
output_schema:
  summary: <500 token 以内>
  decisions:
    - type: <decision_type>
      value: <短い結論>
      rationale: <1-2 文の根拠>
  artifacts:
    - path: <file path>
      type: <file_type>
  unresolved:
    - item: <未解決事項>
      blocker: <ブロッカー or null>
  total_tokens_target: 1500
```

main agent は **schema 化された field だけ読む**:
- 自由文を再パースする手間なし
- 「artifact が file path だけ」 と確定 → main agent が中身を tool で fetch するか判断可
- hallucination 連鎖 (= 主観文章の解釈ズレ) を断つ

### 期待効果

- main agent の context が **subagent 1 個あたり 1,000-2,000 token に収まる**
- 7x 倍率を回避
- subagent の output を main が再解釈する余地を減らす

### 削減見込み

50-100 行 (= main agent の subagent 結果 parse logic を skill から削除可能)

### 議論未確定

- summary 500 token の **十分性** (= 複雑な architect output が 500 token に収まるか)
- schema 違反時の挙動 (= 規定外 field を返してきた場合)
- 既存 agent.md 全部に schema を強制する **migration cost**

### 4 軸分類

common standard

### ADR レベル

中

---

## 戦略 E: SkillOpt 導入

### 思想

Microsoft SkillOpt OSS を活用、 既存 skill を **半自動で圧縮 + 効果検証**。 「人手で 200 行削る」 ではなく **「benchmark task で精度落ちないことを確認しながら自動圧縮」**。

### 業界根拠

- [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt): Claude Code 上で +19.1 point accuracy 改善 (= 圧縮しても精度は **下がらない、 むしろ上がる**)
- skill document を 300-2,000 token 範囲に圧縮可
- trajectory-driven editing (= 失敗から学ぶ) + validation gate (= 精度劣化拒否)
- PyPI v0.1.0 (= 2026-06-02 release)

### 私たちの現状

skill 1 件 3,500 token (= task-slicing)、 業界上限の 75% 超過。 ただし手動圧縮は **fresh context per iteration 原則** との衝突で難しいことが判明 (= 戦略 A 議論で確定)。

### 提案

1. validation benchmark を整備:
   - 既存 skill の代表的判断 task を 10-20 件 case 化
   - SkillOpt の input/output ペアとして使う
2. SkillOpt に既存 6 skill を投入
3. **add/delete/replace edit の自動提案** を受ける
4. validation gate (= benchmark 精度劣化拒否) を経た best_skill.md artifact を review
5. 人手 review で OK なら merge

### 期待効果

- skill 1 個あたり 300-2,000 token に収まる + **精度劣化なし** が客観的に保証
- 削減見込み: **300-400 行 (= 15-20%)**
- 「fresh context 原則を破らない圧縮」 を SkillOpt の validation gate で機械保証

### 議論未確定

- **validation benchmark の整備コスト** (= 既存 skill の判断 task を case 化する手間)
- SkillOpt が **私たちの skill format** (= harness 固有の Phase 構造 / Y-trace 等) に適応するか
- 圧縮された skill が **後の手動 edit との conflict** をどう扱うか
- best_skill.md の deploy フロー (= 既存 skillshare extras との整合)

### 4 軸分類

personal experiment → 効果あれば common standard

### ADR レベル

低 (= 既存 OSS の試用、 効果あれば本格採用 ADR)

---

## 戦略 F: JIT Context Injection via Hooks

### 思想

skill / agent に直書きしている **project 固有情報** (= AGENTS.md / git-strategy.md / commit ルール / Issue template / verifier 一覧 等) を runtime に取りに行く。 `SessionStart` / `UserPromptSubmit` hook で **その turn で必要な情報だけ inject**。

### 業界根拠

- [Anthropic Hooks Docs](https://code.claude.com/docs/en/hooks): UserPromptSubmit / SessionStart は additionalContext を inject 可能
- harness-design.md §1 「2 層分離 = 内側 vendor 非依存 + 外側 project 固有」 の **完全実装** = project 固有を runtime に取りに行く

### 私たちの現状

skill 文面に project 固有説明 (= 「Limn は cargo test」 「OW は npm test」 「commit ルール」 等) が散在。 project 横断で使う前提なら 「project の AGENTS.md を読め」 と外部参照しているが、 AI が AGENTS.md を読みに行く分 context 二重 load。

### 提案 hook 構成

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "~/.claude/scripts/state/prefetch-project-context.py",
        "async": false
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "issue|backlog|チケット|起票",
        "command": "~/.claude/scripts/state/inject-issue-templates.py"
      },
      {
        "matcher": "commit|コミット",
        "command": "~/.claude/scripts/state/inject-commit-rules.py"
      }
    ]
  }
}
```

prefetch-project-context.py は:
1. project root の `AGENTS.md` / `CLAUDE.md` / `docs/development/git-strategy.md` 等を読む
2. 必要な field を抽出 (= 全文ではなく要点)
3. shared state (= 戦略 A) の `formatting_rules` / `references` に格納
4. または additionalContext として stdout 出力

skill 本体は 「inject された context を参照」 とだけ書く = **project 中立に薄く**。

### 期待効果

- skill 本体から project 固有説明を **約 200 行削減**
- fresh context per iteration とも整合 (= 毎セッション最新を取りに行く)
- 新 project の追加が skill 編集不要に (= AGENTS.md を書けば自動で hook が拾う)

### 議論未確定

- hook が 「Issue 切る」 「commit」 等を **string match で確実に拾えるか** (= 誤動作率)
- inject 量の制御 (= 過剰 inject = context 圧迫の本末転倒)
- hook 配置は dotconfig (= 個人マシン)、 他 user との **共通標準化** をどうやるか
- project 固有情報の **schema 標準化** (= 各 project AGENTS.md が同じ field を持つ保証)

### 4 軸分類

common standard (= 設計転換) + personal experiment (= hook の個別実装)

### ADR レベル

中 (= 戦略 A の上に乗る、 設計思想の方向確定が要る)

---

## 戦略 G: Just-in-Time Tool-based Retrieval

### 思想

「context indirection」 = skill に直書きしている **判定 logic / 詳細情報** を script / file に出し、 必要時に tool で fetch。 「全部 context に load」 ではなく 「ID だけ持ち、 実体は tool で取りに行く」。

### 業界根拠

- [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents): 「軽量 ID (= path / URL) を保持、 runtime で tool 経由 動的 load」
- [sshh blog Part 3](https://blog.sshh.io/p/building-multi-agent-systems-part-c0c): 「context indirection」 (= grep / awk で外部から取りに行く)
- 既存実装: `check-future-plans.py` (= grep を script に外出し、 結果だけ取得)

### 私たちの現状

`check-future-plans.py` が成功例。 ただし他にも script 化候補が多数:
- 題材 Issue 同定フロー 1-5 (= 4 skill 重複の根源、 environment 変数 + session 履歴 + repo 名 match で機械判定可)
- YAML schema validation (= finish-task Final Report)
- frontmatter schema validation (= skill / agent 配布事故防止)
- 「将来予定」 grep (= 既に check-future-plans.py で実装済)
- Y-trace format validation (= regex)
- size 判定テーブル (= ファイル数 count)

### 提案 script 群

```
~/code/harness/scripts/
  ├─ state/                  # 戦略 A で導入予定
  │   ├─ read-state.py
  │   ├─ write-*.py
  │   └─ verify-wave.py
  ├─ check-future-plans.py   # 既存
  ├─ identify-issue-target.py   # 新規、 題材 Issue 同定
  ├─ validate-finish-task-yaml.py   # 新規、 YAML schema
  ├─ validate-frontmatter.py   # 新規、 skill / agent frontmatter
  └─ validate-y-trace.py   # 新規、 Y-trace format
```

skill 本体は **「該当 script を呼ぶ」 と 5 行**。 詳細 logic は script のヘルプ message に隠蔽。

### 期待効果

- skill 本体から判定 logic を **約 150 行削減**
- fresh context per iteration 原則と完全整合 (= state on disk)
- 既存 `check-future-plans.py` の **方向の延長**

### 議論未確定

- script 数の **上限** (= 過剰 script 化で別の複雑性発生)
- script の **schema migration** (= harness 更新時の script 互換)
- AI が script 出力を **信じすぎる** リスク (= Fresh Eye 違反)

### 4 軸分類

common standard

### ADR レベル

低 (= 既存 check-future-plans.py の拡張)

---

## 戦略間の依存関係

```
[戦略 A: Shared Structured State] ← 全戦略の前提
   ├→ [戦略 B: Role-Specific Budget]
   │     - shared state の inject 制御として実装
   ├→ [戦略 C: Visibility Boundary]
   │     - shared state schema に visibility tag 追加
   ├→ [戦略 D: Condensed Summary Protocol]
   │     - agent output → shared state.prior_outputs の schema 化
   ├→ [戦略 F: JIT Context Injection via Hooks]
   │     - hook が shared state に prefetch して inject
   └→ [戦略 G: JIT Tool-based Retrieval]
         - shared state の reference field を tool で fetch

[戦略 E: SkillOpt] ← 独立、 戦略 A なしでも先行試用可
```

戦略 A 確定が **全体の出発点**、 B-G は戦略 A 確定後に順次議論。 戦略 E (= SkillOpt) のみ独立、 personal experiment として先行試用可能。

---

## 全戦略統合時の削減効果

現状ベースライン (= 2026-07-01 実測): **skill 1,954 行 / 約 52,356 token**

| 戦略 | 削減 (行) | 削減 (~tokens) |
|---|---:|---:|
| A. Shared Structured State | 300 行 | 約 8,000 token |
| B. Role-Specific Budget | 50-80 行 | 約 1,500-2,200 token |
| C. Visibility Boundary | 70-100 行 | 約 2,000-2,700 token |
| D. Condensed Summary Protocol | 50-100 行 | 約 1,500-2,700 token |
| E. SkillOpt 導入 | 300-400 行 | 約 8,000-11,000 token |
| F. JIT injection (hook) | 200 行 | 約 5,500 token |
| G. JIT retrieval (tool/script) | 150 行 | 約 4,000 token |
| **単純合計** | **1,120-1,330 行 (= 57-68%)** | **約 30,500-36,100 token (= 58-69%)** |

ただし重複削減があるため (= 例えば A と F が同じ部分を削る場合あり)、 実効削減は **40-50%** が現実的見立て:
- 実効行削減: **750-1,000 行**
- 実効 token 削減: **21,000-26,000 token**
- 統合後の目標: skill 1,000-1,200 行 / 26,000-31,000 token
- ただし依然として業界上限 (= 6 skill × 2,000 = 12,000 token) は超過見込み

**注記**: token 数値は cl100k_base 概算、 実 tiktoken で ±10% 誤差の可能性。

---

## 議論で出た指摘 / 懸念

### 「逆に複雑性を上げている可能性」 (= user 2026-07-01 発話)

戦略 A 議論完了後の user 発話。 確かに 1,948 行の skill を 1,000-1,200 行に圧縮する代わりに:
- 新規 script 群 (= 4-6 個)
- 新規 agent (= completion-auditor)
- 新規 hook 設定 (= dotconfig)
- 新規 state schema + migration

を追加することになる。 **削減した行数より複雑性が増す可能性**。

判断保留 = 一晩寝かせる、 これが戦略 B-G の議論でも当てはまる。

### 「fresh context per iteration 原則の帰結」 (= 重要)

戦略 A 議論で確定した: 各 skill が単独完結する必要があるため defensive に全部書くのは **正しい設計**。 圧縮で削れるのは 「同 skill 内同文 + 言い回し短文化 + 業界知見 / why 背景の doc 化」 に限定、 10-15% が現実上限。 ただし戦略 A (= shared state + script 経由) で **構造的に重複を根絶する道** が見えた = これが戦略 A の本質的価値。

戦略 B-G は **戦略 A が機能した前提で乗る** 派生。 戦略 A が機能しないなら B-G も機能しない。

---

## 次のアクション

1. 戦略 A を一晩寝かせて再判断
2. 戦略 A が採用に値すると判断したら、 戦略 B-G を 1 つずつ詳細議論
3. 戦略 E (= SkillOpt) のみ独立試用可、 personal experiment として先行も可
4. 戦略全部却下なら、 当面 skill 圧縮は諦めて 「現状維持 + 個別の小改善」 (= 例えば既存 check-future-plans.py 拡張、 Y-trace validator 追加等) で進める選択肢

---

## 参考 path

- 戦略 A 本体: [compression-discussion-2026-07-01.md](./compression-discussion-2026-07-01.md)
- harness repo: `~/code/harness/`
- 設計思想: `docs/harness-design.md`
- ai-memory: `~/code/ai-memory/user-model/collaboration-preferences.md`

---

## 業界調査の出典 (= 戦略 B-G に関連)

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — JIT loading / 戦略 G の根拠
- [Cognition Devin Playbook 2026](https://www.digitalapplied.com/blog/context-engineering-agent-reliability-playbook-2026) — role-based budget / condensed summary / 戦略 B + D の根拠
- [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt) — 戦略 E 本体
- [Multi-Agent Context Sharing Patterns - Fastio](https://fast.io/resources/multi-agent-context-sharing-patterns/) — visibility boundary / 戦略 C の根拠
- [Building Multi-Agent Systems Part 3 - sshh blog](https://blog.sshh.io/p/building-multi-agent-systems-part-c0c) — context indirection / 戦略 G の根拠
- [Multi-Agent Systems with Context Engineering - Vellum](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering) — shared memory schema 4 element / 戦略 B + D の根拠
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) — UserPromptSubmit / SessionStart で additionalContext inject / 戦略 F の根拠
- [Issue #64898: hook が agent spawn 不可](https://github.com/anthropics/claude-code/issues/64898) — claude -p workaround の制約 / 戦略 F の限界
- [Claude Code Subagents Guide - Nimbalyst](https://nimbalyst.com/blog/claude-code-subagents-guide/) — 7x token / 200-500% overhead / 戦略 B の根拠

---

## 注記

このドキュメントは ADR ではなく **議論の WIP 記録**。 確定実装ではない。 戦略 A の判断確定後、 必要に応じて B-G を順次議論する。
