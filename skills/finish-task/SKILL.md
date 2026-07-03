---
name: finish-task
description: ALWAYS invoke before reporting "done" / "完了" / "終わった" / "PR 作る" / "merge" / "ship" on any delegate-single or delegate-slice task, or any wave that produced files. Triggers include Japanese phrasings like 「完了報告」「終わったよ」「タスク終わった」「まとめて」「PR 作る前にまとめて」「report を出して」, English phrasings like "report done", "task complete", "wrap this up", "summarize what's done", "PR-ready report". Generates a single structured completion report integrating spec coverage, UAT scripts, evidence artifacts, unresolved items, and AI usage disclosure. Separates claim (= what was done) from proof (= evidence). Merges former uat-script + evidence-collection + completion-report into one workflow. SKIP only when the verdict was Lead-direct AND no files were changed (= pure-info / read-only sessions).
---

# Finish task

## Use when

- wave (= $task-slicing の出力) または single-PR タスクが終盤に差し掛かり、エージェントが "done" を報告しようとしているとき。
- プロジェクト側の `$task-completion` を呼ぶ前 (= プロジェクトにあれば)、または commit/push の前 (= ない場合)。
- 変更がユーザー向け挙動に触れており、その変更が diff から自明でないとき。
- メンテナが PR description 用の構造化 artifact を手元で作りたいとき。

変更がユーザーに不可視 かつ タスクが純粋な Lead-direct (= 機械的な trivial 編集) の場合のみスキップしてよい。それ以外はこの skill が最終ゲートとなる。

## Why this skill exists

**claim-vs-proof の分離** が業界で収束点となっている (= Cline `submit_review` の型安全Completion Check / addyosmani「done は主張であり証明ではない」/ openclaw の Evidence セクション / Kubernetes UNRESOLVED マーカー / k8s release-note の構造化フィールド / Atlassian DoD known issues / polars + deno の AI usage disclosure)。ユーザーは「X をやった、Y をやった、Z をやった」という散文の代わりに、1 つの構造化 artifact を読む。主張の hallucination は「証拠が添付されていない」という形で表面化する。

AI 完了報告で最も多い失敗パターン: **証拠のない claim と、散文に埋もれた unresolved items**。この skill は 3 つの関心事を 1 つのワークフローに統合することで、構造的にその両方を防ぐ。

1. **何が起こるべきだったか** (= spec coverage、UAT スクリプト) — uat-script lineage
2. **何が実際に証明されたか** (= テスト出力、ログ、スクリーンショット、コマンド記録) — evidence-collection lineage
3. **何が残ったか** (= TODO、ignore テスト、スコープ逸脱、先送り項目) — completion-report lineage

統合により 3-skill チェーン (= 旧来の `$uat-script → $evidence-collection → $completion-report`) がなくなり、エージェントが 1 つのレポートを出力できる。

## Contract

- すべての spec 項目に `achieved` / `partial` / `abandoned` / `blocked-by-harness` のいずれかのラベルを付ける。
- `achieved` と主張するものは、evidence artifact を最低 1 件添付する。
- ユーザー向け変更には、UAT 基準を最低 1 件用意する (= Given/When/Then、binary pass、30 秒で再現可能)。
- `TODO`, `FIXME`, `#[ignore]`, `xfail`, 先送り項目、「後でやる」という記述 — すべて網羅的に列挙するか、`NONE` と明示する。沈黙は許可しない。
- AI usage disclosure を必ず記載する (= polars / deno の慣例)。
- evidence の種類は許可リストに限定する (= 「確認した」という自由形式の文言は不可)。

## Phase 1: Spec coverage

### Step 1-1: 元の spec を列挙する

- **読む**: タスク記述 (= 元のプロンプト、wave goal の精緻版、実装対象の ADR)。エージェントが届けると約束したものすべて。
- **出力**: 番号付きの spec 項目リスト。

### Step 1-2: 各項目にラベルを付ける

各 spec 項目に対して、以下のうち 1 つだけ:

- **achieved** — 実装済みかつ証拠あり。実装の `file:line` を引用する。
- **partial** — 不完全な実装。ギャップを 1 文で述べる。
- **abandoned** — 実装しないと判断した。理由を 1 文で述べる。
- **blocked-by-harness** — 試みたが verifier が拒否した。verifier 名と検出内容を引用する。

ラベルなし項目は禁止。ラベルがない = エージェントがそれを出荷したかどうか分からない。ユーザーに上げること。

## Phase 2: UAT scripts (= ユーザー向け変更のみ)

`achieved` または `partial` の spec 項目のうち、ユーザー向け挙動に触れるものについて、Given/When/Then の UAT 基準を書く。spec 項目がどれもユーザー向けでない場合 (= 純粋なリファクタ、doc-only、test-only) は、このフェーズ全体をスキップする。

**`$task-slicing` の slice plan に UAT が既にある場合**: 二度書きしない。 slice plan の UAT を実機 evidence で裏付けるのが本 Phase の仕事。 追加サーフェスが見つかったとき (= 実装中に増えた wave 外要素) だけ新しい UAT 基準を足す。 粒度: slice plan の UAT は wave-level (= 1 wave = 1 UAT)、 本 Phase の UAT は surface-level (= 1 GUI / CLI / log 行 = 1 UAT) なので、 同じ wave 内で複数 UAT になることはありうる。

### Step 2-1: ユーザー向けのサーフェスを列挙する

- **判断する**: 変更でユーザーに観測可能になるサーフェスを全部列挙する。GUI 要素 / CLI 呼び出し / ログ行 / ファイル出力 / 設定エントリ。
- **ルール**: 1 サーフェス = 1 UAT 基準。「クリックして観察してログを読んでファイルを検証する」を 1 つにまとめない。分割する。

### Step 2-2: Given / When / Then / Pass / Evidence を書く

各基準について:

- **Given** — ユーザーがシステムを置かなければならない開始状態。具体的なコマンド、「起動している」ではない。
- **When** — 挙動を引き起こすユーザーの操作。具体的なキー入力 / コマンド、「サイドバーを使う」ではない。
- **Then** — 観測可能な結果を 1 文で。具体的な観察、「動く」ではない。
- **Pass** — 1 文の binary 判定基準。二人の合理的な人が判定に異論を持てないこと。
- **Evidence** — エージェントが生成できる evidence の種類を最低 1 つ (= Phase 3 カタログ参照)。

### Step 2-3: 30 秒 / binary / evidence テスト

- **30 秒テスト**: Given/When/Then を声に出して読む。初見のユーザーが 30 秒で再現できること。できなければ書き直すか `requires-human-input` として上げる。
- **binary テスト**: 「二人の合理的な人がこれの合否で意見が分かれる可能性があるか?」と問う。あれば書き直す。
- **evidence テスト**: エージェントは実際にその artifact を生成したか? 生成せずに主張している場合は `not-yet-collected` とマークしてユーザーに上げる。

## Phase 3: Evidence

### Step 3-1: 各 claim を分類する

Phase 1 と Phase 2 の各 claim について、合致する evidence の種類を選ぶ:

- **test-output** — `cargo test --workspace` の抜粋、新しいテスト名
- **command-output** — CLI 呼び出しの短い記録
- **log** — エージェントが実行中に書いたファイルのパス
- **screenshot** — 画像へのパス (= GUI 変更)
- **diff-line** — コードが存在することを証明する `file:line` 参照
- **harness-output** — `$pr-review.sh` やその verifier の終了コード + 簡潔な出力
- **not-yet-collected** — 明示的な「ユーザーが実行する必要がある」

合致する種類がない claim は、検証可能な claim ではない。`claim-without-evidence` として上げる。

### Step 3-2: artifact を生成する

エージェント側で生成可能な種類の artifact について:

- **test-output**: テストを実行し、テスト名 + 標準出力の 5 行抜粋を取得する。
- **command-output**: コマンドを実行し、終了コード + 10 行抜粋を取得する。
- **log**: 引用したパスにログファイルが存在することを確認し、先頭 10 行を引用する。
- **harness-output**: 関連する verifier またはディスパッチャを実行し、終了コード + サマリを取得する。
- **diff-line**: `git diff` で対象の file:line が現在の diff に存在することを確認する。

### Step 3-3: ユーザーだけが生成できるものは委ねる

- **OS レベルの UI のスクリーンショット** (= IME、HiDPI、実 GPU) → `not-yet-collected`、起動コマンドを添付する。
- **手動での確認** (= 「Ctrl+P を押してパレットを確認する」) → `not-yet-collected`、手順を添付する。
- **物理ハードウェア** (= 特定のモニタ、特定の入力デバイス) → `not-yet-collected`。

エージェントが生成していない artifact は **絶対に主張しない**。テストを実行できなかった場合、evidence は `not-yet-collected` であり、`done` ではない。

## Phase 4: Unresolved items (= 必須 grep)

Kubernetes UNRESOLVED マーカー + Atlassian DoD known issues に倣う。沈黙は「確認しなかった」とみなす。grep して何もなければ `NONE` と明示する。

grep の対象は 5 種類: (1) TODO / FIXME (Step 4-1)、 (2) `#[ignore]` / xfail (Step 4-2)、 (3) スコープ逸脱 (Step 4-3)、 (4) 先送り項目 (Step 4-4)、 (5) 将来予定 / Wave 名 / 拡張予定 の混入 (Step 4-5)。 すべて沈黙不可。

### Step 4-1: TODO / FIXME を grep する

- **実行**: 今回の変更で追加された `TODO|FIXME|XXX|HACK` の文字列を `git diff` で検索する。
- **出力**: `file:line` ですべての一致を列挙する。なければ `NONE`。

### Step 4-2: ignore テストを grep する

- **実行**: 今回の変更で追加または変更された `#[ignore]`, `xfail`, `skip:`, `pytest.mark.skip` を探す。
- **出力**: すべての一致を列挙する。なければ `NONE`。

### Step 4-3: スコープ逸脱を列挙する

- **slice plan (= $task-slicing の出力) 対比**: 実装途中で再交渉した wave goal はあるか?
- **ADR 対比**: ADR に記載されているが実装されなかった決定はあるか?
- **出力**: 各逸脱を `from → to` 形式で列挙する。なければ `NONE`。

### Step 4-4: 先送り項目を列挙する

- **元の spec 対比**: 明示的に先送りにしたもの。 ただし **先送り先は必ず repo 外の永続的な置き場** (= GitHub Issue URL / GitHub Project URL / ROADMAP.md セクション名) を **必須記載**。 「M2 で対応」 「次の wave で」 「Phase 2 で再評価」 のような **repo 内の slice 番号 / 将来時制で書かない** (= 詳細は Phase 4-5 参照)。
- **出力**: `item` (= 先送り対象、 present-fact のみ) + `moved_to` (= URL or ROADMAP.md パス) のペアで列挙する。 なければ `NONE`。

### Step 4-5: 将来予定 / マイルストーン / 拡張予定 の混入を grep する

`$task-routing` Boundary の 「将来予定を書かない」 ルール (= 全 agent 遵守 + reviewer 系 agent 指摘対象) に基づく出口側の最終チェック。 sibling skill (= `$task-routing`) の規定を本 skill で再掲はしないので、 ルール本文と背景はそちらを参照。 ここでは grep と表面化だけを行う。

- **実行 (= 推奨経路: script)**: vendor 配下の `scripts/check-future-plans.py` を実行する (= 検出パターン + 除外ロジック + 自己参照除外を実装、 標準ライブラリのみ依存、 OS / vendor 非依存、 untracked file も default scan に含む)。 各 AI CLI vendor の skill ディレクトリと同じ階層に `scripts/` が配置される (= `~/.claude/scripts/`、 `~/.codex/scripts/`、 `~/.cursor/scripts/`、 `~/.gemini/scripts/`、 `~/.agents/scripts/`)。 配置は skillshare extras 経由で harness repo の `scripts/` を各 vendor に sync する (= 配置原則の詳細は [`docs/script-placement.md`](../../docs/script-placement.md) 参照)。

  **agent は自分が動いている vendor の path を選んで呼ぶ** (= Claude Code なら `~/.claude/scripts/`、 Codex なら `~/.codex/scripts/`、 Cursor なら `~/.cursor/scripts/`、 Gemini / antigravity なら `~/.gemini/scripts/`、 universal なら `~/.agents/scripts/`)。 vendor 判定は agent 自身の自己認識 (= 起動 binary 名 / cwd / 環境変数) から行う。

  ```bash
  # 例: Claude Code から実行する場合 (= 他 vendor は path の `.claude` を該当 dir に置換)
  python ~/.claude/scripts/check-future-plans.py            # HEAD vs working tree (+ untracked)
  python ~/.claude/scripts/check-future-plans.py --base main # main..HEAD
  python ~/.claude/scripts/check-future-plans.py --json     # YAML 投入用
  ```

  exit code: `0` = 違反なし、 `1` = 違反検出 (= 行と category を stdout に列挙)、 `2` = invocation 失敗。

  vendor の `scripts/` が無い場合 (= skillshare extras 未設定 / 別環境) の 2 段 fallback:
  1. harness repo が clone 済 (= `~/code/harness/` 等) なら `python ~/code/harness/scripts/check-future-plans.py` を直接呼ぶ
  2. それも無い場合は下記 fallback (= 手動 grep) に落とす

- **実行 (= 非 diff artifact の scan)**: script は `git diff` ベースなので **commit message / PR body** には届かない。 一方 `$task-routing` Boundary はこれらも禁止対象としている。 finish-task では追加で以下を agent 側で手動 check する (= 短いので grep 不要、 目視 / 簡易 regex でよい):
  - **直近 commit message** (= `git log -1 --format=%B HEAD`): 違反 string が混入していないか
  - **PR body** (= 起票予定の本文 or 既存 PR の場合は `gh pr view`): 同上
  - 違反検出時は `unresolved.future_plans_in_artifacts` に `category: <…>` + `file: commit-message@<sha>` or `file: pr-body@<num>` 形式で記録

- **実行 (= fallback: 手動 grep)**: script が使えない環境では agent が以下の文字列パターンを `git diff` 上で手動 grep する。 **検索は case-insensitive** (= `grep -i` / `rg -i`) で行う。 lowercase の `wave 6` / `phase 2` / `sprint 3` も同様に違反扱い。 ただし script 経路と同じ精度を出すには除外条件を意識する必要があるので、 可能なら script を使う。
  - **マイルストーン / Wave / Phase 名** (= 大文字小文字問わず): `M[0-9]`, `Phase [0-9]`, `Wave [0-9]`, `Sprint [0-9]` 等 (= 内部 slice 番号)。 ただし以下は除外:
    - present-fact (= 「ignored until X is implemented」)
    - Y-trace の `accepting:` 欄 (= 「wave 分割で実装期間 1 → 3 セッション」 のような受け入れる trade-off)
    - **markdown 見出し / セクション番号** (= `## Phase 1: Spec coverage` / `### Step 4-5` / `## Phase 4: Unresolved items` 等の **skill 内構造** であり、 マイルストーン commitment ではない)
    - **ルール宣言部の literal 引用** (= 本 skill / `$task-routing` 内で 「これらを検出する」 と書いている meta 説明)
    - **skill 自身の Phase / Step / Wave 構造** (= `skills/*/SKILL.md` / `skills/*/ATTRIBUTION.md` / `docs/` 配下は skill 構造の語彙として Phase / Wave を使うので scan 対象外)
  - **将来時制 commitment**: `will be`, `later wave`, `deferred to`, `is cut when`, 「M5 で再評価」, 「Phase 2 で実装」 等。
  - **拡張予定 / future-proofing**: `for future`, `extensible to`, `may add ... later`, 「将来 ... に拡張可能」, 「(and any future ...)」 等。
- **判定**: 一致を `file:line` + category (= `milestone-name` / `future-tense` / `future-proofing`) + 該当 excerpt で列挙する。 各一致について 3 択ラベルを付ける:
  - **removed**: 違反 string を削除した (= 章ごと or 該当文ごと削除、 周辺文意も整える)
  - **kept-as-present-fact**: 違反 string を **present-fact / present-state 表現に書き換えた** (= 「M5 で再評価」 → 「現在未対応」、 「will be implemented in Phase 2」 → 「not yet implemented」)
  - **escalated**: Lead が判断保留、 user に上げる
- **出力**: すべての一致を YAML `unresolved.future_plans_in_artifacts` に列挙する。 なければ `NONE`。 grep / script のいずれも実行していなければ `not-grepped` (= 沈黙 = 「確認しなかった」 とみなされる、 NONE と書く資格なし)。

なぜ Phase 4 に組み込むか: 「将来予定混入」 は TODO / FIXME と同種の **時間が経つと嘘になる残骸** (= 順番が変わる、 codename が消える、 担当が変わる)。 grep / 静的解析が効かない場所に書かれると次 session の AI が 「実装根拠」 として参照する hallucination 連鎖の温床になる (= 2026-06 limn で ARCHITECTURE.md → ADR → panic msg → `#[ignore]` reason に 28 file 汚染の実例)。 出口でも grep して残さない。

## Phase 5: AI usage disclosure

polars / deno の慣例に倣う:

- **AI を使ったか**: `yes` / `no` / `partial`。
- **どこで** (= どのファイル、どのセクション)?
- **著者が AI 生成の行を全て正確性の観点でレビューしたか**: `yes` / `no` / `partial`。

このセクションは必須。省略すること自体が指摘事項となる。

## Phase 6: Verification artifacts

Cline `submit_review` に倣う (= ユーザーは claim ではなく生の artifact を検査する):

### Step 6-1: ハーネスを実行し、終了コードを取得する

- プロジェクトにハーネスディスパッチャがある場合 (= `$pr-review.sh` 等)、実行して以下を取得する:
  - 終了コード
  - verifier ごとの pass/fail
  - タイムスタンプ
- 生出力の参照 (= パス) を含め、ユーザーが監査できるようにする。

### Step 6-2: テスト / lint / フォーマット

- `cargo test --workspace`, `cargo clippy`, `cargo fmt --check` のそれぞれで終了コード + 簡潔な結果を取得する。
- Rust 以外のプロジェクトでは、同等のゲートを実行する。

### Step 6-3: Smoke test the binary

「build が通った = 動く」 と暗黙判断しないこと。 binary (= CLI / GUI app / server 等) を持つプロジェクトでは、 build 完了後に **実際に起動するか** を agent 側で必ず試す。 これは Phase 3 の 「主張 vs 証跡」 分離の延長 — `build pass` (= compile が通った) と `runtime pass` (= 即 crash しない) は別の claim なので別の evidence として記録する。

- **CLI**: `cargo run --bin <name> -- --help` を実行し、終了コード 0 + usage 出力を取得する。 sub-command がある場合は代表的なもの 1〜2 個も叩く。
- **server**: bind までを確認し、 3〜5 秒で SIGTERM。 起動ログに panic / error がないことを確認。
- **GUI binary**: 通常は headless 環境で起動できないため、 試した記録を残しつつ evidence を `not-yet-collected` に切り替える (= 「`cargo run -p limn-ui` を試したが headless 環境のため `gpui` window 生成で失敗、 user 確認待ち」 のように **何を試して何で失敗したか** を明記)。 「user に丸投げ」 ではなく 「agent が試した結果として user 確認に委ねた」 という履歴を残す。
- **smoke test 即 crash** (= panic / segfault / 起動 1 秒以内に exit code ≠ 0) は **finish-task を停止する条件**。 build pass でも runtime pass でなければ `done` ではない。 停止して bug として上げる。

evidence type は `command-output`。 produced_by_agent は実際に起動を試したなら `yes` (= GUI で失敗しても 「試した」 という事実が evidence)、 全く試していないなら `no` + `not-yet-collected`。

### Step 6-4: Git state confirmation

完了報告は commit 内容に集中しがちだが、 branch / push / PR の状態も明示する。 ユーザーが 「で、 これどこにある?」 と聞き返さずに済むようにする。

- **branch**: `git branch --show-current` で現在の branch 名を取得する。
- **main / master で作業していたら warning**: project の git-strategy.md / CONTRIBUTING.md を読み、 直接 commit が許可されているか確認する。 規約違反の可能性があるなら report に明示し、 ユーザーの判断を仰ぐ。
- **feature branch なら OK**: push 状態を `git status -sb` で確認 (= ahead/behind カウント)。 未 push なら 「push 待ち」 と明示。
- **PR**: 既に PR が開いているなら URL を、 開いていないなら 「PR を開く必要があるか」 を report に書く。 `gh pr view` で確認可能。 push 前提のタスクで未 push なら、 当然 PR も未作成。

evidence type は `command-output`。 git 操作の結果 (= branch 名 / push 状態 / PR URL) をそのまま貼る。

## Stop condition

- 6 フェーズすべてが埋まっている。すべての spec 項目にラベルが付いている。すべての claim が evidence に裏付けられているか、明示的に `not-yet-collected` とマークされている。UAT、unresolved、AI disclosure、verification がすべて存在する。

## Boundary

- evidence なしに spec 項目を `achieved` とマークしては **いけない**。
- ユーザーが 30 秒で再現できない UAT 基準を書いては **いけない**。書き直すか上げる。
- evidence artifact なしに UAT を `done` とマークしては **いけない**。「実装した」は evidence ではない。
- artifact を捏造しては **いけない**。存在しないテスト名、書かれていないログパス、撮っていないスクリーンショットを引用する — すべて hallucination であり禁止。
- エージェントが技術的に生成できない artifact (= ディスプレイのないエージェントの GUI スクリーンショット) に `produced_by_agent: yes` とマークしては **いけない**。
- Phase 4 の grep を実行せずに「問題なし」「すべてクリーン」と書いては **いけない**。grep していなければ、知っているとは言えない。
- Phase 4-5 の future-plans grep を省略しては **いけない**。 `unresolved.future_plans_in_artifacts` を `NONE` と書くには実際に grep して結果が空であることが必要。 未実行なら `not-grepped` と明示する。
- `unresolved.deferred[].moved_to` を空 / 「次の wave」 / 「Phase 2」 等の repo 内 slice 名で埋めては **いけない**。 GitHub Issue URL / GitHub Project URL / ROADMAP.md セクション名のような repo 外の永続的な置き場を必須とする (= 詳細は `$task-routing` Boundary の 「将来予定を書かない」 参照)。
- `unresolved.deferred` のスキーマは旧 string list (= `deferred: ["Symlink follow @ Wave 6"]`) から **構造化 object list (= `[{item, moved_to}]`) に変更されている**。 過去 session の YAML record を再利用する場合は手動マイグレーションが必要 (= 旧形式は新 schema として読めない、 機械変換 tool は提供しない)。
- AI disclosure を省略しては **いけない**。AI がこの作業の一部に関与しているなら、そう言う。
- evidence を散文にまとめては **いけない**。ユーザーは構造化 artifact を読む。エージェントはそれを説明しない。
- Phase 4 のセクションにゼロ件の場合は `NONE` を明示 **しなければならない**。沈黙は「確認しなかった」とみなされる。
- 「テストを実行して通った」(= evidence) と「テストが通るだろう」(= 証拠のない claim) を区別 **しなければならない**。
- 抜粋は短く保つ **こと** (= 5〜10 行)。フルログはファイルへ。抜粋をレポートに入れる。
- spec 項目にラベルを付けられない場合は **停止**する。「エージェントは項目 N の状態を把握していない」として上げ、ユーザーに確認させる。
- claim をどの evidence 種類でも裏付けられない場合は **停止**する。`claim-without-evidence` として上げ、ユーザーに判断させる。

## Helper

この skill はオーケストレーションのみ。スクリプトはない。レポートは Lead がこの skill を呼び出し、UAT 基準を記述し、関連コマンドと取得結果を実行し、unresolved マーカーを grep し、下記の構造化 YAML を出力することで組み立てる。

ホストプロジェクトにセッション記録の慣例がある場合 (= 例: `.skillshare/records/sessions/`)、そこにレポートを追記する。なければ、最終メッセージにインラインで返す。

## Final Report

```yaml
finish-task:
  task: <one-line summary>
  branch: <git branch>
  sha: <short sha>

  # Phase 1
  spec_coverage:
    - id: 1
      description: <spec item>
      status: achieved | partial | abandoned | blocked-by-harness
      evidence: <file:line | test-name | verifier-name | gap-description>

  # Phase 2 (user-facing changes only; n/a if pure refactor)
  uat:
    - id: 1
      given: <starting state>
      when: <user action>
      then: <observable outcome>
      pass: <binary criterion>
      evidence:
        type: test-output | command-output | log | screenshot | diff-line | harness-output | not-yet-collected
        ref: <path / test name / command / null>
        produced_by_agent: yes | no
    unrepresented_surfaces: [<surface needing human clarification>...]

  # Phase 3
  evidence_artifacts:
    - claim: <one-line summary of what's being proven>
      type: <as above>
      ref: <path / test-name / command / null>
      excerpt: |
        <5-10 lines of the actual output, or null if not-yet-collected>
      produced_by_agent: yes | no
      user_command: <only if not-yet-collected, the command the user should run>
    unbacked_claims: [<claim that has no evidence type>...]

  # Phase 4
  unresolved:
    todos: [<file:line>...] | NONE
    ignored_tests: [<test-name>...] | NONE
    scope_deviations: [<from → to>...] | NONE                # from / to は present-fact のみ、 Wave 名 / Phase 名禁止
    deferred:                                                # 先送りは必ず repo 外の永続的な置き場
      - item: <present-fact、 先送り対象>
        moved_to: <GitHub Issue URL / GitHub Project URL / ROADMAP.md セクション>
      | NONE
    future_plans_in_artifacts:                               # Step 4-5 grep 結果
      - file: <path>
        line: <N>
        excerpt: <該当 string>
        category: milestone-name | future-tense | future-proofing
        action: removed | kept-as-present-fact | escalated
      | NONE
      | not-grepped                                          # 未実行は NONE と書く資格なし

  # Phase 5
  ai_usage:
    used: yes | no | partial
    where: [<file:section>...]
    author_reviewed: yes | no | partial

  # Phase 6
  verification:
    harness_dispatcher: { exit_code, passed_count, failed_count, raw_output_ref } | null  # null if project lacks a dispatcher
    test_runner: { exit_code, summary }   # cargo test / pytest / npm test etc.
    linter: { exit_code, summary }        # cargo clippy / ruff / eslint etc.
    formatter: { exit_code, summary }     # cargo fmt --check / black --check etc.
    smoke_test:                            # Step 6-3; null if project has no binary
      attempted: yes | no
      command: <e.g. cargo run --bin foo -- --help>
      exit_code: <int | null if not-yet-collected>
      result: ok | crashed | not-yet-collected
      notes: <e.g. "headless env, GUI window creation failed; user confirmation required">
    git_state:                             # Step 6-4
      branch: <current branch name>
      on_protected_branch: yes | no        # main / master 直作業の warning
      push_state: up-to-date | ahead-N | behind-N | not-pushed
      pr_url: <URL | null>
      pr_action_needed: open | update | none

  # Self-assessment (not a verdict, just a flag)
  agent_confidence: high | medium | low
  agent_uncertainty_notes: <free text; what the agent is unsure about>
```

## Worked example

```yaml
finish-task:
  task: Add sidebar (initial slice of directory tree feature)
  branch: feat/sidebar-walker
  sha: a1b2c3d

  spec_coverage:
    - id: 1
      description: CLI takes a directory argument and shows it as a tree
      status: achieved
      evidence: crates/limn-ui/src/main.rs:42
    - id: 5
      description: symlinks are followed
      status: abandoned
      evidence: ADR-0008 records the security trade-off; not implemented in current scope (= follow-up tracked at https://github.com/sat0-hir0/backlog/issues/XXX)

  uat:
    - id: 1
      given: cargo run -p limn-ui -- ./docs
      when: click docs/README.md in the sidebar
      then: README.md opens in the right pane
      pass: title bar contains "README" within 500 ms
      evidence:
        type: not-yet-collected
        ref: null
        produced_by_agent: no

  evidence_artifacts:
    - claim: 4 unit tests added to explorer module
      type: test-output
      ref: walks_files_and_subdirectories
      excerpt: |
        test explorer::tests::walks_files_and_subdirectories ... ok
      produced_by_agent: yes

  unresolved:
    todos: NONE
    ignored_tests:
      - latency_100k_files (#[ignore]; requires fixture)
    scope_deviations:
      - Original scope included symlink support → abandoned per security reviewer findings (= ADR-0008)
    deferred:
      - item: Symlink follow
        moved_to: https://github.com/sat0-hir0/backlog/issues/XXX
    future_plans_in_artifacts: NONE

  ai_usage:
    used: yes
    where: [crates/limn-service/src/vault/explorer.rs]
    author_reviewed: partial

  verification:
    harness_dispatcher: { exit_code: 0, passed_count: 22, failed_count: 0, raw_output_ref: .skillshare/records/prs/local-a1b2c3d.md }
    test_runner: { exit_code: 0, summary: "35 passed; 1 ignored" }
    linter: { exit_code: 0, summary: "no warnings" }
    formatter: { exit_code: 0, summary: "clean" }
    smoke_test:
      attempted: yes
      command: cargo run -p limn-ui -- ./docs
      exit_code: null
      result: not-yet-collected
      notes: "headless agent env; gpui window creation fails. User must run on real machine."
    git_state:
      branch: feat/sidebar-walker
      on_protected_branch: no
      push_state: ahead-3
      pr_url: null
      pr_action_needed: open

  agent_confidence: medium
  agent_uncertainty_notes: |
    Real-machine acceptance of the sidebar click is not-yet-collected.
    Symlink follow is abandoned in this scope; trade-off documented in ADR-0008, follow-up tracked at https://github.com/sat0-hir0/backlog/issues/XXX.
```

## Related

- `$task-routing` — `$finish-task` が必要かどうかを判断する (= delegate-single / delegate-slice パスは常にこれを呼ぶ。Lead-direct は trivial であればスキップ可)。
- `$task-slicing` と `$wave-status` — `task:` フィールドに使う wave コンテキストを提供する。
- ホストプロジェクトの `$task-completion` (= あれば) — ハーネスゲートの一部としてこの skill を呼び出す。
