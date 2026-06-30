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

#### Issue コメント投稿 (= 「📋 着手 Plan」 軽量版)

##### 投稿目的

本 skill が Issue にコメントする目的は 2 つ:
(1) **透明性担保**: Lead が下した verdict 判断 (= delegate-single / Lead-direct) を、 session がリセットされても追えるようにする。
(2) **作業・判断履歴担保**: verdict / ADR 起票 / 着手判断 など、 Issue を見るだけで判断の流れが分かる状態を保つ。

**投稿価値のある判断 (= 投稿対象イベント)**:
- verdict 判断の確定 (= Lead-direct / delegate-single)
- ADR 起票判断 (= Proposed 起票を決定した事実)
- 着手判断の根拠 (= 計画外の構造的判断が発生した場合)

verdict が `delegate-single` または `Lead-direct` の場合のみ、 hand-off 実行後 (= architect spawn 前。 `Lead-direct` は実装着手前) に 「📋 着手 Plan」 の軽量版 (= wave なし) を Issue に 1 回コメントする。

- **verdict が `delegate-slice` の場合は、 この投稿を実行しない** (= スキップ。 `$task-slicing` Phase 3-4 が wave 付きの 「📋 着手 Plan」 を投稿するため、 ここで投稿すると二重になる)。 `$issue-execute` の hand-off プロンプトは task-routing → task-slicing を連続で走らせる構造なので、 task-routing が Phase 3-2 に到達した上で task-slicing も Phase 3-4 を走る。 明示的にスキップしないと二重投稿する。
- **既存の 「🤖 session 開始」 コメント (= branch/worktree/session 証跡専用) とは別コメント**。 二重投稿しない。

**題材 Issue の同定 (= 投稿条件)**: 以下を順に確認し、 最初に確定したものを投稿先とする。 フロー 1-2 が確定、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ投稿する:

1. `$issue-execute` の hand-off プロンプトに Issue 番号・リポジトリ名が明示注入されている AND 注入された repo 名が **`sat0-hir0/backlog`** である → `sat0-hir0/backlog` へ投稿 (= 最高信頼度)。 注入された repo 名が `sat0-hir0/backlog` 以外なら、 フロー 1 では確定せずフロー 3 に落とす (= 別 project の Issue 番号を backlog に誤投稿しないため)。
2. ユーザーが当該 session で「#N」「Issue N」「backlog#N」等を明示的に言及しており、 かつ対象が `sat0-hir0/backlog` であることが文脈から確定している → 投稿 (= 高信頼度)。
3. session の直前の発話に Issue 番号はあるが、 リポジトリが確定していない → 有人なら 3 択を surface: (a) 新規 Issue を起票して投稿 / (b) 既存 Issue に投稿 (番号を指定) / (c) 今回は残さない。 無人 (= ultra-autonomous / `$issue-execute` で人間不在) なら session pause して「題材 Issue が確定していません。 Issue 番号 / リポジトリを明示してから再開してください。」を記録して終了。
4. 過去 context に偶然 `#N` 文字列が混入しているだけで、 明示的言及がない → **投稿しない** (= 誤爆防止)。
5. Issue 番号が存在しない → **投稿しない**。

フロー 1-2 が確定、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ投稿を実行する。 投稿先リポジトリは `sat0-hir0/backlog` 固定。 他リポジトリへは投稿しない。

posture: **user に明示的に「不要」 と言われない限り、 投稿価値のある判断は投稿 / 立ち戻りを行う** (= デフォルトは投稿側に倒す、 沈黙すると判断が消える)。

**3 択 (c) 「今回は残さない」 を選んだ場合の session 内記録**: surface 直後の chat に Lead が以下の 1 行 log を必ず出す (= 履歴担保の最低保証):

> 📝 透明性 / 履歴担保の放棄を user が許容 (= 判断「<1 行要約>」を Issue に残さない選択)。 session 内のみで完結。

これにより、 (c) を選んだ事実そのものが session 内に残る (= 後から「なぜ Issue に紐付けなかったか」 が追える)。

**「計画外の判断」 の定義 (= escape valve、 過剰 surface 防止)**:
- ✅ 投稿対象: verdict 確定 / ADR 起票判断 / 大幅な scope 逸脱判断 のような **構造的判断**。
- ❌ 投稿対象外: mid-implementation の些末判断 (= lint fix / typo 修正 / test 1 件追加 / 関数名 rename / git commit メッセージ調整 等)。 これらは「計画外」 ではなく「計画内の通常進行」。

**無人実行時の Lead 独断禁止 原則**: 無人 (= ultra-autonomous / cron heartbeat / `$issue-execute` で人間不在) では、 Lead が以下を **絶対に独断で行わない**:
- 題材 Issue 不明時に自動で `$issue-from-idea` を呼んで新規 Issue を起こす (= 透明性 / 履歴担保の放棄を AI 単独で決めるのは原則違反)。
- 「曖昧だから今回はスキップしておこう」 と投稿を黙って省略する (= 沈黙は最悪の選択肢)。

代わりに session pause + surface message「題材 Issue 未確定」 を記録して session を終了する。 透明性 / 履歴担保の放棄は user 判断専属。

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
- **Never** 技術 doc / ADR / コード comment / panic msg / `#[ignore]` reason / config comment / skill 例 / 設計案 / report / commit msg / PR body に **マイルストーン / Phase / Wave 名 (= M0-M5, Phase 2, Wave 9-D, Sprint N)** / **将来時制 (= "will be", "later wave", "deferred to ...", "is cut when X")** / **拡張予定 / future-proofing 表現 (= "for future X", "extensible to ...", "may add Y later", "(and any future palette extension)")** を書かない。 詳細は本セクション直下の 「将来予定を書かない」 を参照。 reviewer 系 agent (= qa-expert / performance-engineer / security-auditor / architect / technical-writer) は本ルール違反を **指摘対象** として扱う。
- **Stop** ユーザー要求が純粋に情報目的 (= 書きなし、 exec なし) なら止める。 この skill は code/docs/state 変更タスク用。
- **Must** verdict 1 つにつき Y-trace 1 行を添える。 escape valve は自明な Lead-direct (= 1 ファイル typo / mechanical rename) のみ。 「結論だけ来て判断に困る」 という user feedback への構造的対応 (= reasoning trace 長さが perceived difficulty proxy になる業界知見、 Y-Statement format = 5 要素 1 文の MADR 派生)。
- **Never** Y-trace を MUST にしてすべての判断に重い trade-off 表を要求しない。 1 行 ≒ 30-50 token、 出力肥大を防ぐため形式を 1 行に縛る。

## 将来予定を書かない (= 全 agent 遵守 + reviewer 指摘対象)

### ルール

技術 doc / ADR / コード comment / panic msg / `#[ignore]` reason / config comment / skill 例 / 設計案 / report / commit msg / PR body に、 以下 3 種を **一切書かない**:

1. **マイルストーン / Phase / Wave 名** (= M0-M5, Phase 2, Wave 9, Wave 10-D, Sprint N 等の内部 slice 番号)
2. **将来時制 commitment** (= "will be implemented", "later wave", "deferred to ...", "is cut when X", 「M5 で再評価」, 「Phase 2 で実装」)
3. **拡張予定 / future-proofing 説明** (= "for future X", "extensible to ...", "may add Y later", "(and any future palette extension)", 「将来 X に拡張可能」)

**codename rename も不可** (= 「Phase 2 で実装」 → 「次の段階で実装」 のような言い換えは本質温存)。 削除一択。

**OK な表現**:
- **present-fact / present-state** (= 「currently a small parser」 「not yet implemented」 「ignored until X is implemented」) — 「現状」 を述べているだけで commitment ではない
- **不確実性表現** (= 「the timeline is uncertain」 「may still be open」) — commitment ではない
- `$task-routing` の Y-trace `accepting:` 欄の **受け入れる trade-off** (= 「wave 分割で実装期間 1 → 3 セッションに伸びる」) — 判断の現在地を記述しているだけ

### なぜダメか (= 背景、 全 agent に伝達)

1. **AI hallucination の温床**: 一度書かれた 「Wave 6 で対応」 が次 session で 「実装根拠」 として参照される連鎖事故が実例で発生 (= 2026-06 limn で ARCHITECTURE.md → ADR → panic msg → `#[ignore]` reason に 28 file 汚染、 後続 PR sat0-hir0/limn#13 unmerged で close)
2. **読者の問い合わせ先が repo 内にない**: 「いつ?」 「誰が?」 を聞ける場所が repo に存在しない (= GitHub Issue / Project / ROADMAP が本来の置き場)。 repo 内に書くと嘘になりやすい (= 順番が変わる / codename 自体が消える)
3. **ADR は過去の判断記録**: 未来 commit を書く場所ではない (= 再評価が必要になったら別 ADR を新規起票するのが governance)
4. **numeric label rename は本質温存で罠**: 「M2 → Phase 2」 と書き換えても 「いつ」 commitment が repo に残る (= grep / 静的解析が効かないので scope 判断の障害になる)

### How to apply

- 編集時に上記 3 種を見つけたら、 周辺文脈を読んで 「単純削除で文意が通るか / 書き換えが要るか / 章ごと削除すべきか」 を判断。 **機械置換は禁止** (= 文脈なし置換で意味壊れる)
- 削除した結果コード側に **orphan な panic / `#[ignore]` / 仮実装 comment** が残ったらセットで直す (= reason は 「現在の事実」 で書く)
- reviewer 系 agent (= qa-expert / performance-engineer / security-auditor / architect / technical-writer) は diff レビュー時に **本ルール違反を指摘対象として扱う**。 「Wave 6 で対応」 「will be implemented」 を見つけたら問題として上げる
- Lead-direct 経路 (= 直接実装) でも本ルールは同様に適用

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
