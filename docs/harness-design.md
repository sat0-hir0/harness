# harness 設計

個人開発で使う AI 開発ハーネスの設計仕様。 universal な部分 (= skill / agent / フロー / 工学原則) のみを記述する。 プロジェクト固有の運用 (= 例: backlog の board / Issue lifecycle) は **§4.1 外側レイヤー** で「乗る場所」 として位置づけるだけで、 詳細は各プロジェクト repo の doc に委ねる。

## 1. 概要

ハーネスは 2 層に分かれる:

- **内側 (= 本 repo のスコープ)**: 「1 つの要求 (= ユーザー発話 / Issue / バグ報告) を受け取り、 設計 → 実装 → 検証 → 完了報告まで回す」 共通の skill chain。 vendor (= Claude Code / Codex / Cursor / Gemini) を問わず同じ構造で動く。
- **外側 (= プロジェクト固有のスコープ)**: 「要求をどこから拾い、 どこに着地させるか」 のライフサイクル。 例: backlog ハーネスでは GitHub Issue を起点に board の 7 列 (= child 6 status + Epic 列、 §18) で管理する。

本 doc は **主に内側を記述** し、 外側との接続点 (= boundary) を §4.3 で明示する。 内側と外側の責務分離が doc 整理の核心。

## 2. 採用する工学原則

| 原則 | 意味 |
|---|---|
| State is on disk, not in context | 記憶は git / docs / state ファイルに置く。 context に頼らない |
| One item per loop | 1 要求 = 1 ループ。 triage / fix / review を混ぜない |
| Fresh context per iteration | 仕様は毎ループ source から再ロード、 context 汚染回避 |
| Maker / Checker split | 設計と検証は別 agent / 別 scaffold で実施 |
| Out-of-process supervisor | 停止判定を agent の自己採点ではなく外部で行う |
| Active over passive AI use | 委任ではなく概念探究として使う |

## 3. 多層防御スタック

「何を持つか」 (= agent / state / tool) とは独立した 「何で守るか」 の次元。

実装状態の凡例 (= 分類は grep + ファイル実在確認で裏取り。 根拠は [`wip/harness-evaluation-2026-07-02.md`](wip/harness-evaluation-2026-07-02.md) §3.8):

- **implemented**: 「役割」 欄が要求する形の機構が実在する (= 実 script / hook / agent 定義 / 運用中 boundary skill として確認できる)
- **prompt-text-only**: 原則 / 指示が skill 本文に存在するが、 強制する機構 (= hook / cap / code) は無い (= LLM が従わない場合に破れる)
- **not-built**: code にも skill 本文にも実体が無い (= 該当語がこの表以外に存在しない)

| 層 | 役割 | 起源 | 実装状態 |
|---|---|---|---|
| 1. 役割分離 | 設計 / 実装 / 検証 / UAT 準備を別 agent | Sense-Plan-Act、 Behavior Tree | implemented (= `agents/*.md` 6 種、 frontmatter `tools:` 制限は platform が強制) |
| 2. Back pressure | lint / typecheck / test green まで前進不可 | CI | prompt-text-only (= typecheck / test を green まで強制する gate は無く、 qa-expert / `$finish-task` の本文指示のみ。 `lefthook.yml` pre-push の 3 lint (= fixture-sync / frontmatter / agent-ref) は実在するが repo 自身の doc 整合 lint であり、 「役割」 欄が要求する test back pressure ではない) |
| 3. Out-of-process supervisor | 停止条件を外部 hook で grep block | MAPE-K | prompt-text-only (= 原則は skill 本文と Completion Check routine にあるが、 grep block hook は無い) |
| 4. Watchdog (in-band) | wave 毎の budget cap、 反復上限 | ROS software watchdog | prompt-text-only (= Stop conditions 4 件は本文指示のみ、 budget cap / 反復上限の code は無い) |
| 5. E-stop (out-of-band) | 破壊的操作 denylist、 手動 kill | ROS Nav2 Safety Node | not-built (= settings の deny は secret Read のみ、 破壊的操作 denylist は無い) |
| 6. Circuit breaker | 同一 task 連続失敗で escalation | Fowler | prompt-text-only (= 「検証 2 連続失敗 → surface」 は skill 本文指示のみ) |
| 7. Saga | 各 step に compensating action を up-front 定義 | Richardson | not-built |
| 8. Error budget | 失敗予算を pre-allocate、 枯渇で diagnostic 強制 | Google SRE | not-built |
| 9. Exponential backoff + jitter | rate limit / 5xx 時の retry 戦略 | AWS Builders' Library | not-built (= harness 側 retry code 無し、 platform 任せ) |
| 10. Durable execution | tool call を append-only event log、 resume 時 replay | Temporal | not-built (= wave-status の Log は進捗記録であり tool call event log ではない) |
| 11. Hermetic / content-addressed | input closure hash で agent step を memoize | Bazel / Nix | not-built |
| 12. UAT 引き渡し品質 | 人間 UAT に必要な素材を AI が揃える | 本ハーネス固有 | implemented (= `$finish-task` + boundary skill (`$prepare-uat`) が 9 要素を実運用で生成) |

> **読み方**: implemented は 12 層中 2 層のみ (= 1 / 12)。 5 / 7 / 8 / 9 / 10 / 11 の 6 層は該当語がこの表以外に存在しない (= 紙の防御層)。 この表を 「12 層で守られている」 と読まない。 組織 rollout 等でこのスタックを引用する際は、 実装状態列まで含めて引用する。

## 4. システム構成

内側 skill chain + 外側プロジェクトレイヤー + boundary 接続部 を一つの章にまとめる。 全体俯瞰は [`diagrams/inner-skill-chain.svg`](diagrams/inner-skill-chain.svg) (= 内側) と [`diagrams/backlog-lifecycle.svg`](diagrams/backlog-lifecycle.svg) (= 外側、 backlog プロジェクトを例にした参考図) を参照。

### 4.1 外側レイヤー (= プロジェクト固有、 本 repo の管轄外)

要求の入口と着地点はプロジェクトに依存する。 例:

| プロジェクト | 入口 | 着地点 |
|---|---|---|
| backlog | GitHub Issue (= board 7 列 = child 6 status + Epic 列) | PR merge で Done |
| 単発タスク (= chat 直起動) | user 発話 | session 終了 |
| code-review 作業 | PR / branch diff | 修正 commit |

外側レイヤーは内側 skill chain の **wrapping** をする責務を持つ。 backlog の場合は `$issue-from-idea` (= Inbox → Ready) / `$issue-execute` (= Ready → In Progress、 内側起動) / `$prepare-uat` (= 完了 → Completion Check) の 3 skill が wrapping を担う。 これら 3 skill は **backlog repo に置く** (= 本 repo には置かない)。

#### 入口集約 × 着地分散 (= boundary skill の repo 解決責務)

要求の **入口 (= どこから拾うか)** と **着地点 (= コードがどの repo にあるか)** は別軸であり、 一方に集約したもう一方は分散しうる。 backlog の例では 入口を 1 つ (= backlog repo の Issue) に集約する一方、 実コードは対象 product ごとの repo (= harness / limn / ...) に分散する。 この非対称を吸収するのが boundary skill の責務である。

原則: boundary skill は **「Issue を操作する repo」と「コードを操作する repo」を分離**する。 前者は入口 repo に固定され、 後者は Issue の分類情報 (= 例: `product:*` ラベル) から解決する。 両者を同一視すると、 別 repo のコードに対して入口 repo で branch を作り、 対象ファイルが存在せず実装できない (= repo mismatch)。 具体の解決規則 (= どの分類がどの repo に対応するか) は **入口 repo 側の boundary skill / 運用 doc に置く** (= 本 repo の管轄外、 §4.1 の方針どおり)。

### 4.2 内側 skill chain (= 本 repo の管轄、 vendor 非依存)

要求 1 件を回す共通フロー。 入口 2 つ + 共通ステージで構成。

#### 入口 (= entry-point)

ユーザー発話の性質に応じて 2 つの入口のどちらかが起動する。

| skill | trigger | 役割 |
|---|---|---|
| `$task-routing` | 実装系発話 (= 「直して」 / 「add」 / 「実装」) | verdict 3-way (= `Lead-direct` / `delegate-single` / `delegate-slice`) を出す |
| `$intent-clarify` | 相談 / 意図整理発話 (= 「相談」 / 「迷ってる」 / 「どう思う」) | 6 軸 intent (= Outcome / User / Why now / Success / Constraint / Out of scope) を確定 → `$task-routing` に one-directional に hand-off (= ループしない) |

#### 共通ステージ (= verdict 後)

- **Lead-direct**: Lead が直接実装。 sub-agent なし。 trivial な機械的編集 (= 1 file typo / mechanical rename) のみ。
- **delegate-single**: `architect` (= 設計) → `fullstack-engineer` (= 実装) → `qa-expert` + `security-auditor` (= 並列検証) の 1 ラウンド。 Lead は監督、 編集しない。
- **delegate-slice**: `$task-slicing` で wave 分解 → `$wave-status init` → 各 wave を delegate-single 相当で回す。

各 wave 完了時に `$wave-status mark` で進捗永続化、 全 wave 完了時に `$finish-task` で完了報告統合 + コミットメッセージ生成 (= `$commit-message`)。

#### subagent 6 種

| agent | 役割 |
|---|---|
| `architect` | 設計 / 影響範囲分析 / 接続点設計 |
| `fullstack-engineer` | 実装 (= file 編集 / コマンド実行) |
| `qa-expert` | 検証 (= test 実行、 typecheck、 spec との突き合わせ) |
| `performance-engineer` | 性能観点 lens (= 必要時) |
| `security-auditor` | security 観点 lens (= 必要時) |
| `technical-writer` | doc 整理 / README / コメント |

各 agent は自分の領域の影響判断を行う SPOF 解消 (= 「Lead が全部判断」 ではなく 「各 teammate が自領域を判断」)。

### 4.3 boundary 接続部 (= 外側 → 内側 → 外側)

外側レイヤーは以下の形で内側に hand-off する:

```
[外側] requestを準備 (= Issue / branch / context)
  ↓
[boundary skill が chat にプロンプトを投入]
  例: $issue-execute は 「Issue #N 実装、 終わったら $prepare-uat 呼んで」 を投入
  プロンプトには Execution mode (= ultra-autonomous / step-by-step) を inject
  ↓
[内側] $task-routing が description match で起動
  ↓
... verdict → wave → 実装 → 検証 ...
  ↓
[内側] $finish-task で統合レポート
  ↓
[boundary skill が外側に return]
  例: $prepare-uat は UAT パッケージを Issue にコメント + status を Completion Check に遷移
```

boundary skill (= `$issue-execute` / `$prepare-uat` 等) は **プロジェクト個別の repo** で持つ。 本 repo の skill は内側のみを記述する。 boundary skill が branch / worktree を用意し hand-off プロンプトに載せる際、 その worktree は **解決した着地 repo** (= §4.1 「入口集約 × 着地分散」) を指す。 内側 chain は渡された worktree の上で実装するため、 着地 repo の解決は内側に露出せず boundary が吸収する。

## 5. 起動経路

ユーザー発話と外側レイヤーの組み合わせで 3 経路ある。 backlog プロジェクトを例にすると:

| 経路 | trigger | 仕組み |
|---|---|---|
| a. chat 指示 | 人間が AI に 「Issue #N やって」 / 「X を直して」 | boundary skill を直接呼ぶ (= 即時起動) |
| b. board drag | 人間が board の status を手動で動かす | scheduled task の次サイクルで拾われる (= 最大 15 分 lag) |
| c. routine heartbeat | Claude routine が cron で起動 | プロジェクト固有の pick skill が要求を 1 件選んで boundary skill 呼出 |

chat 直起動の単発タスクは 「外側レイヤーなし」 で内側 skill chain が直接走る (= a 経路の特殊形)。

## 6. 入口 skill の判定

`$task-routing` の判定基準 (= Phase 1 定性 gate 3 質問):

1. **公開挙動の変更?**: UI 挙動 / public API / runtime contract / CLI semantics / on-disk file format が変わるか?
2. **harness で検証可能?**: 既存 verifier (= typecheck / cargo test / clippy / golden files) が客観的に確認できるか?
3. **設計判断は不要?**: 原因確定済 AND 修正は既存パターンの素直な適用 (= grep-1-shot) か?

3 つすべて NO / YES / YES → `Lead-direct`、 いずれかが該当しない → 委譲。 委譲は size (= `$task-slicing` の Size テーブルを SoT とする XS/S/M/L/XL) で `delegate-single` か `delegate-slice` に分かれる。

`$intent-clarify` の判定基準: 「意図整理 / 観点出し / stress-test / 方針決め」 に該当するか。 6 軸 intent を確定し、 必要なら 6 lens (= architect / fullstack-engineer / qa-expert / security-auditor / performance-engineer / technical-writer) を並列起動して観点を集める。 確定 intent を `$task-routing` に渡す (= one-directional)。

評価 / 監査 / レビュー型要求 (= 「評価して」 「audit X」) はどちらの入口の対象でもない。 read-only でレポートを成果物とし、 実装 verdict も意図整理も要らないため、 Lead が `qa-expert` + `architect` を直接 spawn する (= security 観点を含むなら security-auditor も併用)。

## 7. UAT パッケージの 9 要素 (= 外側レイヤーの仕様)

backlog プロジェクト等で実装完了から人間 UAT に渡す際に生成する素材。 内側 skill chain は本 9 要素を直接生成しないが、 `$finish-task` の統合レポートが素材を提供する。 boundary skill (= 例: `$prepare-uat`) がそれを 9 要素フォーマットに整形する。

**証跡 (1-3) → 確認方法 (4-6) → リスク + 自己開示 (7-8) → 差し戻し (9)** の順:

1. **実装サマリ** — 変更ファイル + 設計判断 + diff 規模 + 関連 ADR
2. **テスト結果** — test command + 新規 unit ケース + pass/fail + coverage 観点 + 手動確認
3. **レビュー指摘** — qa-expert / その他 subagent の指摘 + 対応状況 (= 修正済 / 意図的に残した / 後続 Issue)
4. **何を確認すべきか** — 要求機能の確認ポイント、 想定エッジケース、 regression 観点
5. **どう確認するか** — preview URL / 起動コマンド、 操作シーケンス、 test data
6. **AI が自分で確認した範囲** — 自動テストの screenshot / log、 「ここまでは自動」 の境界線
7. **想定リスク** — 「ここは confidence が低い」 「この edge case は試していない」 の自己申告
8. **AI 側で勝手に決めた事 + 懸念** — user 確認なく取った判断を **必ず列挙** (= 該当なしなら 「特になし」 明記)
9. **失敗時の差し戻し方** — 修正指示の付け方 + 再 pick の手順

## 8. Resume 戦略 (2 種類)

session が止まることはあり得るので、 再開手段を 2 つ用意する。

| 種類 | 用途 | 手段 |
|---|---|---|
| A. 同 session で再開 | 過去 context (= 議論履歴) を継承して続ける | Desktop sidebar から該当 session を開く、 または `claude --resume <id>` |
| B. 新 session で続行 | 過去 context は捨て、 repo state から復元 | worktree に cd → `claude` 起動 → 「branch から現状確認」 と指示 |

boundary skill (= 例: `$prepare-uat`) は UAT パッケージに **両方の手順を記載** する。

## 9. stuck 検知 + label 設計 (= 外側レイヤーの仕様)

長時間動かない session を検知する仕組みは外側レイヤーの責務 (= 内側は単一 session の中で完結する)。 backlog の例:

- `$issue-picking-heartbeat` が起動時に `~/.claude/projects/` の jsonl 最終更新時刻を scan し、 **6 時間** 以上更新がない In Progress な要求を **stuck と推定**。
- 挙動: **勝手に止めない、 警告のみ**。 警告内容 (= Issue コメント): 「session が N 時間更新ありません」 + Resume 手段 A / B 併記 + **24 時間 dedup**。
- 判断 (= Resume するか、 wontfix にするか、 そのまま待つか) は人間が行う。

### label の役割分離 (= 状態を記録、 状態遷移トリガーには使わない)

ラベルは 「状態を記録するか」 「状態を遷移させるか」 で 2 種類ある。 本ハーネスは **記録のみ採用、 遷移トリガーは不採用**:

| label | 役割 | 付与 | 削除 |
|---|---|---|---|
| `running` | 着手フラグ / 排他ロック memo (= optimistic locking) | boundary skill が claim 時 | boundary skill が離脱時 |
| `long-running` | 6h+ 滞留警告 | heartbeat が自動付与 | しない (= 過去事実として残す) |
| `needs-human` | 最初から AI 着手対象外 (= 静的判定) | user 明示 | user 明示 |
| `needs-fix` | 人間 UAT fail の差し戻し記録 (= Ready 差し戻しと同時に付与、 詳細は §17) | UAT fail 時に人間 | 再実装成功時にその session、 または人間 |

`running` の race detection: boundary skill が pick 前に `running` の有無を確認し、 既にあれば後発として abort (= board を一切触らず降りる)。 PRE==0 を 2 session が同時に見る稀な同時起動では両者が進む可能性があるが、 ラベル付与 + status 遷移は冪等に収束し、 session 開始コメントが 2 件付くだけで board に残留物は出ない。

stuck で `running` が残るのは意図的 (= 「動いている可能性」 を勝手に否定しない)。 `running` + `long-running` が同居 = 「着手中のはずが 6h 放置」 = stuck の明確なサイン。

### needs-human (= 静的判定、 着手前で除外)

`stuck` (= 着手後の動的状態) とは別軸で、 **最初から人間が物理的に手を動かさないと進まない要求** を区別する。 対象範囲は **AI が代替不能で物理的に人間の手が要る** 領域のみ (= 2 カテゴリ):

1. **environment / 設定の物理操作**: ローカル環境固有の path / 認証 / OS 設定、 外部サービス UI 操作、 chezmoi 手動 review、 ハードウェア絡み
2. **security / privacy / 不可逆操作**: 認証情報 / 鍵生成 / rotation、 production 破壊的操作、 external publish、 課金 / billing

それ以外 (= 学習優先 / 好み判断 / upstream 待ち / 抽象アイデア) は AI が回せる範囲なので対象外。 **AI 自動判定はしない** (= 誤判定で人間 Issue が AI に取られる本末転倒を避ける、 user 明示宣言のみで付与)。

boundary skill (= 例: `$issue-execute`) は起動時に label を確認し、 `needs-human` があれば **副作用ゼロで早期停止** する (= branch 作成 / status 遷移 / session コメント / `running` 付与のいずれも実行しない)。

## 10. 要求 ↔ branch ↔ session の紐付け

GitHub プロジェクトの場合、 標準機能 (= Issue の Development sidebar、 `gh issue develop`) を使い、 命名規約を自作しない。

- branch 名: `<issue-number>-<title-kebab>` (= GitHub 自動生成)
- worktree path: Issue 専用 worktree `~/code/.worktrees/<repo>/<issue-number>` (= メイン clone への checkout ではなく、 Issue 番号ごとに分離した worktree に展開する。 同一 repo で複数 Issue が同時着地しても衝突しない)
- session ID: Claude session が発行する ID
- 紐付け証跡: boundary skill が session 開始時に Issue コメントとして 「session ID / branch / worktree path」 を投稿

紐付けは worktree path から jsonl ファイルへ自動で辿れる (= 機械的対応可能)。

GitHub プロジェクト以外 (= 単発 chat タスク) は branch + worktree のみ、 紐付け証跡は git commit message に含める。

## 11. ワークフロー全体図

ASCII 図ではなく SVG 2 枚に統合した。 [`diagrams/backlog-lifecycle.svg`](diagrams/backlog-lifecycle.svg) (= 外側、 backlog プロジェクトを例) と [`diagrams/inner-skill-chain.svg`](diagrams/inner-skill-chain.svg) (= 内側 skill chain) を参照。 解説は [`diagrams/README.md`](diagrams/README.md) にある。

## 12. 無人実行の完走規約 (= チケット起動時の停止境界)

backlog の a / c 経路 (= chat の `Issue #N やって` / heartbeat 自動 pick) は **人間不在の自動 session**。 boundary skill が `Execution mode: ultra-autonomous` を inject した状態で `$task-routing` → `$task-slicing` chain が走る。 ここでの正しい終端を固定する。

### 正しい挙動

- **計画承認ゲートは自動 proceed**。 `$task-slicing` の ultra-autonomous mode は本来 「計画を 1 回 surface して人間の `proceed` を取る」 が、 **無人時は承認者が不在なので待たずに進む**。 計画提示で止まるのは誤動作。
- **全 wave を最後まで走破 → 最後に 1 回だけ boundary skill (= `$prepare-uat`) でまとめ UAT**。 wave 境界ごとの報告も、 途中の Completion Check / Awaiting UAT 退避もしない。
- 1 session で全 wave が終わらなくても、 **進めた分まで実装** して UAT に出す。 次 session (= heartbeat の別 run / 人間 resume) が wave 進捗ファイルから続きを拾う。

### 停止理由にならないもの (= 自己採点での過剰な慎重さの禁止)

設計原則 「停止判定を agent の自己採点ではなく外部で行う (= Out-of-process supervisor、 §2)」 の帰結。 以下は **止める理由にならない**:

- 「規模が XL / 複数 session にまたがる」 → wave 分割済みなので 1 wave ずつ進む
- 「未確定リスク」 → それを確かめるのが該当 wave の中身。 検証は wave 内タスク
- 「ADR が要る」 → Proposed 起票して進む (= Accepted 昇格だけ別 turn / 人間判断)
- 「設計判断が多い」 → architect / fullstack-engineer に委譲する話

### 本当に止めて良い条件 (= 客観的異常のみ)

- 検証 (= test / typecheck) が 2 連続で失敗
- UAT 不能 wave が分割後も残る
- 計画段階で予見していなかった ADR が wave の途中で初めて必要になる
- ユーザー向け変化を特定できないほど要求が曖昧

これらは In Progress のまま blocker を要求源 (= Issue) に surface して終わる (= UAT パッケージを作らない、 diff 0 行で boundary skill を呼ばない)。 stuck として heartbeat が 6h 後に拾える。

> この規約が無いと、 Lead が 「大変そうだから計画だけ立てて Awaiting UAT に逃がす」 誤動作を起こす (= 過去に実発生)。 内側 skill chain と boundary skill の各層に対応する gate を実装済み。

## 13. Completion Check 精査ルーチン (= 性悪説 Checker、 外側レイヤーの仕様)

boundary skill (= 例: `$prepare-uat`) が着地させた要求を、 別の scheduled task (= 例: `completion-check-routine`、 cron `7-59/15 * * * *`、 heartbeat と 7-8 分裏) が **性悪説 (= 達成していないと疑う) を default** に精査する。 §2 の 「Out-of-process supervisor」 + 「Maker / Checker split」 を体現する **Checker 役**。 実装 session (= Maker) の自己申告を鵜呑みにせず、 別 process が証跡で裏取りする。

### 4 つの証跡ソース

| 証跡 | 見る対象 |
|---|---|
| 本文 wave 進捗 | 要求 body の wave チェックボックスが全完了か |
| git log 裏取り | 主張した変更が実際に commit され、 **origin に push されているか** (= 未 push はローカルのみで GitHub から見えない) |
| スコープ乖離 | 要求と diff の範囲がズレていないか |
| test 通過 | test / typecheck の pass 証跡があるか |

### 3-way routing (= 実質 forward/bounce の 2-way + 例外)

| verdict | 遷移 | 補足 |
|---|---|---|
| forward (達成) | Completion Check → Awaiting UAT 前進 | 全 wave ✓ + git log 裏付け (push 済み) + test ✓ + スコープ乖離なし。 人間 UAT へ |
| bounce (未達) | Completion Check → Ready 差し戻し | スコープ未達・乖離・**未 push**・test 未通過。 **worktree は残す** (= 継続性、 再 pick が現状から続行) |
| escalate (真の判断不能) | Completion Check → Awaiting UAT に回す | 別 repo で repo 名喪失 / 本文と diff 矛盾 = cron が機械的に合否を出せない。 「裏取りゼロ」 を ⚠️ コメントで明示し人間が一から judge |

**判断不能の再分類** (= escalate を激レアに縮小):

- **未 push** は 「裏取り不能 = 判断不能」 ではなく **「push 義務違反 = 不合格 (bounce)」**。 「State is on disk」 (= §2) に push は含まれ、 ローカルのみ = State が共有されていない = 完了の前提未達。
- **push 済みで branch 名だけ判明** なら worktree path 不明でも gh 経由で git log 裏取り可能 (= 判断不能にしない)。
- 真の判断不能 = 「別 repo で repo 名が記録から喪失」 のみ。 session 開始コメント保全でこのケースも大幅に減る。

いずれの verdict でも Completion Check を抜ける際に `running` ラベルを削除する (= 離脱でフラグを下ろす)。

### DRY_RUN 安全装置

判定ロジックが信頼できるまで `DRY_RUN=true` で起票。 verdict を Issue コメントで報告するだけ、 status は動かさない。 cron 判定が実際の前進 / 差し戻しと一致することを確認してから `false` へ flip。

### worktree ライフサイクル (= 作成 / 保持 / 削除の全体)

Issue 専用 worktree (`~/code/.worktrees/<repo>/<N>`、 §10) は 3 つの局面を持つ。 3 局面すべてに主体が割り当てられており、 「残す (= 保持)」 だけが書かれて終端の無い leak を作らないよう、 ライフサイクル全体をここに固定する:

- **作成**: `$issue-execute` が Phase 2 (branch 作成) で worktree を作る (= メイン clone には checkout せず、 Issue 番号ごとに分離した worktree に展開する)。
- **保持 (= 継続性)**: bounce (= Completion Check → Ready 差し戻し) 時、 **worktree は破棄しない**。 再 pick した session が repo state (= Resume 戦略 B、 §8) から現状を復元して続きを進められる。 差し戻しは 「やり直し」 ではなく 「未完を Ready に戻して継続」。
- **削除**: **Done 確定時**に worktree を撤去するのが設計上の終端。 その主体は `#122` (board-Done 到達時の gh issue 自動 close routine) で、 Done → close の 1 走査に 「gh issue close」 と 「worktree 削除 (`git worktree remove --force`)」 を束ねる。 `#122` は land 済み (= `done-close-routine` が cron 登録済み、 close の成否と独立に `~/code/.worktrees/<repo>/<N>` を撤去する)。 撤去は `.worktrees` ルート配下の path のみを対象とする 2 段階正規化 (= `realpath -m` で traversal 解決 + `cygpath -u` で drive 形統一) を安全弁に持ち、 メイン clone / ルート外 path を弾く。 branch は残す (= `worktree remove` は worktree ディレクトリのみ削除、 branch 掃除は本 routine のスコープ外)。 `$issue-execute` 側の worktree 化 (`#129`) と `#122` 側の削除実装は別 land だが、 両者とも land 済み。

3 局面すべてに主体があり、 削除の設計上の終端は Done 確定、 その自動化は `#122` (`done-close-routine`) が担う。

## 14. session 透明性の規約 (= plan / wave 変動を外部記録に残す)

session が途中で死んでも **外部記録 (= Issue コメント / commit message / wave-status file 等、 プロジェクトが保有する記録メディア) だけ追えば最新の Plan / Wave 構成 / 進捗地点が分かる** 状態にするための運用規約。 §2 「State is on disk, not in context」 の帰結。 透明性 (= 何を着手し、 どう Plan が変わり、 どこで引き継ぐか) を上げる。

### 投稿タイミング (= 3 種類のイベントだけ記録、 他は記録しない)

| イベント | 担当 skill | 内容 |
|---|---|---|
| 着手時 | verdict に応じて `$task-routing` (= `Lead-direct` / `delegate-single`) または `$task-slicing` (= `delegate-slice`) | Plan (= wave 構成 / Agent chain / Execution mode / ADR)。 1 ループ 1 回のみ |
| Plan 変動時 | `$task-slicing` (= 再スライス時) または `$wave-status` (= 直接 mark で wave dropped/blocked/追加/順序変更) | 変更点 + 更新後の plan |
| 完了時 | boundary skill (= 例: `$prepare-uat`) | UAT パッケージ + 進捗地点 / 残タスク / 注意点 (= 完了レポートに統合、 別記録にしない) |

**done / in-progress の単純進行では記録しない** (= wave が予定通り進んだだけでは外部記録を増やさない、 ノイズになるため)。 記録するのは plan 変動イベント (= dropped / blocked / 追加 / 順序変更) と着手 / 完了の節目のみ。

### 責務分離 (= Plan 変動の二重投稿排除)

再スライスのフロー (= `$task-slicing` 再呼び出し → plan 更新 → `$wave-status mark` で wave dropped/blocked) では、 **`$task-slicing` が Plan 変動記録を投稿する担当**。 `$wave-status` は再スライス経由で呼ばれた場合は **投稿しない** (= `$task-slicing` 側が投稿済み)。 `$wave-status` が投稿するのは、 **`$task-slicing` を経由しない直接 mark で wave が dropped/blocked/追加 された場合のみ**。

両 skill が独立に 「plan 変動 = 投稿」 を持つため、 この担当分離が無いと同一イベントで二重投稿する。

### 二重投稿排除の verdict 別ルール

`delegate-slice` の着手 Plan は `$task-slicing` のみが投稿する (= `$task-routing` は投稿しない、 明示スキップ)。 `delegate-single` / `Lead-direct` は `$task-routing` が軽量版 (= wave なし、 アプローチ + Agent chain + ADR) を投稿。

### 投稿目的 (= なぜ書くか)

`$task-routing` / `$task-slicing` / `$wave-status` が外部記録 (= GitHub Issue コメント等) に書く目的は 2 つ:

(1) **透明性担保**: Lead が下した判断 (= verdict / slice plan / wave 構成変動) を、 session がリセットされても外部記録から追える状態にする。
(2) **作業・判断履歴担保**: 着手判断 / ADR 起票 / dropped 判断などを Issue を見るだけで時系列で追えるようにし、 Lead の頭の中だけに残さない。

この 2 目的のどちらにも貢献しない投稿 (= 単純進行 done / in-progress マーク等) は書かない (= 過剰投稿防止)。

### 題材 Issue の同定フロー (= 投稿先決定、 旧 「2 条件 AND」 を置き換え)

`$task-routing` / `$task-slicing` / `$wave-status` は **複数プロジェクトで共用される汎用 skill**。 投稿先 (= 題材 Issue) の決定を **出自 (= どの skill から呼ばれたか) ではなく、 投稿価値のある判断が発生した時点で能動的に Issue を同定する** 方針に倒す。

以下を順に確認し、 最初に確定したものを投稿先とする:

1. 外側 boundary skill (= 例: backlog の `$issue-execute`) の hand-off プロンプトに Issue 番号・リポジトリ名が明示注入されている AND 注入された repo 名が **その skill の投稿先 repo (= 例: backlog harness では `sat0-hir0/backlog`) と一致する** → そのまま投稿 (= 最高信頼度)。 注入された repo 名が一致しない (= 別 project から hand-off された) なら、 フロー 1 では確定せずフロー 3 に落とす (= 別 project の Issue 番号を誤投稿しないため)。
2. ユーザーが当該 session で `#N` / Issue 番号を明示的に言及しており、 かつ対象 repo が文脈から確定している → 投稿 (= 高信頼度)。
3. session の直前の発話に Issue 番号はあるが、 対象 repo が確定していない → 有人なら 3 択を surface (= (a) 新規 Issue 起票 / (b) 既存 Issue に紐付け / (c) 今回は残さない)、 無人 (= ultra-autonomous / cron heartbeat / 自動 session) なら **session pause** して「題材 Issue 未確定」 を記録して終了。
4. 過去 context に偶然 `#N` 文字列が混入しているだけで、 明示的言及がない → **投稿しない** (= 誤爆防止)。
5. Issue 番号が存在しない → **投稿しない**。

フロー 1-2 が確定、 またはフロー 3 でユーザーが (a)/(b) を選択した場合のみ投稿を実行する。 想定外のプロジェクトで投稿 API が誤爆するのを防ぐため、 投稿先 repo は各 skill 文面で **固定** する (= 例: backlog harness では `sat0-hir0/backlog` 固定)。

### 投稿価値のある判断 (= 投稿対象イベント) と escape valve

投稿対象 (= 構造的判断):
- slice plan 生成 (= 新規 wave 構成の確定)
- Plan 更新 (= wave の追加 / dropped / blocked / 順序変更)
- ADR 起票判断 (= Proposed 起票を決定した事実)
- verdict 判断の確定 (= Lead-direct / delegate-single)
- Wave 着手判断の根拠 (= 計画外の構造的判断)

投稿対象外 (= 些末判断、 過剰 surface 防止の escape valve):
- mid-implementation の些末判断 (= lint fix / typo 修正 / test 1 件追加 / 関数名 rename 等)
- done / in-progress への単純進行マーク
- 計画通りに次 wave へ進む行為

### Posture (= 沈黙より投稿)

デフォルトは **投稿側に倒す**。 user に明示的に「不要」 と言われない限り、 投稿価値のある判断は投稿 / 立ち戻りを行う。 沈黙すると判断が消えるため、 「迷ったら投稿」 が原則。

### 3 択 (c) 「今回は残さない」 を選んだ場合の session 内記録

surface 直後の chat に Lead が以下の 1 行 log を必ず出す (= 履歴担保の最低保証):

> 📝 透明性 / 履歴担保の放棄を user が許容 (= 判断「<1 行要約>」 を Issue に残さない選択)。 session 内のみで完結。

これにより (c) を選んだ事実そのものが session 内に残る (= 後から「なぜ Issue に紐付けなかったか」 が追える)。

### 無人実行時の Lead 独断禁止 原則

無人 (= ultra-autonomous / cron heartbeat / boundary skill 経由で人間不在) では、 Lead が以下を **絶対に独断で行わない**:
- 題材 Issue 不明時に自動で `$issue-from-idea` 等を呼んで新規 Issue を起こす (= 透明性 / 履歴担保の放棄を AI 単独で決めるのは原則違反)。
- 「曖昧だから今回はスキップしておこう」 と投稿を黙って省略する (= 沈黙は最悪の選択肢)。

代わりに session pause + surface message「題材 Issue 未確定」 を記録して session を終了する。 透明性 / 履歴担保の放棄は user 判断専属。

### 投稿先・フォーマットのプロジェクト固有性

具体的な投稿先 (= Issue コメント / commit message / Slack / その他) と投稿フォーマット (= 見出し / 絵文字 / 構造) は **プロジェクト固有**。 各プロジェクト repo の boundary skill とプロジェクト doc で定義する (= 例: backlog プロジェクトでは GitHub Issue コメントに `📋` / `🔄` / `🎯` 絵文字付きで投稿)。

## 15. 採用しない選択

セミ自律であって全自律ではない。 以下は意図的に持たない。

- budget cap なしの autonomous overnight
- MCP 経由での本番システム接続
- AI 自己判定での PR merge
- 破壊的操作の事前 gate なし実行
- 全自動で人間 review を skip する経路
- AI による依存推論 (= 機能の実装順を AI に推論させる、 推論誤りが多い)
- label を介した **状態遷移 trigger** (= 「ラベルを付けたら status が動く」 のような間接的な遷移トリガー。 責務が間接的になるため不採用)

> **`running` ラベルとの関係 (= 上記の例外ではない)**: `running` ラベルは **状態遷移 trigger ではなく排他ロック memo** (= optimistic locking の claim 印、 §9)。 「`running` が付いたから status が動く」 のではなく、 status 遷移は常に明示的な script (= `issue-status.ps1` 等) が行い、 `running` は 「今 claim されているか」 を記録するだけ。 heartbeat はこのラベルを **読んで** race を判定するが、 ラベルが status を **動かす** ことはない。 同様に `long-running` も状態を記録するだけで遷移を起こさない。 したがって両ラベルは 「状態遷移 trigger 不採用」 の方針と矛盾しない。

## 16. Done の定義 (= board Done と git merged の一致)

> この節は末尾に追記する (= §10〜§15 の連番を動かさない)。 過去に §10 挿入で以降を繰り下げた際、 repo 内 1 件 + repo 外 7 件の `§N` deep link がずれた。 新規節は **常に末尾に足す** ことで既存参照を保全する。

**Done の唯一の定義は、 対応 PR が main に merge された状態である**。 board 上で Done column に入っていることと、 対応 branch が main に merge 済みであることは、 常に一致する。

**Done への遷移主体は built-in workflow (= 自動)**。 board で要求を Done column に移すのは、 PR が main に merge された時に built-in workflow (= GitHub Projects の PR merge → Done 自動遷移) が行う。 board の Done は git merged の **後追い** であり、 先行しない。 boundary skill (= 例: `$prepare-uat`) が置くのは Awaiting UAT までで、 **AI が merge 未確認のまま自己判定で Done に動かすことは禁止** (= §15 「AI 自己判定での PR merge」 不採用と同軸)。 人間が merge を実行 / 承認した結果として built-in workflow が Done に運ぶ、 という因果を守る。

unmerged なまま Done column に置かれた card は不整合である。 §9 の heartbeat が拾う stuck 判定 (= `running` + `long-running` の同居) とは別軸の異常であり、 「Done なのに branch が残っている」 状態は stale branch として扱う。 stale branch は、 該当 Issue の card が Done にあるにもかかわらず未 merge の branch が存在する状態を指す。

## 17. 差し戻しプロトコル (= needs-fix + issue 本文への必須 deliverable 追記)

> §16 と同じく末尾追記 (= §1〜§16 の連番を動かさない)。

人間 UAT が fail した要求は、 `needs-fix` label (= §9) を付与し、 fail 理由を Issue コメントに残し、 status を Ready に差し戻す (= §13 の bounce と同じ着地、 worktree は残す)。 label を外すのは **再実装 session が成功した時にその session 自身、 または人間** (= 成功の自己申告は §13 の Checker が裏取りする)。

**fail コメントだけでは再実装 session に消費されない (= 実証済み)**。 backlog#82 では `needs-fix` label + fail コメントのみの差し戻しに対し、 再実装 session が同一 fail を 2 連続で再現した (= コメントは読み飛ばされる)。 **必須 deliverable を Issue 本文に追記する方式へ切替後**、 backlog#82 は 3 回目で収束、 backlog#86 は 1 発で収束した (= 本文は再 pick 時に必ず読まれる)。

したがって差し戻しは、 fail 理由コメントに **加えて**、 Issue 本文へ 「**差し戻し: 必須 deliverable**」 セクションを追記することを必須とする。 内容は (1) 再実装が満たすべき deliverable の列挙、 (2) 各 deliverable の受け入れ確認 (= acceptance check、 再実装 session が自己検証できる形)。 コメントは経緯の証跡、 本文追記は次 session への確実な入力、 と役割を分ける。

## 18. 階層 Issue 構造 (= Epic + sub-issue、 外側レイヤーの仕様)

> §16 と同じく末尾追記 (= 既存節の連番を動かさない)。

backlog harness は GitHub Sub-issues (= parent ↔ child) を **計画 / 実装** のレイヤー分離に使う。 概念:

- **Epic** = 上位の機能群を束ねる **計画装置** (= 目次 + 進捗バー表示装置)。 child 一覧は GitHub native の Sub-issues 欄が自動表示するため、 本文には列挙しない (= 二重管理回避)
- **child** = 実装単位の Issue (= 1 child = 1 deliverable)。 AI 着手対象はこちらのみ

### 設計原則 (= 5 軸)

| 軸 | 採用方針 |
|---|---|
| AI 着手対象 | **child Issue のみ** (= Epic は計画装置で着手対象外) |
| status 連動 | **独立** (= child は個別 status、 Epic の進捗は GitHub の `subIssuesSummary` が自動表示) |
| 実装スコープの記述 | **child 本文に分散** (= Epic は目次。 詳細実装事項は child 側) |
| heartbeat の pick 対象 | **child のみ** (= Epic は board の `Epic` 列にしか居ないため、 Ready 列 pick の filter で自然に除外される) |
| Completion Check の判定 | **各 child 独立判定** (= 親 Epic は判定対象外、 child の Done 集計は GitHub 側で勝手に行う) |

### 列構造 (= board 上の Epic 列、 backlog 固有)

backlog board の Status field option は 7 個:

| Status | 説明 |
|---|---|
| Inbox | 着手前の未整理 Issue (= idea / 議論中) |
| Ready | 着手可能、 仕様確定済 (= heartbeat pick 対象) |
| In Progress | AI 着手中 (= `running` ラベル付与済、 §9) |
| Completion Check | 性悪説 Checker による精査中 (= §13) |
| Awaiting UAT | 人間 UAT 待ち |
| Done | 完了 (= child は PR merge で自動遷移、 Epic は user が手動で移動) |
| **Epic** | 親 Issue 専用 (= child の status 遷移とは独立、 完了したら user が手動で Done に動かす) |

child Issue は 6 個の status を巡回し、 Epic Issue は `Epic` 列に居続けて (= 全 child が Done になったら user が `Done` に動かす)。 board の view を **Group by Parent issue (Swimlane)** にすると、 各 Epic ごとに横 row が形成され、 child が `Status × Epic` の格子上に並ぶ (= backlog 固有の運用 doc は [backlog/docs/board-view-guide.md](https://github.com/sat0-hir0/backlog/blob/main/docs/board-view-guide.md))。

### 紐付け API (= GitHub Sub-issues REST)

- POST `repos/{owner}/{repo}/issues/{parent_number}/sub_issues` で parent ↔ child を紐付け
- 引数 `sub_issue_id` は **REST database id (= integer)** を要求 (= GraphQL global node_id ではない)。 `gh api repos/.../issues/<N> --jq .id` で取得した integer を `gh api -F sub_issue_id="$ID"` で送る (= `-F` が JSON typed フィールド)
- Tasklist (= 本文の `- [ ] #N` チェックボックス) は別物 (= 本文の参照リンクであり、 階層構造として Projects v2 が認識しない)。 階層構造管理は Sub-issues API 一択

### Epic Issue 本文の form (= `.github/ISSUE_TEMPLATE/epic.yml`)

Epic 用 form の field 構成:

| field | 必須 | 内容 |
|---|---|---|
| Product (dropdown) | yes | `product:limn` / `product:harness` 等 (= §19 product label 設計) |
| 目的 (textarea) | yes | この Epic で達成したいこと (= Why) |
| スコープ (textarea) | yes | 含む範囲 / 含まない範囲 (= What / What not) |
| 完了条件 (textarea) | no | Done と判断できる基準 |
| 依存関係 / 前提 (textarea) | no | 他 Epic / 外部サービスへの依存 |
| 備考 (textarea) | no | 詳細はコメントで追記する文化を維持 (= 議論ログを本文に埋め込まない) |

child Issue 本文の form (= `idea.yml`) と異なり、 Epic は `### Execution mode` / `### 人間対応の要否` セクションを持たない (= Epic は計画装置で `$issue-execute` が parse しないため不要)。

## 19. product label 設計 (= 横断 product の識別、 外側レイヤーの仕様)

backlog は複数 product を 1 つの board で扱う (= 現状 limn / harness)。 各 Issue が **どの product 由来か** を識別する仕組みとして `product:*` ラベルを使う。

### ラベル一覧 (= 現状)

| ラベル | 対象 product |
|---|---|
| `product:limn` | limn (= keyboard-first Markdown editor) 関連 |
| `product:harness` | harness (= AI development harness) 関連 |

### 付与経路 (= 二系統)

| 経路 | 付与方法 |
|---|---|
| web UI 経由 (= Issue Forms) | `.github/workflows/apply-product-label.yml` workflow が **本文の `### Product` section を parse** して label を付与 |
| chat 経由 (= `$issue-from-idea`) | skill が `gh issue create --label product:<x>` で **直接付与** (= workflow を経由しない) |

両経路ともに本文に `### Product` section を持たせるため、 万一の二重付与は冪等で無害 (= 同じラベルを 2 回 add しても GitHub API は idempotent)。

### Epic と child の関係

- Epic Issue: form の Product dropdown が必須 (= Epic 作成時に必ず 1 product を選択)
- child Issue (= 経路 b/c): 親 Epic の product label を **継承** (= skill が `gh issue view <E> --json labels` で親の `product:*` を取得して child に同じ label を付ける)
- child Issue (= 経路 a、 parent なし): product label を **付けない** (= AI が無理に判定しない、 user に確認も急がない。 後から `gh issue edit` で足せる)

product label は **board の filter / search** で活用される (= 「limn 関連の Issue だけ表示」 「harness の Ready を一覧」 等の view 切替)。 label の追加 / 削除は単純な `gh label create` / `gh label delete` で行い、 board 側 field の変更は不要 (= ラベルは Issue に直接付くため、 board の field 設定とは独立)。
