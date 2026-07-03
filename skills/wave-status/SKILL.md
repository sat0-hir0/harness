---
name: wave-status
description: >-
  ALWAYS invoke to track / check / update wave progress on sliced features. Triggers include Japanese
  phrasings like 「進捗どうなってる」「wave のステータス」「今どこにいる?」「どこまで終わった?」「次の wave 何だっけ?」, English phrasings like "what's the status", "where are we", "which wave is next", "progress on X". Also auto-invoked after `$task-slicing` produces a plan (= `init` action) and after each wave completes (= `mark` action).
  フィーチャーごとに 1 つの markdown ファイルでチェックボックスの状態を管理する $task-slicing の姉妹 skill。 計画と状態を分離することで、
  セッションリセット後も進捗が残る。 SKIP for tasks without an active wave plan.
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
<vendor-home>/state/slice-<feature>.md   ← default (= 例: Claude Code なら ~/.claude/state/slice-<feature>.md)
```

`<feature>` は短い kebab-case のスラッグ (= 例: `sidebar`、`ime-jp`、`ai-completion`)。Lead が `init` 時にスラッグを決める。

**`<vendor-home>` の per-vendor 自己判定**: agent は自分が動いている vendor の config home を選ぶ (= Claude Code なら `~/.claude/`、 Codex なら `~/.codex/`、 Cursor なら `~/.cursor/`、 Gemini / antigravity なら `~/.gemini/`、 universal なら `~/.agents/`)。 vendor 判定は agent 自身の自己認識 (= 起動 binary 名 / cwd / 環境変数) から行う (= `$finish-task` の scripts path 自己判定と同じパターン)。 本 skill 内の `<vendor-home>` は全てこの解決結果を指す。

ホストプロジェクト独自のセッション記録規約がある場合 (= 例: Limn の `.skillshare/records/waves/`)、Lead はそちらにファイルを置いてもよい。 ただし **どちらか 1 つを選んだら最後まで一貫させる**: 同じ feature について global と project の両方にファイルを置くと SSOT が壊れる。

**SSOT 規約 (= 重要)**: `init` 時に決めたパスを、 ファイル自体の frontmatter (= 下記 `path: ...`) に記録する。 以降の `mark` / `show` はその path を辿る。 これで複数 session 跨ぎの drift を防ぐ。 vendor を跨いで続きを扱う場合 (= 例: Claude Code で init した feature を Codex session で mark) は、 自 vendor の `state/` に file が無ければ他 vendor home (= 上記一覧) の `state/slice-<slug>.md` を順に探し、 見つけた file をそのまま使う (= init した vendor の file が SSOT、 複製 / 移動しない)。

## File format

```markdown
---
feature: <slug>
created: <YYYY-MM-DD>
path: <init 時に解決した絶対パス>   # SSOT 規約参照
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
- **Output**: `<vendor-home>/state/slice-<slug>.md` を書き出す (= `<vendor-home>` は File location の per-vendor 自己判定で解決)。front matter と wave ごとに 1 行のチェックボックス行 (すべて `todo`) を含める。
- **Stop on**: ファイルが既に存在する場合。ユーザーに知らせ、re-init (= 上書き) かマージかを選ばせる。

## Phase 2: Mark

### Step 2-1: Locate file
- **Read**: `<vendor-home>/state/slice-<slug>.md` を読む (= 自 vendor に無ければ他 vendor home を順に探す、 File location の SSOT 規約参照)。存在しない場合は明確なエラーを出す。

### Step 2-2: Update one wave
- **Output**: コマンドに従い、対象 wave の記号とラベルを変更する (= done / in-progress / blocked / dropped)。`Log` セクションに日付と変更内容を追記する。
- **Stop on**: wave の参照が曖昧な場合 (= 例: ファイルに wave 3 が存在しないのに "wave 3" が指定された場合)。

### Step 2-3: wave 構成変動時の Issue コメント (= 「🔄 Plan 更新」、 backlog harness 経由時のみ)

**本 skill が 「🔄 Plan 更新」 を投稿するのは、 `$task-slicing` を経由しない直接の mark 操作で wave が dropped/blocked/追加 された場合のみ** (= 責務分離、 二重投稿排除)。 session 透明性のため、 Plan の変動を Issue コメントから追える状態にする。

- **再スライス経由で呼ばれた場合は投稿しない** (= `$task-slicing` の再呼び出し → slice plan 更新 → 本 skill で wave を dropped/blocked に変更、 という流れでは `$task-slicing` 側が既に 「🔄 Plan 更新」 を投稿済み、 task-slicing SKILL.md Plan 更新節参照)。 同一イベントで二重投稿しない。
- **done / in-progress への変更では投稿しない** (= wave が予定通り進んだだけの単純進行は過剰投稿防止のため記録しない)。 投稿対象は **dropped / blocked / 追加** のような構成変動のみ。
#### 投稿目的

本 skill が Issue にコメントする目的は 2 つ:
(1) **透明性担保**: Lead が下した wave 構成変動の判断を、 session がリセットされても追えるようにする。
(2) **作業・判断履歴担保**: dropped / blocked / 追加 / 順序変更 のような wave 構成変動を、 Issue を見るだけで判断の流れが分かる状態を保つ。

**投稿価値のある判断 (= 投稿対象イベント)**:
- wave 構成変動 (= dropped / blocked / 追加 / 順序変更)
- 計画外の判断が発生 (= 例: Wave 追加判断の根拠)

**投稿しないイベント**:
- done / in-progress への単純進行マーク
- 計画通りに次 wave へ進む行為

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
- ✅ 投稿対象: wave 構成変動 (= dropped / blocked / 追加 / 順序変更) を伴う **構造的判断**。
- ❌ 投稿対象外: mid-implementation の些末判断 (= lint fix / typo 修正 / test 1 件追加 / 関数名 rename 等)。 これらは「計画外」 ではなく「計画内の通常進行」。

**無人実行時の Lead 独断禁止 原則**: 無人 (= ultra-autonomous / cron heartbeat / `$issue-execute` で人間不在) では、 Lead が以下を **絶対に独断で行わない**:
- 題材 Issue 不明時に自動で `$issue-from-idea` を呼んで新規 Issue を起こす (= 透明性 / 履歴担保の放棄を AI 単独で決めるのは原則違反)。
- 「曖昧だから今回はスキップしておこう」 と投稿を黙って省略する (= 沈黙は最悪の選択肢)。

代わりに session pause + surface message「題材 Issue 未確定」 を記録して session を終了する。 透明性 / 履歴担保の放棄は user 判断専属。

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
- **Read**: `<vendor-home>/state/slice-<slug>.md` を読む (= lookup 順は Step 2-1 と同じ)。

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
- **Never** backlog 以外の project で Issue コメントを投稿しない。 投稿先は `sat0-hir0/backlog` 固定。 投稿は Step 2-3 の「題材 Issue 同定フロー」1-2 が確定した場合、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ。 過去 context に偶然 `#N` があるだけ (= フロー 4) では投稿しない (= 誤爆防止)。 フロー 3 で有人なら 3 択 surface、 無人なら session pause。

## Helper

この skill はオーケストレーションのみで、スクリプトは不要。状態の操作は plain markdown の編集であり、Lead がこの skill を呼び出して実施する。パスの規約 (`<vendor-home>/state/slice-<slug>.md`) はファイルの場所を口頭で確認することで担保される。

将来スクリプトによる実装が必要になった場合 (= `scripts/wave-status.sh init|mark|read`)、この skill のコントラクトを変えることなく追加できる。

## Final Report

### init
```
wave-status init: <vendor-home>/state/slice-<slug>.md created with N waves (= all todo).
next: Wave 1 — <one-line goal>
```

`<vendor-home>` は解決済みの実 path で出力する (= 例: Claude Code なら `~/.claude/state/slice-sidebar.md`)。

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
