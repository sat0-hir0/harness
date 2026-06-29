---
name: wave-status
description: ALWAYS invoke to track / check / update wave progress on sliced features. Triggers include Japanese phrasings like 「進捗どうなってる」「wave のステータス」「今どこにいる?」「どこまで終わった?」「次の wave 何だっけ?」, English phrasings like "what's the status", "where are we", "which wave is next", "progress on X". Also auto-invoked after `$task-slicing` produces a plan (= `init` action) and after each wave completes (= `mark` action). フィーチャーごとに 1 つの markdown ファイルでチェックボックスの状態を管理する $task-slicing の姉妹 skill。 計画と状態を分離することで、 セッションリセット後も進捗が残る。 SKIP for tasks without an active wave plan.
---

# Wave status

## Use when

- `$task-slicing` がスライス計画を出力したとき (= `$wave-status init <feature>` を呼ぶ)。
- wave がマージされたとき (= `$wave-status mark <feature> wave-N done` を呼ぶ)。
- 新しいセッションで「今どこにいるか」を確認するとき (= `$wave-status read <feature>` を呼ぶ)。
- 何かにブロックされたとき (= `$wave-status mark <feature> wave-N blocked --reason "<text>"` を呼ぶ)。

## Contract

- 1 フィーチャー = 1 markdown ファイル。そのファイルが該当フィーチャーの wave 進捗の唯一の信頼源。
- ステータス値: `todo` / `in-progress` / `done` / `blocked` / `dropped`。
- ファイルは人間が読み書きできる形式。Lead はいつでも手で編集してよい。skill は以下のコントラクト以外のフォーマットを強制しない。

## File location

```
~/.claude/state/slice-<feature>.md   ← default
```

`<feature>` は短い kebab-case のスラッグ (= 例: `sidebar`、`ime-jp`、`ai-completion`)。Lead が `init` 時にスラッグを決める。

ホストプロジェクト独自のセッション記録規約がある場合 (= 例: Limn の `.skillshare/records/waves/`)、Lead はそちらにファイルを置いてもよい。 ただし **どちらか 1 つを選んだら最後まで一貫させる**: 同じ feature について global と project の両方にファイルを置くと SSOT が壊れる。

**SSOT 規約 (= 重要)**: `init` 時に決めたパスを、 ファイル自体の frontmatter (= 下記 `path: ...`) に記録する。 以降の `mark` / `show` はその path を辿る。 これで複数 session 跨ぎの drift を防ぐ。

## File format

```markdown
---
feature: <slug>
created: <YYYY-MM-DD>
plan_source: <スライス計画の場所>   # optional
---

# Wave status: <slug>

## Waves

- [ ] **Wave 1**: <一行ゴール> — `todo`
- [x] **Wave 2**: <一行ゴール> — `done` (= merged 2026-06-23)
- [~] **Wave 3**: <一行ゴール> — `in-progress`
- [!] **Wave 4**: <一行ゴール> — `blocked` (= "<reason>")
- [-] **Wave 5**: <一行ゴール> — `dropped` (= "<reason>")

## ADR
- ADR-NNNN: <title> — Proposed / Accepted

## Flag
- <FLAG_NAME>: stage 1 (hidden) → target stage 2 after Wave 5

## Log (= append-only)
- 2026-06-23: init
- 2026-06-24: Wave 2 done
```

チェックボックスの記号:
- `[ ]` todo
- `[~]` in-progress
- `[x]` done
- `[!]` blocked
- `[-]` dropped

## Phase 1: Init

### Step 1-1: Receive slice plan
- **Read**: `$task-slicing` が出力したスライス計画を読む (= 入力として渡されるか、`plan_source` 経由で見つける)。
- **Decide**: フィーチャーのスラッグを決める。デフォルトは最初の名詞句を正規化したもの。

### Step 1-2: Create file
- **Output**: `~/.claude/state/slice-<slug>.md` を書き出す。front matter と wave ごとに 1 行のチェックボックス行 (すべて `todo`) を含める。
- **Stop on**: ファイルが既に存在する場合。ユーザーに知らせ、re-init (= 上書き) かマージかを選ばせる。

## Phase 2: Mark

### Step 2-1: Locate file
- **Read**: `~/.claude/state/slice-<slug>.md` を読む。存在しない場合は明確なエラーを出す。

### Step 2-2: Update one wave
- **Output**: コマンドに従い、対象 wave の記号とラベルを変更する (= done / in-progress / blocked / dropped)。`Log` セクションに日付と変更内容を追記する。
- **Stop on**: wave の参照が曖昧な場合 (= 例: ファイルに wave 3 が存在しないのに "wave 3" が指定された場合)。

### Step 2-3: wave 構成変動時の Issue コメント (= 「🔄 Plan 更新」、 backlog harness 経由時のみ)

**本 skill が 「🔄 Plan 更新」 を投稿するのは、 `$task-slicing` を経由しない直接の mark 操作で wave が dropped/blocked/追加 された場合のみ** (= 責務分離、 二重投稿排除)。 session 透明性のため、 Plan の変動を Issue コメントから追える状態にする。

- **再スライス経由で呼ばれた場合は投稿しない** (= `$task-slicing` の再呼び出し → slice plan 更新 → 本 skill で wave を dropped/blocked に変更、 という流れでは `$task-slicing` 側が既に 「🔄 Plan 更新」 を投稿済み、 task-slicing SKILL.md Plan 更新節参照)。 同一イベントで二重投稿しない。
- **done / in-progress への変更では投稿しない** (= wave が予定通り進んだだけの単純進行は過剰投稿防止のため記録しない)。 投稿対象は **dropped / blocked / 追加** のような構成変動のみ。
- **投稿条件 (= 2 条件の AND、 他 project への誤投稿防止)**: 投稿前に以下の両方を確認し、 確定していなければ **スキップ** する:
  - (1) `$issue-execute` から hand-off された context である (= Issue 番号が明示的に注入されている。 過去 context に偶然 `#N` 文字列があるだけでは不可)。
  - (2) 対象リポジトリが **`sat0-hir0/backlog`** である (= リポジトリ名が hand-off で明示されている)。
  - 本 skill は汎用なので、 上記 2 条件が確定しない文脈では投稿しない (= 他 project で `gh issue comment` が誤爆して失敗するのを防ぐ)。

```bash
gh issue comment <N> --repo sat0-hir0/backlog --body "🔄 Plan 更新

## 変更点
- Wave N → blocked (= 理由: <reason>)
- (= または dropped / 追加)

## 更新後の Waves
- [x] Wave 1: <goal> — done
- [!] Wave N: <goal> — blocked (= \"<reason>\")
- ...
"
```

## Phase 3: Read

### Step 3-1: Locate file
- **Read**: `~/.claude/state/slice-<slug>.md` を読む。

### Step 3-2: Summarise
- **Output**: wave ごとに 1 行、記号 + ラベル + ステータスを順に出力する。ADR セクションと Flag セクションはそのまま転記する。

### Step 3-3: Recommend next action
- **Decide**: 次に着手できる未ブロックの `todo` を特定する (= `blocked-by` 依存がすべて `done` になっている wave)。
- **Output**: "next: Wave N — <一行ゴール>"。

## Stop condition

- 要求された操作 (= init / mark / read) が正常に完了したか、明確なエラーを返したとき。

## Boundary

- **Never** 既存のステータスファイルを無言で上書きしない。確認するか拒否する。
- **Never** スライス計画にない wave を作り出さない。ステータスファイルは計画のミラー。計画が変わった場合はユーザーが re-init または手動編集する。
- **Never** ステータスを自動で進めない (= `todo` → `in-progress` は Lead の判断、skill が行うものではない)。
- **Must** 冪等であること。既に `done` の wave を再度 `done` にしてもエラーにしない (= Log には touch を記録する)。
- **Never** `done` / `in-progress` への変更で Issue コメントしない (= 過剰投稿防止。 「🔄 Plan 更新」 コメントは dropped / blocked / 追加 のような wave 構成変動時のみ、 Step 2-3)。
- **Never** 再スライス (= `$task-slicing` 再呼び出し) 経由の mark で 「🔄 Plan 更新」 を投稿しない (= `$task-slicing` 側が投稿済み、 二重投稿排除)。 本 skill が投稿するのは `$task-slicing` を経由しない直接 mark の構成変動のみ (= Step 2-3)。
- **Never** backlog 以外の project で Issue コメントを投稿しない。 投稿は **(1) `$issue-execute` から Issue 番号が明示注入されている AND (2) 対象リポジトリが `sat0-hir0/backlog`** の 2 条件 AND が確定した場合のみ。 過去 context に偶然 `#N` があるだけでは投稿しない (= 誤爆防止)。 未確定なら Step 2-3 をスキップ。

## Helper

この skill はオーケストレーションのみで、スクリプトは不要。状態の操作は plain markdown の編集であり、Lead がこの skill を呼び出して実施する。パスの規約 (`~/.claude/state/slice-<slug>.md`) はファイルの場所を口頭で確認することで担保される。

将来スクリプトによる実装が必要になった場合 (= `scripts/wave-status.sh init|mark|read`)、この skill のコントラクトを変えることなく追加できる。

## Final Report

### init
```
wave-status init: ~/.claude/state/slice-<slug>.md created with N waves (= all todo).
next: Wave 1 — <one-line goal>
```

### mark
```
wave-status mark: <slug> wave-N → <new status>.
remaining: <todo count> todo, <blocked count> blocked.
next: Wave M — <one-line goal>  # if any unblocked todo
```

### read
```
wave-status read: <slug>

- [x] Wave 1: <goal> — done
- [x] Wave 2: <goal> — done
- [~] Wave 3: <goal> — in-progress
- [ ] Wave 4: <goal> — todo
- [!] Wave 5: <goal> — blocked ("<reason>")
- [ ] Wave 6: <goal> — todo

ADR: ADR-NNNN Proposed, ADR-MMMM Accepted
Flag: LIMN_FEAT_X stage 1 (hidden), promote after Wave 5

next: resolve Wave 5 blocker, or proceed to Wave 4 (independent of Wave 5)
```

## Related

- `$task-slicing` — この skill が追跡する計画を生成する。
- ホストプロジェクトの skill (= `$start-task`、`$finish-task`、`$review-pr`) — wave ごとに呼び出す。`$finish-task` がクリーンに完了したら wave を done にする。
