---
name: task-routing
description: Routes any non-trivial development request to a verdict (Lead-direct / delegate-single / delegate-slice) that the Lead MUST follow. ALWAYS invoke at the very first turn, BEFORE any Edit / Write / Bash / sub-agent call, whenever the user asks to add, fix, change, refactor, implement, set up, wire up, integrate, respond to, debug, or investigate code / docs / config / build / CI / project state. Triggers include Japanese phrasings like 「実装して」「直して」「追加して」「入れて」「対応して」「セットアップ」「調べて」「足して」「動かして」「リファクタ」, English phrasings like "add X", "fix X", "set up X", "implement X", "wire X", "handle X", and any mention of file paths, function names, or build / test commands. SKIP for pure-info questions ("what is X?", "explain Y") with zero file writes / shell, AND for consult / ideation requests (use $intent-clarify instead). Skipping this is the #1 source of misrouted work (= Lead-direct on tasks that should have been delegated, missed ADR triggers, public-behaviour changes slipped past review). **OUTPUT CONTRACT**: every verdict MUST be accompanied by a Y-trace 1-liner (= 採用根拠 + 棄却した代替 + 受け入れる trade-off) so the user can audit the judgement without re-deriving it. Format: `判定: <verdict> | ∵ <why this>, 棄却: <what & why not>, accepting: <trade-off>`. Skip Y-trace only for self-evident Lead-direct (= 1 file typo, mechanical rename) where context already proves the verdict; default is add.
---

# Task routing

## Use when

- 明らかな chat 質問 (= 「X を説明して」 / 「Y って何?」) 以外のすべてのユーザー要求。
- 具体的には: コード / docs / 外部状態に触れるすべて。

純粋に情報を求められているだけ (= ファイル書き込みなし、 1 回の read だけ) ならスキップ。

## Why this skill exists

理由は 2 つ:

1. **AI agent の精度**: 役割分離で hallucination を減らせる。 Lead は監督、 専門 sub-agent (= architect / fullstack-engineer / reviewer / qa-verifier) が各自のスコープを担当。 各 agent は必要なものだけ読む。
2. **context window**: routing rule を CLAUDE.md ではなくこの skill に置くと、 Lead の context が軽く保たれる。 invoke されたときだけ load される。

default は **委譲**。 Lead-direct は trivial な機械的編集だけの例外。

## Contract

- ユーザー要求 1 件につき verdict 1 つを出力: `Lead-direct` / `delegate-single` / `delegate-slice`。
- verdict は次のアクションを決める。 この skill 自体はタスクを実行しない。

## Phase 1: 定性 gate (= 3 つの質問)

3 つすべてに答える。 迷ったら NO に倒す。

### Step 1-1: 公開挙動の変更?

- **判定**: この変更で UI 挙動 / public API / runtime contract / CLI semantics / on-disk file format が変わるか?
- **NO** = 公開挙動は変わらない。
- **YES** = 委譲 (= 「いずれかが NO」 のカウントに加える)。

### Step 1-2: harness で検証可能?

- **判定**: プロジェクトの既存 verifier (= typecheck / cargo test / clippy / project-specific verify-* / golden files) が正しさを客観的に確認できるか?
- **YES** = harness がカバーする、 他条件も OK なら Lead-direct 可能。
- **NO** = harness 外、 人か sub-agent の判断が要る → 委譲。

### Step 1-3: 設計判断は不要?

- **判定**: 原因が確定済 AND 修正は既存パターンの素直な適用 (= grep-1-shot、 昨日と同じ) か?
- **YES** = 設計判断なし。
- **NO** = 設計判断が要る → 委譲。

### Step 1-4: 補助指標 (= ファイル数)

主決定軸ではないが sanity check として:

- **触るファイル ≤1 (= 開始前推定)** AND 上 3 つが全部 「Lead-direct」 → 本当に Lead 可能。
- **≥2 ファイル**、 定性 OK でも → 再検討。 多ファイルはたいてい層をまたぐか設計判断が Step 1-3 で見落とされている。

ファイル数だけで定性 gate を上書きしない。 sanity check のみ。

## Phase 2: Verdict

```
Step 1-1 NO  AND  Step 1-2 YES  AND  Step 1-3 YES   → Lead-direct
(いずれかが Step 1-1 YES / 1-2 NO / 1-3 NO)  → 委譲
```

委譲なら single か slice かを決める:

### Step 2-1: スコープ見積もり

- **XS** (= 1-2 ファイル、 単一の論理変更、 新 dep なし) → `delegate-single`
- **S-M** (= 3-4 ファイル、 1 feature、 新 dep あるかも) → `delegate-single` (= architect + fullstack + reviewer + qa-verifier 並列の 1 ラウンド)
- **L-XL** (= 5+ ファイル、 層をまたぐ、 複数の判断) → `delegate-slice`

### Step 2-2: Verdict

- `Lead-direct` → Lead が直接実装。 sub-agent なし。
- `delegate-single` → プロジェクト標準チェーンを 1 回 (= architect → fullstack-engineer → reviewer + qa-verifier の並列レビュー)。
- `delegate-slice` → `$task-slicing` で wave 分割、 `$wave-status init`、 各 wave を標準チェーンで。

## Phase 3: Hand-off

### Step 3-1: Verdict を宣言 (= Y-trace 必須)

- **出力**: ユーザーに 1 行サマリ + Y-trace 1 行 (= 計 2 行)。
- **Y-trace format**: `判定: <verdict> | ∵ <採用根拠 = どの gate がどう転んだか>, 棄却: <候補と棄却理由>, accepting: <受け入れる trade-off>`
- **根拠の確度を開示**: `∵` の後ろに **「memory / grep / file 確認 / 推測」 のどれか** を含める (= user が「調べた」 と「推測した」 を区別できる)。
- 例:
  - `判定: Lead-direct | ∵ file 確認: 1 ファイル + 公開挙動なし + harness OK, 棄却: delegate-single = 単一 typo に overhead, accepting: 自己 review 範囲 = typo なので低リスク`
  - `判定: delegate-single (S) | ∵ grep: 3 ファイル想定 + 1 feature + 新 dep なし, 棄却: Lead-direct = 公開挙動 (CLI arg) 変更で reviewer 必須, accepting: 1 ラウンド spawn コスト ≒ 5 min`
  - `判定: delegate-slice (L) | ∵ 推測: 5+ files + 層またぎ + 設計判断 3 件, 棄却: delegate-single = 1 PR 巨大化リスク, accepting: wave 分割で実装期間 1 → 3 セッションに伸びる`
- **escape valve**: 自明な Lead-direct (= README typo / 1 行 rename) は Y-trace 省略可。 迷ったら付ける。

### Step 3-2: Hand-off 実行

- `Lead-direct`: 実装に進む。
- `delegate-single`: `architect` (= read-only 調査 + 設計) → `fullstack-engineer` (= 実装) → `reviewer` (= 敵対的レビュー) + `qa-verifier` (= typecheck/test) を並列 spawn。 Lead は監督、 **ファイル編集しない**。
  - **必須**: 実装後に `reviewer` + `qa-verifier` を **必ず並列 spawn** する。 Lead が直接実装してレビュー / 検証を兼ねる代替は **不可** (= 自己レビューは敵対的視点を欠く、 spawn 省略は単独責任で品質落ちる主因)。
  - 「軽微だから」 「すぐ済むから」 で省略しない。 spawn 自体を skip するのは Lead-direct verdict のときだけ。
- `delegate-slice`: `$task-slicing` invoke。 slice plan 完了後 user 承認、 各 wave を `delegate-single` 相当で回す。
  - **無人起動時 (= `$issue-execute` 経由 / 人間不在の自動 session) は user 承認を待たず自動 proceed**。 承認者が不在なので計画提示で止まらない。 計画を `$prepare-uat` に逃がして実装を放棄するのは **禁止** (= 詳細は `$task-slicing` の 「無人起動時のデフォルト」 セクション)。
  - **必須**: 各 wave で **reviewer + qa-verifier を必ず spawn** する。 wave スキップ (= 「この wave は小さいから reviewer 省略」) は **不可**。
  - **ADR が要る wave**: `$adr-proposal` 等で **Proposed として起票だけ** する。 **Accepted 昇格は別 turn で user 確認後** に行う (= 同一 turn で起票から昇格まで通すと user の design judgement 機会を奪う)。

#### Issue コメント投稿 (= 「📋 着手 Plan」 軽量版、 backlog harness 経由時のみ)

verdict が `delegate-single` または `Lead-direct` の場合のみ、 hand-off 実行後 (= architect spawn 前。 `Lead-direct` は実装着手前) に 「📋 着手 Plan」 の軽量版 (= wave なし) を Issue に 1 回コメントする。 session が途中で死んでも着手内容を Issue から追えるようにするため。

- **verdict が `delegate-slice` の場合は、 この投稿を実行しない** (= スキップ。 `$task-slicing` Phase 3-4 が wave 付きの 「📋 着手 Plan」 を投稿するため、 ここで投稿すると二重になる)。 `$issue-execute` の hand-off プロンプトは task-routing → task-slicing を連続で走らせる構造なので、 task-routing が Phase 3-2 に到達した上で task-slicing も Phase 3-4 を走る。 明示的にスキップしないと二重投稿する。
- **投稿条件 (= 2 条件の AND、 他 project への誤投稿防止)**: 投稿前に以下の両方を確認し、 確定していなければ **投稿をスキップ** する:
  - (1) `$issue-execute` から hand-off された context である (= Issue 番号が明示的に注入されている。 過去 context に偶然 `#N` 文字列があるだけでは不可)。
  - (2) 対象リポジトリが **`sat0-hir0/backlog`** である (= リポジトリ名が hand-off で明示されている)。
  - 両方が確定していなければ投稿しない (= 他 project で `gh issue comment` が誤爆して失敗するのを防ぐ)。
- **既存の 「🤖 session 開始」 コメント (= branch/worktree/session 証跡専用) とは別コメント**。 二重投稿しない。

```bash
gh issue comment <N> --repo sat0-hir0/backlog --body "📋 着手 Plan (軽量版)

## Verdict
- delegate-single (S) (= または Lead-direct)

## アプローチ (= wave なし、 1 ラウンド)
- <1-2 行で着手内容>

## Agent chain
- architect → fullstack-engineer → reviewer + qa-verifier → \$finish-task
- (= Lead-direct の場合は 「Lead 直接実装 (= sub-agent なし)」)

## ADR
- ADR-NNNN: <title> — Proposed (= 無ければ 「なし」)
"
```

**Agent Teams (= 複数 teammate 並列) を起動する局面**: 上記 `delegate-single` の reviewer + qa-verifier は通常の subagent 並列で済む。 Agent Teams は **3+ 次元** (= security / perf / docs / test 等) で同時 depth が必要なときに限る。 環境制約: WezTerm は split-pane 非対応 → **in-process mode 一択** (= 1 terminal で agent panel UI)。

### Step 3-3: Autonomous mode

ユーザー要求に 「ざっくり」 / 「勝手に進めて」 / "you decide" / "go ahead" 等が含まれていたら:

- verdict + 直後アクションを surface。
- step ごとの承認なしで進む、 wave 境界 (= `delegate-slice`) または最終 review (= `delegate-single`) だけ surface。
- **autonomous mode でも止める条件**:
  - 3 質問のいずれかに自信を持って答えられない (= 「公開挙動を変えるか不明」) → ユーザーに 1 つ clarify を聞く。
  - sub-agent が user の product 判断を要する blocker を報告 (= flag 昇格、 スコープ逸脱、 仕様 defer) → surface。
  - 連続 2 回の verification 失敗 → surface。

#### Ultra-autonomous mode (= wave 完了通知も出さず全走破)

`delegate-slice` のとき、 さらに踏み込んで **wave 完了通知を出さず最後に 1 回だけ報告** する mode。 trigger:

- user 発話に 「全部やって」 「最後まで止まらず」 「ultra」 「wave 完了通知要らない」 等。
- 直前に `$issue-execute` が hand-off プロンプトに `Execution mode: ultra-autonomous` を inject した状態で本 skill が起動された (= backlog Issue 経由)。 hand-off プロンプトの `Execution mode:` 行を必ず読み、 値が `ultra-autonomous` なら ultra で動かす。 値が `step-by-step` なら通常 autonomous (= wave 境界で pause) で動かす。 `Execution mode:` 行自体が存在しない場合 (= chat 直起動、 または別 entry-point) は user 発話 trigger だけで判断 (= ultra ワードがなければ通常 autonomous)。

ultra の挙動詳細 (= 計画 1 回承認 → 全 wave 走破 → 最終報告 1 回) は `$task-slicing` の 「Ultra-autonomous mode」 セクションを参照。 Stop conditions は通常 autonomous と同じ。

**チケット起動 (= `$issue-execute` が `Execution mode: ultra-autonomous` を inject) の場合、 計画 1 回承認のゲートは自動 proceed**。 人間が不在なので承認を待たず、 **全 wave を最後まで走破 → 最後に 1 回だけ `$prepare-uat` でまとめ UAT** に到達することがゴール。 「規模が XL」 「未確定リスク (= IME 等) がある」 「ADR が要る」 はいずれも **停止理由にならない** (= 検証は wave 内タスク、 ADR は Proposed 起票して進む)。 計画段階 / wave 境界で止めて Awaiting UAT に逃がすのは **誤動作**。 止めて良いのは Stop conditions の 4 件 (= 真の異常) のみ。

## Project git workflow integration

verdict が決まったら、 **実装着手前** に project の git 規約を確認:

- `docs/development/git-strategy.md` か `AGENTS.md` (= プロジェクトの contributor 向け doc) を **必ず読む**。 AI workflow / branch 戦略 / PR template に関する規約があればそれに従う。
- **multi-file 変更 / 新 feature 追加 / public API 変更 / 公開挙動変更** のいずれかに該当するなら、 **必ず feature branch を切る** (= `git checkout -b <type>/<scope>`)。 main 直 commit は **不可**。
- 気付かず main で作業し始めたら **即 stop して branch を切り直す** (= `git stash` → `git checkout -b ...` → `git stash pop`)。 「もう数行書いたから」 は理由にならない。
- `Lead-direct` (= trivial / 単一ファイル / 公開挙動不変) でも、 project 規約が branch 必須なら従う。 規約が無い場合に限り main 直 commit は許容範囲。

`delegate-single` / `delegate-slice` のときは hand-off 前に Lead が branch を切ってから sub-agent に渡す (= sub-agent 側で branch 戦略の判断負担を持たせない)。

## Stop condition

- verdict が決まり、 対応する hand-off が始まっている (= Lead 実装中 / architect spawn 済 / `$task-slicing` invoke 済)。

## Boundary

- **Never** 多ファイル変更 / 公開挙動変更を `Lead-direct` にルーティングしない。 Lead の仕事は監督であって編集ではない。
- **Never** XS-S タスクで `$task-slicing` を invoke しない。 単一 feature の slice は overhead だけ。
- **Never** L+ タスクで `delegate-single` を invoke しない。 1 ラウンド委譲は大規模 PR と context あふれを生む。
- **Must** 3 質問のいずれかに自信を持って答えられないときは surface。 委譲の摩擦を避けるために黙って 「Lead-direct」 と仮定しない。
- **Must** ファイル数指標は advisory のみと扱う。 定性 gate が判断。
- **Never** `delegate-single` / `delegate-slice` の各 wave で `reviewer` / `qa-verifier` の spawn を省略しない。 **autonomous mode でも省略不可**。 「軽微」 「時間ない」 「自分で見たから OK」 はすべて却下理由 (= 自己レビュー bias で品質落ちる主因)。 spawn 自体を skip して良いのは Lead-direct verdict のときだけ。
- **Never** `delegate-slice` で ADR を同一 turn で Proposed から Accepted に昇格させない。 起票 = この turn、 昇格 = 別 turn (= user 確認後)。
- **Never** project 規約が branch を要求するときに main 直 commit しない。 multi-file / 新 feature / 公開挙動変更なら **必ず feature branch**。
- **Stop** ユーザー要求が純粋に情報目的 (= 書きなし、 exec なし) なら止める。 この skill は code/docs/state 変更タスク用。
- **Must** verdict 1 つにつき Y-trace 1 行を添える。 escape valve は自明な Lead-direct (= 1 ファイル typo / mechanical rename) のみ。 「結論だけ来て判断に困る」 という user feedback への構造的対応 (= reasoning trace 長さが perceived difficulty proxy になる業界知見、 Y-Statement format = 5 要素 1 文の MADR 派生)。
- **Never** Y-trace を MUST にしてすべての判断に重い trade-off 表を要求しない。 1 行 ≒ 30-50 token、 出力肥大を防ぐため形式を 1 行に縛る。

## Helper

orchestration のみ、 script なし。 Lead は各タスクの冒頭でこの skill を呼び、 ユーザー向けには 「verdict + hand-off」 を 1 行で surface する (= Phase 3-1 の出力)。 下記 YAML Final Report は内部記録用で、 ユーザー向けには出さない (= 1 行と YAML は別レイヤー)。

## Final Report

```yaml
task-routing:
  request: <1 行サマリ>
  invoked_from: user-direct | intent-clarify-handoff  # intent-clarify から one-directional に渡されたら後者
  qualitative_gate:
    public_behaviour_changed: yes | no
    harness_verifiable: yes | no
    design_judgement_needed: yes | no
  file_count_proxy: <N>
  scope_estimate: XS | S | M | L | XL
  verdict: Lead-direct | delegate-single | delegate-slice
  hand_off: <次に invoke するもの>
  autonomous: yes | no
```

## Related

- `$intent-clarify` — 相談 / 観点出し / 意図整理を直接受ける sibling skill (= 別入口)。 本 skill は intent-clarify から確定 intent を受け取って起動されることがある (= one-directional hand-off、 ループしない)。
- `$task-slicing` — verdict が `delegate-slice` のとき invoke。 wave 分解。
- `$wave-status` — `$task-slicing` 後に init。 L+ タスクの進捗追跡。
- プロジェクト個別 skill (= 例: Limn の `$adr-proposal` 等) — wave ごと / `delegate-single` ごとに invoke。

## Worked examples

### Example 1: 「README L42 の typo を直して」
- 公開挙動: NO
- harness 検証可: YES (= lychee / markdownlint がキャッチ)
- 設計判断: NO
- ファイル数: 1
- **Verdict**: `Lead-direct`
- **Y-trace**: 省略可 (= 自明 escape valve、 1 ファイル typo)

### Example 2: 「limn-core utils に Vec::tail() ヘルパー追加」
- 公開挙動: NO (= 内部ヘルパー)
- harness 検証可: YES (= cargo test)
- 設計判断: NO (= 素直)
- ファイル数: 1-2
- **Verdict 判定**: 開始前推定で 1 ファイルなら `Lead-direct`、 test ファイルを編集する見込みがあるなら `delegate-single`。 1 つだけ選んで宣言する (= or は禁止)。

### Example 3: 「Alfred みたいなコマンドパレットを足して」
- 公開挙動: YES (= 新 keybinding、 新 modal)
- harness 検証可: 部分的 (= modal focus の E2E なし)
- 設計判断: YES (= fuzzy lib、 provider、 prefix)
- ファイル数: 5+
- Scope: L
- **Verdict**: `delegate-slice` → `$task-slicing`
- **Y-trace**: `判定: delegate-slice (L) | ∵ 推測: 新 modal + keybinding + fuzzy lib 選定 = 5+ files / 設計判断 3 件, 棄却: delegate-single = 1 PR 巨大化 + reviewer の review 範囲過大, accepting: wave 分割で fuzzy lib 選定が wave 1 で blocking question 化`

### Example 4: 「main.rs の .expect() を ? に置き換え」
- 公開挙動: NO
- harness 検証可: YES
- 設計判断: NO
- ファイル数: 1
- **Verdict**: `Lead-direct`

### Example 5: 「GPL containment policy の新 ADR」
- 公開挙動: NO (= ADR は record、 behaviour ではない)
- harness 検証可: 部分的 (= adr-consistency.sh が format をキャッチ)
- 設計判断: YES (= ADR 自体が決定の記録)
- ファイル数: 1-2
- **Verdict**: `delegate-single` (= プロジェクトの `$adr-proposal` skill が独自のレビューチェーンを持つ)
- **Y-trace**: `判定: delegate-single (XS) | ∵ file 確認: ADR 1 ファイル + 公開挙動なし + 設計判断 = ADR 本体, 棄却: Lead-direct = 設計判断が ADR の核なので reviewer 必須, accepting: ADR 起票 = Proposed のみ、 Accepted 昇格は別 turn`
