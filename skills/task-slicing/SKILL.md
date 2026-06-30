---
name: task-slicing
description: ALWAYS invoke when the user asks to slice / split / decompose a large feature into stages or waves. Triggers include Japanese phrasings like 「wave に切って」「スライスして」「段階分けして」「feature を分割して」「どう段階化する?」「リリース計画を立てて」, English phrasings like "slice this", "break this into waves", "stage this rollout", "decompose this feature". Also auto-invoked when `$task-routing` returns `delegate-slice` verdict for L+ tasks (= 5+ files / cross-layer / multiple judgements). Outputs a slice plan with UAT-able vertical waves mapped to release / flag stages (= 実装はしない). 本 skill 内で参照される project skill 名 (= 例: $propose-adr / $start-task / $review-pr) は project 個別の慣例で、 違うプロジェクトでは hand-off 行をそのプロジェクトの chain に読み替える。 SKIP for XS-S tasks (= 1-4 files, single feature) and pure-info questions.
---

# Task slicing

## Use when

- フィーチャーリクエストが中〜大規模 (≥2 ファイル、公開挙動の変更、または自明でない調査が必要) である。
- `$task-routing` の verdict が `delegate-slice` だった (= Phase 1 定性 gate のいずれかが NO で、 かつスコープが L-XL)。
- 非自明なタスクに対して、 project の chain skill (= 例: `$propose-adr` / `$start-task`) を呼ぶ前。

自明な Lead 単独対応 fix なら本 skill はスキップしてよい。

## Contract

- slice plan (= wave の順序付きリスト) を出力する。すべての wave は独立して UAT 可能でなければならない。
- ユーザーには見えない deliverable しか持たない wave は **wave ではない**。次の wave とマージするか、検証 surface (log / debug CLI / dump コマンド) を追加する。
- slice plan を作るだけ。本 skill でコードは書かない。

## Phase 1: Understand

### Step 1-1: リクエストを読む

- **Read**: ユーザーのフィーチャーリクエストを原文のまま読む。明示された制約があればメモする (= 「これは諦めて良い」「symlink は後回し」等)。
- **Decide**: 何の観測可能なユーザー向け変化が求められているか? 1 文で書く。

### Step 1-2: 既存制約を読む

- **Read**: 関連する `AGENTS.md` / `ARCHITECTURE.md` / `CLAUDE.md` / 既存 ADR を読む。
- **Decide**: このフィーチャーが触れる既存制約 (= レイヤー境界 / std-only / 依存ポリシー / 公開 API 安定性 / round-trip 等) を特定する。
- **Output**: slice plan の `## Constraints` セクションに制約一覧を書く。

### Step 1-3: 多次元評価

- **Decide** 各次元を決定する:
  - **Size** (= XS / S / M / L / XL — 下表)
  - **Difficulty** (= 既存パターンの再利用 vs 新規発明)
  - **Impact scope** (= public-behaviour / private-only / docs-only)
  - **New dependencies** (= 0 / +1 / +many)
  - **Verifier coverage** (= どの `$verify-*` が発火するか; 件数)
- **Output**: slice plan に評価テーブルを書く。

#### Size テーブル

| Size | Files | 説明 | 目安時間 |
|---|---|---|---|
| XS | 1 | 関数 1 つの調整 | <30 min |
| S | 1-2 | 論理的変更 1 つ | <1 h |
| M | 3-5 | フィーチャー 1 つ、スコープ明確 | 1-2 h |
| L | 5-8 | 複数モジュールをまたぐ | 2 h+ |
| XL | 8+ | **必ずスライスする** — 1 wave での計画は拒否 | N/A |

### Step 1-4: `$task-routing` で再確認 (= 取り違え防止)

- **Read**: `$task-routing` の Phase 1 定性 gate (= 3 質問 + ファイル数指標)。
- **Decide**: verdict が `Lead-direct` に該当 → 本 skill は不要、**直接実装へ戻る**。`delegate-single` → 本 skill は不要、 標準チェーン 1 回で済む。`delegate-slice` のみ Phase 2 へ進む。
- **Note**: `$task-routing` 起動後にこの skill に来ているはずだが、 ユーザーが直接 `$task-slicing` を呼んだ場合の sanity check。

## Phase 2: Slice

### Step 2-1: スライス候補を列挙

- **Output**: 候補 wave を各々以下の情報付きで列挙する:
  - 1 行ゴール (= 「この wave がマージされた後にユーザーができること」)
  - UAT 方法 (= GUI / CLI / log / debug surface / test output — いずれか 1 つ)
  - UAT スクリプト (= ユーザー操作 → 観測可能な出力 → pass 基準)

### Step 2-2: UAT 不能 wave を除外

- **For each candidate**: 現実的な UAT 方法がない場合、その wave は無効。
- **Decide**: (a) 隣接 wave とマージする、(b) deliverable にデバッグ surface を追加する、(c) 後の wave の UI が検証 surface を提供するまで延期する、のいずれかを選ぶ。
- **Stop on**: これらの選択肢を適用してもまだ UAT 不能な wave が残る場合はユーザーに surface する。黙って plan に残さない。

### Step 2-3: 依存順に並べる

- **Output**: wave を実行順に並べる。未マージの wave に依存する wave (= 別フィーチャー / マイルストーンのものであっても) はブロックされる。`blocked-by` としてマークする。

### Step 2-4: Foundation wave は OK

エンドユーザーに見える UI がまだない基盤作業 (foundation work) は、以下の自前の検証 surface を持つ場合に限り有効な wave である:
- `cargo run --example dump-X` が観測可能な出力を生成する、または
- `RUST_LOG=debug` が該当するログ行を出力する、または
- 隠し `--debug-X` フラグが状態を露出する、または
- テスト名 + その evidence がユーザーに「OK」と言わせるに足りる。

**「基盤を作った、次の wave で見えるようになる」は wave として無効。** 除外して次の wave とマージする。

## Phase 3: Map

### Step 3-1: ADR 数を決める

- **Decide**: アーキテクチャ上の判断 1 つにつき ADR 1 つ。1 wave に複数の判断 → 複数の ADR。複数 wave が 1 つの判断を実装 → ADR 1 つ。
- **Output**: ADR タイトルと対象 wave を書く。

### Step 3-2: wave を リリース/flag ステージにマップ

`wave : flag = N : M`。Wave のマージ ≠ リリース。Flag の昇格は **プロダクト判断** であり、wave マージから自動導出しない。

各 wave について:
- どの flag がゲートしているか (= 既存 flag / 新規 flag / flag なし)
- どのステージに着地するか (= hidden / experimental / stable)
- 完了がどのステージ昇格をトリガーするか (= 「Wave N 完了 → flag X を hidden から experimental に昇格」、または「昇格なし」)

Wave は **クリーンにマージされ (DoD 完了)** て初めて done とカウントされる。ステージ昇格はそれとは別の、後続の判断。

### Step 3-3: Hand-off 計画

- **Output**: wave ごとに呼び出す agent チェーンを書く (= 例: `$propose-adr → $review-design → $start-task → fullstack-engineer → $review-pr → $finish-task`)。
- Lead は実装しない。Lead は監督し、ルーティングする。

#### Branch / push / PR 戦略

- **Wave 1 着手前に feature branch を切る** (= `feat/<topic>` 等、 project の `docs/development/git-strategy.md` または同等の規約に従う)。 main から直接実装を始めない。
- **各 wave 完了で commit** (= Conventional Commits 形式、 project の commit hook が enforcer)。
- **全 wave 完了で push、 PR は user に依頼する** (= Lead は `git push` まで実行、 PR 作成は user の判断ステップとして残す)。 ただし autonomous mode で 「勝手に PR まで」 と明示された場合のみ Lead が PR を作る。

## Slice plan テンプレート (= 本 skill の出力物)

```markdown
# Slice plan: <feature name>

## Request (1 sentence)
<what the user asked for>

## Constraints
- <constraint 1>
- <constraint 2>

## Evaluation
| Dimension | Value |
|---|---|
| Size | L |
| Difficulty | new-invention in part X, reuse-of-existing in part Y |
| Impact scope | public-behaviour |
| New dependencies | +1 (= <crate>, license <Apache-2.0/MIT/etc.>) |
| Verifier coverage | `<project's verifier suite from scripts/ or CI>` (= N verifiers) |

## Lead 単独着手の可否
- (1) ≤1 file: NG (= touches 5 files)
- (2) no public-behaviour change: NG (= adds Ctrl+P binding)
- (3) fix is obvious: NG (= async strategy is a design judgement)
- Verdict: **delegate** (not Lead-doable)

## Waves

### Wave 1: <one-line goal>
- UAT manner: <GUI / CLI / log / debug surface>
- UAT script:
  - given: <state>
  - when: <user action>
  - then: <observable>
  - pass: <criterion>
- Files (likely): <paths>
- Size: S/M/L
- blocked-by: none / Wave X / unmerged Y

### Wave 2: ...

## ADR plan
- ADR-NNNN: <title> (covers Wave 1, 3)
- ADR-MMMM: <title> (covers Wave 2)

## Flag mapping
- Wave 1, 2, 3 → LIMN_FEAT_FOO (hidden)
- Wave 4, 5 → LIMN_FEAT_BAR (hidden)
- Promotion: after Wave 5 merges, promote LIMN_FEAT_FOO to experimental

## Hand-off
- Wave 1: $propose-adr → $review-design → architect / fullstack-engineer / reviewer / $finish-task
- Wave 2: ...
```

## Stop condition

- Slice plan が書かれ、すべての wave が有効な UAT スクリプトを持ち、ADR/flag マッピングが明示され、hand-off チェーンが記録されている。

## Boundary

- ユーザーには見えない deliverable の wave を **書かない**。基盤作業は付属の検証 surface がある場合のみ OK。
- wave マージから flag 昇格を **自動導出しない**。Flag 昇格はプロダクト判断。
- 外部コントリビューターに本 skill を **強制しない**。これは Lead のワークフロー。コントリビューターの PR は対象プロジェクトの `CONTRIBUTING.md` に従う。
- 複数の異なる判断を 1 つの ADR にまとめ**ない**。ADR 1 つ = 判断 1 つ (= プロジェクトの `$propose-adr` Boundary を参照)。
- Step 2-2 のオプションを適用してもまだ UAT 不能 wave が残る場合は **Stop**。
- Step 1-1 でユーザー向け変化を特定するにはリクエストが曖昧すぎる場合は **Stop**。
- **main (= 既定ブランチ) で実装を開始したら即 Stop して branch を切り直す**。 Wave 1 のコードを 1 行でも main に書き始めた時点で、 hand-off chain が破綻している。 `git checkout -b feat/<topic>` で feature branch を切ってから resume する。
- **Issue コメントを過剰投稿しない** (= 「📋 着手 Plan」 は slice plan 1 回のみ、 「🔄 Plan 更新」 は plan 変動時のみ)。 done / in-progress の単純進行では投稿しない。
- **再スライスによる 「🔄 Plan 更新」 は本 skill が投稿する担当**。 同一イベントで `$wave-status` 側が再投稿しないよう責務分離する (= 二重投稿排除、 Progress tracking 参照)。
- **backlog 以外の project では Issue コメントを投稿しない**。 投稿先は `sat0-hir0/backlog` 固定。 投稿は Step 3-4 の「題材 Issue 同定フロー」1-2 が確定した場合、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ。 過去 context に偶然 `#N` があるだけ (= フロー 4) では投稿しない (= 誤爆防止)。 フロー 3 で有人なら 3 択 surface、 無人なら session pause。

## Helper

本 skill はオーケストレーション専用。スクリプトはない。Slice plan は Lead (= 本 skill を呼び出すモデル) が書き、ホストプロジェクトの慣習に従ってメモやセッション記録に保存する。

ホストプロジェクトにセッション記録の慣習がある場合 (= 例: Limn の `.skillshare/records/sessions/<date>.md`)、そこに slice plan を追記する。なければ、最終メッセージとして slice plan を返す。

## Final Report

上記テンプレートで slice plan を返す。Lead はそのまま Wave 1 の hand-off に進む (= プロジェクトのチェーンに従って `$propose-adr` 等を呼び出す)。

Plan が書けたら、`$wave-status` (= 兄弟 skill) で進捗トラッキングを登録する。ステータスファイル (`~/.claude/state/slice-<feature>.md` またはプロジェクト固有のパス) が wave のチェックボックスを持ち、`$wave-status` が wave マージのたびに更新する。

## Worked example: ディレクトリツリーフィーチャー (= VSCode Explorer 風サイドバー)

実際の Limn フィーチャーの完全な slice plan。エンド・ツー・エンド。

> **Note**: これは Rust + gpui project (= Limn) の一例。 別言語 / 別 framework の project では各層 (= layer 境界 / I/O ownership / threading 制約 / round-trip 不変条件 等) をその project の制約に読み替える。 構造 (= 7 wave、 dump CLI による UAT、 ADR 数、 flag mapping) は移植可能だが、 path / crate 名 / verifier 名 / dependency は project 固有。

### Request (1 sentence)
Add a left-sidebar tree of the workspace, click-to-open, gitignore-aware, async-scanned.

### Constraints
- limn-core is std-only (= ADR-0002).
- limn-service owns vault I/O; the new walker must live there.
- limn-ui must not call std::fs directly.
- gpui main thread must not block on filesystem walk.
- Markdown round-trip unchanged (= not touched).

### Evaluation
| Dimension | Value |
|---|---|
| Size | L |
| Difficulty | new-invention (= async walker) + reuse (= Vault::open_path) |
| Impact scope | public-behaviour (= CLI arg meaning changes; new pub mod) |
| New dependencies | +2 (= `ignore` MIT/Unlicense, `async-channel` MIT/Apache-2.0) |
| Verifier coverage | `<project's verifier suite>` (= 例: layer 境界 / std-only / threading / file-sandbox / ADR-required / license-containment 等、 project の `scripts/` または CI で定義されているもの) |

### Lead 単独着手の可否
- (1) ≤1 file: NG (= 5+ files)
- (2) no public-behaviour change: NG (= new CLI semantics + new pub mod)
- (3) fix is obvious: NG (= async strategy is a design judgement)
- Verdict: **delegate** (not Lead-doable)

### Waves (= 7 thin slices)

#### Wave 1: Walker + dump CLI (基盤、デバッグ surface による UAT)
- UAT: `cargo run --example dump-walk ./docs` が見つかった `.md` とディレクトリをすべて出力する
- pass: 既知ファイルがすべて現れ、.git/ がデフォルトで除外される
- Files: `crates/limn-service/src/vault/explorer.rs`, `crates/limn-service/examples/dump-walk.rs`
- Size: S
- blocked-by: none

#### Wave 2: サイドバー UI シェル (= 空ツリーを描画)
- UAT: `cargo run -p limn-ui -- ./docs` で左ペインが表示される (空でも可)
- pass: 左カラムが 260 px で見えた状態でウィンドウが開く
- Files: `crates/limn-ui/src/sidebar.rs`, `crates/limn-ui/src/root_view.rs`
- Size: S
- blocked-by: none (Wave 1 と並列)

#### Wave 3: Walker → サイドバー配線 (= ツリーにファイルを表示)
- UAT: 同じ起動でツリーにファイルが表示される (= 未ソート、フラット)
- pass: 既知ファイルがサイドバーに見える
- Size: S
- blocked-by: Wave 1, Wave 2

#### Wave 4: フォールディング (= ▸/▾)
- UAT: フォルダ行をクリック → 子が隠れる; 再度クリック → 再表示
- pass: クリックで表示が切り替わる
- Size: S
- blocked-by: Wave 3

#### Wave 5: クリックして開く (= エディタ入れ替え)
- UAT: .md 行をクリック → 右ペインにそのファイルが表示される
- pass: タイトルと内容が一致する
- Size: S
- blocked-by: Wave 3

#### Wave 6: Gitignore + 非 md ファイル
- UAT: `.gitignore` に載ったエントリが除外される; 非 .md ファイルは disabled スタイルで表示される
- pass: secret.txt が消え、image.png がグレーアウト表示される
- Size: M
- blocked-by: Wave 1

#### Wave 7: 非同期ノンブロッキングスキャン (= 1000+ ファイル)
- UAT: 大規模ワークスペースを開いてもスキャン中に UI がフリーズしない; 行がインクリメンタルに出現する
- pass: ウォーカー実行中もウィンドウがインタラクティブであり続ける
- Size: M
- blocked-by: Wave 3

### ADR plan
- ADR-NNNN: "Add sidebar and confine explorer to vault module" (covers Wave 1, 2, 3)
- ADR-MMMM: "Stream explorer results via async channel" (covers Wave 7)

### Flag mapping
- Wave 1-7 → `LIMN_FEAT_SIDEBAR` (stage 1: hidden)
- Promotion: Wave 5 がマージされたら (= サイドバーがエンドツーエンドで使える状態) LIMN_FEAT_SIDEBAR を stage 2 (experimental) に昇格。
- Wave 7 の polish は hidden→experimental の enabler であり、それ自体の昇格ではない。

### Hand-off (= wave ごとのチェーン)

**Wave 1 着手前**: `git checkout -b feat/sidebar-tree` (= project の git-strategy.md の規約に従う)。 main で直接実装を始めない。

各 wave は同じチェーンを走る。スコープがラウンドごとに小さくなるだけ:

```
$propose-adr   (新規 ADR を導入する wave のみ; ここでは Wave 1 と Wave 7)
  ↓
$review-design (独立したレビュアーエージェント)
  ↓
$start-task    (この wave のスコープベースラインを固定)
  ↓
architect      (read-only 設計ブラッシュアップ、小規模 wave ではオプション)
  ↓
fullstack-engineer (実装)
  ↓
reviewer + qa-verifier (独立した検証)
  ↓
$finish-task   (ディスパッチャー + 監査ゲート)
  ↓
git commit     (Conventional Commits、 各 wave 完了で 1 commit)
  ↓
$wave-status mark Wave N done
```

新規 ADR のない wave は最初の 2 ステップをスキップ。スコープが小さい wave は `architect` をスキップ。

**全 wave 完了後**: `git push -u origin feat/sidebar-tree` を実行、 PR 作成は user に依頼する (= autonomous mode で 「PR まで作って」 と明示されない限り、 PR 作成は user の最終 review ステップとして残す)。

### Step 3-4: Issue コメント投稿 (= 「📋 着手 Plan」、 backlog harness 経由時のみ)

#### 投稿目的

本 skill が Issue にコメントする目的は 2 つ:
(1) **透明性担保**: Lead が下した slice plan 確定 / Plan 更新の判断を、 session がリセットされても追えるようにする。
(2) **作業・判断履歴担保**: wave 構成 / ADR 起票 / dropped 判断など、 Issue を見るだけで判断の流れが分かる状態を保つ。

**投稿価値のある判断 (= 投稿対象イベント)**:
- slice plan 生成 (= 新規 wave 構成の確定)
- Plan 更新 (= wave の追加 / dropped / blocked / 順序変更)
- ADR 起票判断 (= Proposed 起票を決定した事実)
- Wave 着手判断の根拠 (= 計画外の判断が発生した場合のみ)

**投稿しないイベント**:
- done / in-progress への単純進行マーク (= `$wave-status` 側の責務)
- 計画通りに次 wave へ進む行為

**題材 Issue の同定 (= 投稿先決定フロー)**:

以下を順に確認し、 最初に確定したものを投稿先とする:

1. `$issue-execute` の hand-off プロンプトに Issue 番号とリポジトリ名が明示注入されている → そのまま `<N>` / `sat0-hir0/backlog` を使う (= 最高信頼度)。
2. ユーザーが当該 session で「#N」「Issue N」「backlog#N」等を明示的に言及しており、 かつ対象が `sat0-hir0/backlog` であることが文脈から確定している → そのまま `<N>` / `sat0-hir0/backlog` を使う (= 高信頼度)。
3. session の直前の発話に Issue 番号はあるが、 リポジトリが確定していない → 有人なら 3 択を surface: (a) 新規 Issue を起票して投稿 / (b) 既存 Issue に投稿 (番号を指定) / (c) 今回は残さない。 無人 (= ultra-autonomous / `$issue-execute` で人間不在) なら session pause して「題材 Issue が確定していません。 Issue 番号 / リポジトリを明示してから再開してください。」を記録して終了。
4. 過去 context に偶然 `#N` 文字列が混入しているだけで、 明示的言及がない → **投稿しない** (= 誤爆防止)。
5. Issue 番号が存在しない → **投稿しない**。

フロー 1-2 が確定、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ投稿を実行する。 投稿先リポジトリは `sat0-hir0/backlog` 固定。 他リポジトリへは投稿しない。

posture: **user に明示的に「不要」 と言われない限り、 投稿価値のある判断は投稿 / 立ち戻りを行う** (= デフォルトは投稿側に倒す、 沈黙すると判断が消える)。

**3 択 (c) 「今回は残さない」 を選んだ場合の session 内記録**: surface 直後の chat に Lead が以下の 1 行 log を必ず出す (= 履歴担保の最低保証):

> 📝 透明性 / 履歴担保の放棄を user が許容 (= 判断「<1 行要約>」を Issue に残さない選択)。 session 内のみで完結。

これにより、 (c) を選んだ事実そのものが session 内に残る (= 後から「なぜ Issue に紐付けなかったか」 が追える)。

**「計画外の判断」 の定義 (= escape valve、 過剰 surface 防止)**:
- ✅ 投稿対象: wave 分割 / ADR 起票判断 / wave 構成変動 (= dropped / blocked / 追加 / 順序変更) / scope 逸脱判断 のような **構造的判断**。
- ❌ 投稿対象外: mid-implementation の些末判断 (= lint fix / typo 修正 / test 1 件追加 / 関数名 rename / git commit メッセージ調整 等)。 これらは「計画外」 ではなく「計画内の通常進行」。

**無人実行時の Lead 独断禁止 原則**: 無人 (= ultra-autonomous / cron heartbeat / `$issue-execute` で人間不在) では、 Lead が以下を **絶対に独断で行わない**:
- 題材 Issue 不明時に自動で `$issue-from-idea` を呼んで新規 Issue を起こす (= 透明性 / 履歴担保の放棄を AI 単独で決めるのは原則違反)。
- 「曖昧だから今回はスキップしておこう」 と投稿を黙って省略する (= 沈黙は最悪の選択肢)。

代わりに session pause + surface message「題材 Issue 未確定」 を記録して session を終了する。 透明性 / 履歴担保の放棄は user 判断専属。

slice plan を生成し終え、 `$wave-status init` でステータスファイルをシードするのと **同タイミング** (= Phase 3 末尾) で、 着手時点の Plan を Issue に 1 回だけコメントする。 session が途中で死んでも Issue コメントだけ追えば最新の Plan / Wave 構成 / 進捗地点が分かる状態にするため。

- **既存の 「🤖 session 開始」 コメント (= `$issue-execute` が投稿、 branch/worktree/session 証跡専用) とは別コメント**。 二重投稿しない。 着手 Plan は plan 生成後の独立したコメント。
- **slice plan 1 回のみ**。 re-slice (= 再スライス) は新規投稿せず 「🔄 Plan 更新」 コメント (= Progress tracking 参照) で扱う。

```bash
gh issue comment <N> --repo sat0-hir0/backlog --body "<comment>"
```

コメント本文テンプレート:

```markdown
📋 着手 Plan

## Waves (= slice 構成)
- [ ] Wave 1: <一行ゴール> — blocked-by: none
- [ ] Wave 2: <一行ゴール> — blocked-by: Wave 1
- ...

## Agent chain (= 各 wave で回す)
- $propose-adr → $review-design → architect / fullstack-engineer → reviewer + qa-verifier → $finish-task
- (= 新規 ADR のない wave は最初の 2 step をスキップ)

## Execution mode
- ultra-autonomous (= 無人時は計画承認ゲートを自動 proceed、 全 wave 走破後に $prepare-uat)
- または通常 (= wave 完了ごとに surface)

## ADR plan
- ADR-NNNN: <title> (covers Wave 1, 3) — Proposed
- (= 無ければ 「なし」)

## wave-status
- file: ~/.claude/state/slice-<feature>.md (= 進捗の SSOT)
```

## Project connection (= 実際のリポジトリへの組み込み方)

本 skill はベンダー中立・プロジェクト中立。特定のプロジェクトに組み込むには、Lead がプロジェクトの既存チェーン skill (= `$propose-adr` / `$start-task` / `$review-pr` / `$finish-task` 等) を選んで、上記の wave ごと hand-off にはめ込む。

### Project 固有 mapping は project 側で持つ

本 skill (= personal global) には project 固有の skill 名 / agent 名 / verifier 名を直書きしない。 各 project の `.skillshare/skills/` (= または project の harness 配置) で:

- どの project skill が本 skill の `$propose-adr` / `$start-task` / `$review-pr` / `$finish-task` スロットを埋めるか
- どの agent (`architect` / `fullstack-engineer` / `reviewer` / `qa-verifier` 等) を呼ぶか
- どの verifier が `scripts/` または CI で発火するか

を project 個別に定義する。 Lead は session 開始時に project の `AGENTS.md` / `.skillshare/HARNESS.md` 等を読んで mapping を把握する。

### ハーネスがまだない project の場合

ホストプロジェクトに skill チェーンがない場合、Lead は各 wave を通常の PR サイクルとして処理する (= コードを書く → push → レビュー → マージ)。Slice plan は引き続き wave 境界を示す。Hand-off チェーンは「wave ごとに implement → commit → (全 wave 後に) push → PR」に集約される。 branch / push / PR 戦略 (= Step 3-3) はハーネスの有無に関わらず適用する。

## Autonomous mode (= ざっくり指示で勝手に回す)

ユーザーが 1 行のリクエストを渡し、ステップごとの承認なしにスライシングを進めてほしい場合、本 skill を autonomous mode で動かす:

1. Phase 1-3 を確認なしで実行する。
2. 計画を 1 度だけ全文 surface し、確認を 1 回取る: 「この計画で: proceed / revise / abort」。
3. `proceed` を受けたら、Lead は hand-off チェーン経由で wave ごとに実行し、wave 完了時のみ surface する (= wave 完了を報告し「次の wave へ / pause」を確認)。
4. Autonomous mode でも有効な **Stop conditions**:
   - Phase 1-1 でユーザー向け変化を特定できない → 確認の質問を 1 つだけ聞く。
   - Phase 2-2 でマージとデバッグ surface の両オプションを使い果たしても UAT 不能 wave が残る → ユーザーに surface する。
   - Wave 検証が 2 回連続で失敗 → ユーザーに surface する。
   - 計画になかった新規 ADR が wave の途中で必要になる → ユーザーに surface する。

ユーザーはどの wave 境界でも「pause」または「revise plan」で上書きできる。

## Ultra-autonomous mode (= wave 完了通知も出さず全走破)

通常 autonomous mode は wave 境界ごとに surface して 「次の wave へ / pause」 を確認する。 これは安全側の default だが、 仕様が明確で設計判断が少ない task では報告と承認の往復が冗長になる。 そのような task では ultra-autonomous mode で動かす:

1. Phase 1-3 を確認なしで実行する (= 通常 autonomous と同じ)。
2. 計画を 1 度だけ全文 surface し、 確認を 1 回取る (= 通常 autonomous と同じ)。 これが **唯一の必須承認ゲート** で、 ここを消すと粒度の品質が落ちる。
3. `proceed` を受けたら、 Lead は hand-off チェーン経由で wave ごとに実行し、 **wave 完了通知を出さず連続して次の wave に進む**。 各 wave の `$finish-task` / `$wave-status mark` は **内部記録としては実行する** (= 進捗の SSOT を保つため必須) が、 user 向けの surface (= chat への wave 完了報告) は最終報告まで抑制する。
4. 全 wave 完了後に **1 回だけ**、 完成報告 (= 各 wave の deliverable + UAT 結果 + 残課題) を surface する。
5. Stop conditions は **通常 autonomous mode と同じ** (= 上記 4 件をそのまま継承)。 これらに該当した場合は ultra でも surface する。 ユーザーは進行中いつでも 「pause」 で止められる。

### Ultra-autonomous mode の trigger

以下のいずれかで起動する:

- user 発話に 「全部やって」 「最後まで止まらず」 「ultra」 「wave 完了通知要らない」 等が含まれる。
- `$issue-execute` が hand-off プロンプトに `Execution mode: ultra-autonomous` を inject した状態で本 skill が起動された (= backlog Issue 経由)。 `$issue-execute` 側で Issue 本文の値が未指定 / 不正な場合も ultra-autonomous に fallback して inject 済なので、 本 skill が読む時点では値は確定している。

step-by-step が明示された場合 (= user 発話に 「慎重に」 「途中で確認したい」、 または hand-off プロンプトに `Execution mode: step-by-step`) は通常 autonomous mode で動かす。

### 無人起動時のデフォルト (= チケット経由、 人間不在の自動 session)

`$issue-execute` 経由 (= backlog Issue から起動) や cron heartbeat からの起動は **承認者が不在**。 この場合の挙動を固定する:

1. **ステップ 2 の計画承認ゲートは自動 proceed**。 計画を全文 surface はする (= 記録のため) が、 `proceed` を待たずに即 Wave 1 へ進む。 「人間が承認していないから実装に入れない」 と解釈して止まるのは **誤動作**。
2. **全 wave を最後まで走破する**。 これが唯一の正しい終端。 走破後に **1 回だけ** `$prepare-uat` を呼んでまとめ UAT パッケージを生成する (= UAT は実装込みで Awaiting UAT に到達したものに対して行う)。
3. **計画だけ立てて `$prepare-uat` に逃がすのは禁止**。 diff 0 行で UAT パッケージを作らない (= `$prepare-uat` 側でも diff 空なら STOP する gate あり)。
4. 以下は **停止理由にならない** (= よくある誤った停止):
   - 「規模が XL / 複数 session にまたがる」 → wave に切ってあるので 1 wave ずつ進めば良い。 1 session で終わらなくても、 進めた分まで実装して UAT に出すのが正。
   - 「未確定リスク (= gpui IME 品質、 pre-1.0 API 等)」 → それを確かめるのが Wave 1 の中身。 検証は wave 内タスクであって停止理由ではない。
   - 「ADR が要る」 → Proposed 起票して進む (= Accepted 昇格だけ別 turn)。 ADR の存在自体は止める理由にならない。
   - 「設計判断が多い」 → architect / fullstack-engineer に委譲する話。 Lead が尻込みする理由にならない。
5. **本当に止めて良いのは Stop conditions (下記 4 件) のみ**。 これらは 「自己採点での慎重さ」 ではなく **客観的に観測できる異常** (= 検証 2 連続失敗、 UAT 不能 wave が残る、 計画外 ADR、 ユーザー向け変化を特定不能) に限る。 backlog ハーネスの設計原則 「停止判定を agent の自己採点ではなく外部で行う (= Out-of-process supervisor)」 に従い、 Lead が主観で 「大変そうだから計画で止めよう」 と判断するのは禁止。

> ⚠️ Stop conditions の 「計画になかった新規 ADR が wave の途中で必要になる」 は、 **計画段階で予見済みの ADR には該当しない** (= 予見済みは Proposed 起票して進む)。 「途中で初めて判明した、 計画になかった」 ADR だけが停止トリガー。

## Progress tracking

Wave のステータスは兄弟 skill の `$wave-status` が永続化する。本 skill の Phase 3 が計画を書いたら、`$wave-status init <feature>` を呼んでステータスファイルをシードする。各 wave がマージされるたびに `$wave-status mark <feature> wave-N done` を呼ぶ。ステータスファイルがセッションをまたいだ「今どこにいるか」の唯一の正解 (single source of truth)。

### wave 構成変動時の Issue コメント (= 「🔄 Plan 更新」、 backlog harness 経由時のみ)

**再スライス (= 本 skill の再呼び出しによる wave 構成変更) は、 本 skill が 「🔄 Plan 更新」 コメントを投稿する担当**。 再スライスで wave の追加 / dropped / blocked / 順序変更が起きたとき、 本 skill が 1 回投稿する。 session 透明性のため、 Plan の変動は Issue コメントから追える状態にする。

- **二重投稿の排除 (= 責務分離)**: 再スライス経由で `$wave-status mark` が wave を dropped/blocked に変更しても、 **`$wave-status` 側は投稿しない** (= 本 skill が投稿済み、 wave-status SKILL.md Step 2-3 参照)。 逆に `$wave-status` を直接 mark する操作 (= 再スライスを経ない単独の dropped/blocked/追加) では `$wave-status` 側が投稿する。
- **投稿条件**: 上記「Step 3-4 題材 Issue の同定フロー」の 1-2 が確定、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ投稿する (= 同定フロー共通)。 無人実行でフロー 3 に該当した場合は session pause (= 投稿しない)。 フロー 4-5 は投稿しない。
- **plan 変動イベント 1 回 1 コメント**。 done / in-progress の単純進行 (= wave が予定通り進んだだけ) では **投稿しない** (= 過剰投稿防止)。

```bash
gh issue comment <N> --repo sat0-hir0/backlog --body "🔄 Plan 更新

## 変更点
- Wave N を dropped (= 理由: ...)
- Wave M を追加 (= ...)
- 順序変更: ...

## 更新後の Waves
- [x] Wave 1: <goal> — done
- [~] Wave 2: <goal> — in-progress
- ...
"
```
