# ハーネス評価レポート (2026-07-02)

harness / backlog の両リポと直近の作業キューを対象にした multi-agent 評価の結果記録。評価は 2 つの workflow で実施した (= 内部評価 19 agents + 外部比較 6 agents、計 25 agents / 約 195 万 output tokens)。**「確定」と表記した項目は、実 repo / 実 Issue への敵対的検証 (= verdict: valid) を通過したもののみ**。検証で棄却・修正された judge 推奨は §7 に記録した。

> **snapshot 注記**: 評価は 2026-07-02 の作業ツリー (= feat/eval-regression-classify checkout 時点) と board 状態に基づく。レポート作成時点で main は eval 基盤一式 (= eval/ + lefthook.yml + scripts/eval-gate.py、45 files) を取り込み済みであることを確認した。該当 finding (= §3.4) には解消状況を併記。

## 0. TL;DR

- **設計思想は 2026 年半ばの業界最先端とほぼ一致 (= near-frontier)。弱点は思想ではなく「ゲートの機械的締結」**。紙の上では必須の統制が実際には効いていない箇所が複数確定した。
- スコア: eval・観測性 2/5、他 5 次元 (= context 経済性 / routing 信頼性 / 外側ループ / process 重量 / platform 適合) 3/5。
- 最重要発見: **mandatory review gate が存在しない agent 名を参照** (= §3.1)。3 judge が独立検出。組織導入の教訓は「文書化された gate は機械的に解決可能・検証可能でなければならない」。
- 外部比較: 利用度は power user 水準を超え、ギャップは機能不足ではなく**可搬性** (= CI/headless ゼロ、全ガードレールが 1 台の Windows 機依存)。
- 方向性: 5 つの賭けのうち 4 つ (= verification-first / 比例 routing / human-UAT ゲート / eval 駆動 skill 開発) はエコシステム収束先と一致。逆張りは skillshare のみで、Claude 向け配布は plugin/marketplace への分割を推奨。

## 1. 評価手法

### 内部評価 workflow (19 agents)

1. **Read**: 6 並列 reader (= skills 全 6 件精読 / agents 全 6 件 / 設計 doc + wip / eval 基盤 / backlog 外側ループ / roadmap Issue 群)
2. **Judge**: 6 次元の成熟度採点 (= 1-5、5 = solo-dev ハーネスの最先端水準)
3. **Verify**: judge の全推奨を実 repo / 実 Issue に照合する敵対的検証 (= verdict: valid / already-covered / questionable)
4. **Critique**: どの次元もカバーしなかった盲点の抽出、judge 間矛盾の検出

### 外部比較 workflow (6 agents)

1. **Survey**: Anthropic 公式 guidance / community practice / eval 業界水準 の 3 並列 Web 調査 (= 計 35 ソース、code.claude.com docs / anthropic engineering blog / HN / 実務者ブログ)
2. **Inventory**: ローカル Claude Code 設定の実監査 (= settings / hooks / MCP / plugins / cron / worktrees / CI)
3. **Compare**: 利用度 judge + 方向性 judge

## 2. スコア (5 点満点)

| 次元 | スコア | 採点根拠の要約 |
|---|---|---|
| context 経済性 | 3 | 上層 (= CLAUDE.md の再掲禁止方針) は模範的。skill 本体に triplication (= §3.7) と description 超過。meta 規律 (= token 実測 / 3.7x 見積誤差の自己修正) は最先端水準 |
| routing 信頼性 | 3 | 2 入口設計 (= 相互 SKIP 参照 / bilingual trigger / verdict 語彙統一) は良質。agent 名 drift + size 表分裂 + assess 型 request の fall-through |
| eval・観測性 | **2** | 実インフラはあるが skill を実行しない (= §3.3)。expected_trigger は記録のみで未評価。段階 1 metrics 未実装 |
| 外側ループ自動化 | 3 | 設計は証跡付き (= DRY_RUN 段階 rollout / Completion Check が実 defect 検出)。UAT 滞留 + 自己申告証跡 + 差し戻し経路の破綻 (= §4) |
| process 重量 vs 価値 | 3 | バイアスへの抵抗証跡あり (= CAS 棄却 / strategy A 保留 / §15 棄却記録)。未証明 ceremony が相当量 (= XS でも dual-review 必須、13 block UAT 固定) |
| platform 適合 | 3 | 構造 (= frontmatter / tool 制限 / model 段階化) は正しい。実行面で読み込みモデルと衝突 (= §3.2、progressive disclosure ゼロ) |

## 3. 確定 defect (敵対的検証済み)

### 3.1 mandatory review gate が存在しない agent を参照 (最重要)

task-routing / task-slicing / intent-clarify が spawn を必須指定する `reviewer` / `qa-verifier` / `docs-curator` は agents/ に存在しない。実在は architect / fullstack-engineer / performance-engineer / qa-expert / security-auditor / technical-writer の 6 つのみ。

- 該当: `skills/task-routing/SKILL.md:97-102,215`、`skills/task-slicing/SKILL.md:171,307`、`skills/intent-clarify/SKILL.md:34-36`
- backlog 側の issue-execute chain は実在名を使用しており、修正の参照先が既にある
- 3 judge (= routing 信頼性 / process 重量 / platform 適合) が独立検出。ハーネス中枢の品質ゲートが「必須かつ未締結」であり、12 層防御スタックの ~7 層がコードゼロである点 (= §3.8)、Completion Check の自己申告受理 (= §4) と同型の失敗様式

### 3.2 description の YAML `#` 切断

skill description が途中で切れる原因は長さ制限ではなく、**unquoted YAML scalar 中の ` #` がコメント開始として parse される**こと。

- task-routing: 1,388 字中 837 字 (= ` #1` の直前、"Skipping this is the" で切断) — 検証が live skill 一覧で実測
- backlog の issue-execute: **約 60 字で切断** (= trigger 面が実質破壊、「〜 Issue」 で途切れる)
- 「~850 字 render limit」という judge 仮説は検証で棄却 (= §7.2)。修正は quoting のみ

### 3.3 eval が skill を実行していない

`eval/scripts/eval-run.py` は手書き YAML (= cases) と手書き YAML (= baseline) の diff であり、skill 本文は一度も実行されない (= eval-run.py:5-13 に自己申告あり)。

- SKILL.md 本文の変更は pre-push gate を素通りする (= gate の主目的である回帰クラスを検出できない)
- 失敗時メッセージが「re-baseline して push」を指示し、`--override` は無レビューで通る (= eval-gate.py:230-234、rubber-stamp 反射を訓練する構造)
- expected_trigger / expected_no_trigger は全 30 case に記録されているが一度も評価されない
- 業界比較 (= §5.3): 「deterministic checks at commit、LLM judge は PR/nightly」が実務者合意。judge-on-every-commit は数ヶ月で無効化されるのが通例と報告されている。現 gate は fixture-sync lint として正名化すれば健全

### 3.4 Done ≠ merged (→ 内容は解消済み、stale branch 残存)

評価時点: #63/#64 が board-Done なのに eval/ が main に無く、feature branch 5 本が積層、#65 が #64 の未 merge branch 上に構築され rebase リスクが顕在化していた。

- **レポート作成時点で eval 基盤一式は main 到達を確認** (= 0d2fccc → aa914fe)
- ただし feat/eval-harness / feat/eval-regression-classify / feat/epic-sub-issue-layer / feat/no-future-plans-in-skills / fix/backlog-17-issue-comment-gate の 5 branch は git 上 no-merged のまま残存 (= 内容は別 commit で main 到達した模様、クリーンアップ候補)
- 構造的教訓は残る: **board の Done と git の merged が独立に動ける** (= 改善案 §9 の Done 定義)

### 3.5 差し戻し経路が初回で破綻する

- prepare-uat の UAT package 要素 9 が指示する `needs-fix` label が sat0-hir0/backlog に存在しない (= gh label list で確認)
- `docs/architecture-vision.md` への dangling 参照が約 10 箇所 (= issue-execute / prepare-uat / issue-from-idea / completion-check-routine)

### 3.6 DRY_RUN drift (= chezmoi apply が地雷)

**2026-07-03 追記**: DRY_RUN drift は解消済みを確認 (= deployed / source 両方 `DRY_RUN=true` で一致)。 残っていた実 drift は deployed 側の frontmatter 二重化のみで、 chezmoi apply + runtime prompt 同期で解消した (= Issue #84)。

completion-check-routine の deployed 版は DRY_RUN=false、chezmoi source (= dotconfig) は true。`chezmoi apply` を実行すると本番 gate が silent に dry-run へ戻る。

### 3.7 skill 間の重複と SoT 分裂

- backlog 専用 issue-comment protocol (= 約 180 行) が task-routing:105-167 / task-slicing:320-401 / wave-status:89-149 にほぼ逐語で triplicate。**重複自体は fresh-context 原則による受理済み設計判断** (= §7.1) だが、独立 drift の実害が既に発生:
- **size 表分裂 (確定)**: task-routing:71-73 (= XS 1-2 files / S-M 3-4 / L-XL 5+) と task-slicing:47-53 (= XS 1 / S 1-2 / M 3-5 / L 5-8 / XL 8+) で delegate-slice 閾値の SoT が 2 つ。5 files のタスクで判定が食い違う

### 3.8 その他の確定事項

- harness-design.md §3 の 12 層防御スタックのうち **~7 層 (= watchdog / E-stop / saga / error budget / backoff / memoize 等) はコードゼロ** — 該当語は表の中にしか存在しないことを grep で確認。実装状態列が無い
- agent frontmatter の dead MCP 参照: architect の context7 (= 全 scope 未設定)、fullstack-engineer の serena (= ow-my-coach でのみ設定) が silent に無効
- wave-status が `~/.claude/state/` を 6 箇所 hardcode (= finish-task は per-vendor 自己判定パターンを既に持つ。vendor 可搬性の主張と矛盾)
- intent-clarify の ATTRIBUTION.md が現 SKILL.md に無い機能を引用 (= companion file の drift 実例)

## 4. 外側ループの観察

- **UAT 滞留の内訳** (= 評価時点): Awaiting UAT 8 件 = stale 1 (= #3、closed のまま滞留) + trivial 3 (= #69/#70/#79) + 重い判断 1 (= #65 merge 判断) + その他。human の一括 pass 1 回で列の半分が消える構成だった
- Ready=0 / Inbox=37 — triage と UAT の両端で human が制約
- **Completion Check は実装 AI の自己申告を証跡として受理** (= completion-check-routine SKILL.md:160-166 の項目 (d))。独立証跡が要求されていない
- completion-check cron の登録状態は reader 間で矛盾 (= 登録済み説 / 手動運用説) が未解決 — 要 1 コマンド確認 (= 2026-07-03 追記: scheduled-tasks MCP で確認、 登録済み・enabled=true・cron `7-59/15 * * * *` を確定。 「登録済み説」が正、 Issue #84)
- 良い証跡: Completion Check が実 defect (= #65 の未 push commit) を検出した実績、#3 の失敗教訓が limn epic #71 に明示的制約として artifact 化、running/long-running label が #72 の stall を自動検出

## 5. 外部比較

### 5.1 利用度 (= 機能棚卸しの結論)

power user 水準を超えて利用している: skills / subagents (tool 制限 + model 段階化済み) / Agent Teams (experimental) / 高度な hooks (= prompt 型 Stop hook + Sonnet judge、StopFailure asyncRewake) / MCP / 第三者 marketplace の plugin / cron / worktrees / 自作 statusline (ccmeter) / 自作 eval harness。per-skill 回帰 gate は community でも最希少 (= offline eval 実施は組織でも 52.4%)。

未利用で価値のあるもの:

| 未利用 | なぜ効くか |
|---|---|
| headless / CI (= claude -p、GitHub Actions) | 全 gate が 1 台の Windows 機依存。組織移植の最大リスク |
| harness / backlog リポの CLAUDE.md | SoT 警告 (= skillshare dir 編集禁止) が private auto-memory にのみ存在し、CI / 他人 / cloud session から不可視 |
| plugin + private marketplace 配布 | 組織が install / version pin / update できる公式経路 |
| Codex plugin の review chain 配線 | 導入済みだが未接続。same-model review の盲点共有を解消する設定作業のみ |
| output styles / .claude/rules/ 等 | 低優先。global CLAUDE.md の常時 context 分をオフロード可能 |

### 5.2 方向性 (= 5 つの賭けの判定)

| 賭け | 判定 |
|---|---|
| skill-chain routing (= verdict 制) | ✅ 公式の比例原則 (= 計画は diff 1 文で説明できるタスクでは省略) の明示ルール化。整合 |
| Issue 駆動外側ループ + human UAT | ✅ HN 合意 (= 「ボトルネックは生成でなく検証」「checkpoint 付き orchestration > 全自動」) と一致 |
| eval-before-compress | ✅ error-analysis-first 文化と一致。skill-creator の eval/benchmark productization を先取り |
| skillshare 配布 | ⚠️ multi-vendor 動機は正当、Claude 向けチャネルとしては plugin/marketplace への分割を推奨 |
| 実 product (limn) での dogfooding | ✅ 長期運用 harness の公式 guidance (= progress artifact / 1 feature ずつ) を独立に再実装 |

### 5.3 eval 統計の業界比較

- 現状 (= 5 case/skill + baseline + push gate) は個人実務を上回り、skill-creator の 3-16 case 水準と同等
- 成熟チームとの差: single-trial では temp 0 でも pass@1 が 2.2-6.0pp 振れるため noise と回帰を区別できない / judge の human label 較正なし / case が worked example からの複写で failure-sourced でない / 100% pass case の飽和処理なし
- 参照枠: pass@k (= best-case) vs pass^k (= 一貫性)、binary rubric > Likert、eval 工数の 60-80% はデータを見る作業

## 6. 直近の作業キューへの評価

### 6.1 計測トラック (= Epic #62 配下)

順序原則 (= measure-before-compress) は正しく、動機も 3.7x token 見積誤差という定量的失敗に根差す。個別判定:

| Issue | 判定 | 根拠 |
|---|---|---|
| #66 context 消費実測 | **即実行可** | execution-ready、UAT 基準が直接実行可能。未実装の段階 1 を正確に埋める |
| #67 未使用 skill 検出 | **前提 spike を単独先行** | 「hook で skill 呼び出しを観測できる」前提が未検証 (= PostToolUse-on-Skill か transcript parse が必要な可能性)。#66/#68 との batch 実行は前提崩壊時に無駄が波及 |
| #68 重複の構造 vs 削減余地 | **deprioritize 推奨** | 結論は既に settled (= 構造的重複は irreducible、削減上限 10-15%、docs/wip + memory に記録済み)。維持コストつき classifier は over-instrumentation バイアスの典型候補 |

- 圧縮 strategy A (= 4-6 scripts + 新 agent + hooks で ~19% 削減) は保留のまま **kill criterion の文書化を推奨** (= 例: 計測された context 圧が routing 失敗を実際に起こした場合のみ採用)
- 計測対象は always-on 面 (= descriptions / CLAUDE.md / hook 出力) が高利回り。skill 本体 1,948 行は on-invoke でしか load されない

### 6.2 limn epic (= #71/#72)

- #71 の slicing は良質 (= 縦切り / UAT 可能 / 失敗 Issue #3 の教訓を明示的制約として本文に埋め込み)
- #72 は 6h+ 無 commit で long-running label — scope 過大の証明ではなく **dead-session シグナル**。中間 commit 慣行が無いため stall と slow を区別できないのが真の問題
- #64/#65 境界の教訓: #65 の成果物の大半が #64 の branch 内で先に構築され、2 sessions + 1 bounce が 64 LOC に費やされた。親 branch の scope が育った時点での子 Issue re-cut が有効だった

## 7. judge 間矛盾と解決 (= 検証・批評フェーズの成果)

### 7.1 triplicated protocol の companion file 抽出 (2 judge が推奨) → 棄却

検証が、この案は **user が fresh-context 原則違反として既に却下した設計判断**であることを特定 (= skill 間重複は各 skill が単独 context で完結するための構造)。推奨を差し替え: 重複は許容したまま、**drift-check lint (= mismatch guard)** で size 表分裂のような独立 drift だけを機械検出する。

### 7.2 description 切断の機構 (= 「長さ制限」説 → 棄却)

3 judge が「~850 字 render limit + 長さ budget」を推奨したが、検証が実測で **YAML ` #` comment parse** を特定 (= §3.2)。即効修正は quoting。長さ budget は独立の hygiene 課題として docs/wip/testing-metrics-baseline の description 圧縮 pilot が既にカバー。

### 7.3 #68 deprioritize vs 重複削減推奨の相反

eval・観測性 judge は「#68 の答えは settled」、context 経済性 judge は「重複抽出は common-standard」— 同じ証拠から逆の結論。解決: 重複の**総量削減**は settled (= 上限 10-15%、やらない)、重複の**drift 検出**は未着手 (= やる価値あり)。2 つは別の課題。

## 8. 本評価がカバーしなかった領域 (= 批評フェーズの指摘)

1. **自律 gh 操作のセキュリティ**: write 権限つき gh を持つ LLM が 15 分毎に untrusted な issue body を読む構造の prompt injection / credential scope / blast radius。2026-06 に claude-code-action の injection 事例が公表されており、組織導入で最初に問われる領域
2. **コスト会計**: cron + 必須 dual-spawn の $/token が未計量 (= process 重量は ceremony 面でのみ監査)
3. **memory 層の drift**: MEMORY.md / ai-memory も unversioned な SoT 面 (= ATTRIBUTION.md の stale 化が既に実例)

## 9. 改善案一覧 (= 4 分類、優先順)

すべて提案であり、採否と実施順は Issue (= sat0-hir0/backlog) 側で管理する。「検証」列は敵対的検証の verdict。

| # | 分類 | 改善案 | 検証 | 根拠 |
|---|---|---|---|---|
| 1 | minimum-guardrail | agent 名 drift 修正 (= reviewer/qa-verifier/docs-curator → 実在名) + skill 参照 agent 名の実在 grep lint | valid | 中枢 gate の締結。lint が再発防止 (= §3.1) |
| 2 | minimum-guardrail | 全 skill description の ` #` quoting 修正 (= harness + backlog) | valid | issue-execute の trigger 面が現に破壊中 (= §3.2) |
| 3 | minimum-guardrail | needs-fix label 作成 + architecture-vision.md dangling 参照 ~10 箇所の置換 | valid | 差し戻し経路が初回で破綻 (= §3.5) |
| 4 | minimum-guardrail | DRY_RUN を chezmoi source へ同期 + completion-check cron 登録状態の確認 | valid | chezmoi apply が本番 gate を silent に無効化 (= §3.6) |
| 5 | minimum-guardrail | size 表の SoT 一本化 (= task-slicing 所有、task-routing は参照) | valid | delegate-slice 閾値の判定が現に食い違う (= §3.7) |
| 6 | common-standard | Done = merged-to-main の定義 (= または unmerged-branch label) + stale branch 5 本の整理 | valid | board Done と git merged の独立変動を締結 (= §3.4) |
| 7 | common-standard | Awaiting UAT の一括 human pass (= stale drop / trivial sign-off / 重い判断の分離) | valid | 1 pass で列の半分が消える構成 (= §4) |
| 8 | common-standard | Completion Check に独立証跡 1 点 (= fresh test run の exit code か gh run link) を要求 | valid | 自己申告受理は rubber-stamp 点 (= §4) |
| 9 | common-standard | eval gate の正名化 (= fixture-sync lint と改称、失敗時メッセージを「diff をレビューしてから re-baseline」へ) + description lint (= ` #` 検出 + 長さ warn) を gate に追加 | valid | 偽の安心と訓練された bypass の解消 (= §3.3) |
| 10 | common-standard | harness-design.md §3 に実装状態列 (= implemented / prompt-text-only / not-built) | valid | 紙の防御層を組織 rollout に持ち込まない (= §3.8) |
| 11 | common-standard | harness / backlog リポに CLAUDE.md (= repo 地図 / eval-gate 契約 / SoT 警告 / board 語彙) | valid | CI・他人・cloud session の前提 (= §5.1) |
| 12 | common-standard | eval-gate を GitHub Actions で PR 実行 (= off-laptop 化)。Issue 起動型を足す場合は injection hardening 必須 | valid | 単一マシン結合の解消 = 組織移植の前提 (= §5.1) |
| 13 | team-discretion | XS / docs-only delegate-single の dual-review 免除 (= Lead spot-check に緩和、M+ は維持) | valid | 未証明 ceremony の軽量化。§3.1 修正とセットで「締結された軽い gate」へ |
| 14 | team-discretion | prepare-uat package のサイズ条件化 (= XS は 3-4 要素の軽量形、常時空の Handoff block 削除) | valid | 13 block 固定は ceremony (= process 重量監査) |
| 15 | team-discretion | wave-status の state path を per-vendor 自己判定へ (= finish-task の既存パターン流用) + 第 2 vendor での 1 回の実走 or Claude-only と明記 | valid | 可搬性主張の事実化 (= §3.8) |
| 16 | team-discretion | dead MCP 参照の除去 (= architect の context7 / fullstack の serena) | valid | silent 劣化の解消 (= §3.8) |
| 17 | team-discretion | skillshare の出力に git-hosted private plugin を追加 (= Claude 向け配布層、skillshare 自体は cross-vendor build 層として維持) | valid | 組織が採用可能な配布経路 (= §5.2) |
| 18 | personal-experiment | 計測トラックの順序調整 (= #66 先行 / #67 は前提 spike 単独 / #68 deprioritize) + strategy A の kill criterion 文書化 | valid | §6.1 |
| 19 | personal-experiment | 圧縮着手前の最小行動 eval 1 回 (= task-routing 5 case を N=3 で実走し verdict のみ diff、held-out 2-3 case 追加) | valid | single-trial の noise と回帰を区別する最安の方法 (= §5.3) |
| 20 | personal-experiment | 読み取り専用 assess 型 request の routing 出口追加 (= 第 4 verdict か明示 SKIP 注記) | valid | 「評価して」型 request が両入口から fall-through (= 本評価依頼自体が実例) |
| 21 | personal-experiment | Codex cross-model review を delegate-slice wave か pre-UAT に配線 | valid | plugin 導入済み、設定のみ (= §5.1) |

## 10. 評価の限界

- reader 間矛盾 1 件が未解決のまま (= completion-check cron の登録状態、§4) (= 2026-07-03 追記: 確定済み、 §4 参照)
- 外部比較の「業界水準」は Web 調査 (= 35 ソース) に基づく snapshot であり、一次検証はしていない
- 本評価自体も AI 生成物。「確定」以外の項目 (= スコアの絶対値、業界比較の位置づけ) は判断材料であって証明ではない

## 11. 再評価 (2026-07-03、同一手法 19 agents)

Epic #80 の改善 wave (= 20 票、全 merge) 完了後に §1 と同一手法で再採点した。judge には「改善が実在するかを自力検証してから採点」を課し、prior score を anchor に証拠がある場合のみ変動させた。

### 11.1 スコア delta

| 次元 | 07-02 | 07-03 | 変動根拠 |
|---|---|---|---|
| context 経済性 | 3 | 3 | 計測 tooling 実在 (= #66 が 55,988 token を定量化) と CLAUDE.md 2 本の lean さは加点、常時 context の増加 (= description 1,388→1,684 字) が相殺 |
| routing 信頼性 | 3 | **4** | 昨日の 3 defect (= agent 名 / YAML 切断 / assess fall-through) が **lint という締結付き**で解消。assess 出口は本再評価 session 自身が実証 |
| eval・観測性 | 2 | **3** | L2 runner が実在し実行した (= committed baseline に実コスト $2.74 と honest fail 1 件 = 捏造困難)。正名化・CI・metrics も実在。他 5 skill 未カバー / judge 未較正で 4 には届かず |
| 外側ループ自動化 | 3 | 3 | 設計は 4 相当 (= 差し戻しプロトコル実戦検証済み) だが、runtime が pre-wave の skill で稼働していた (= §11.2) ため据え置き |
| process 重量 vs 価値 | 3 | **4** | ceremony 削減 (= XS 免除 / UAT 軽量形 / 空 Handoff 削除) と「全 gate が実 defect 対応 1:1 + stdlib 高速 + 締結済み」の両立 |
| platform 適合 | 3 | 3 | MCP wildcard / per-vendor path / CI / plugin build は実在。deployed==SoT が backlog 層で不成立 (= §11.2) のため据え置き |

### 11.2 再評価が検出した新規 defect (= 全て検出同日に修正済み)

1. **merged ≠ deployed の再発 (1 層下)**: backlog 3 skill の deployed が pre-wave commit で凍結 (= 宙参照が runtime に残存、#93 tiering 未反映)。原因は backlog checkout が stale branch に居たこと。→ main resync + hash 検証で解消
2. **wave 自身が持ち込んだ矛盾 3 箇所**: task-routing の免除 ceiling (= docs-only ≦ S) が Boundary と plan template で欠落、size 数値の再掲。→ 文言修正
3. **description の実 render cap ~1,535 字**: 07-02 の「長さ制限説は棄却」は半分だけ正しかった (= YAML `#` と render cap の両方が実在)。1,684 字に育った task-routing が再切断。→ body 重複部を削り 1,459 字化
4. **CI が direct main push を素通り**: → `push: branches: [main]` trigger 追加

### 11.3 残課題 (= 検証 valid のみ)

- **セキュリティ盲点の継続**: §8.1 (= write 権限 gh × untrusted issue body の cron) は改善 wave でもチケット化されず未対応
- L2 の no-verdict-line 率 21% の root-cause (= L2 signal を信頼する前提条件)
- DRY_RUN=false への切替の数値基準 (= dry-run verdict と人間判断の一致実績は蓄積済み)
- §17 差し戻しプロトコルの prepare-uat 要素 9 への配線 / description 長 warn の lint 化 / 第 2 vendor 実走 / cost 会計

### 11.4 教訓の追加

- 「文書化された gate の機械的締結」はスコアに反映された (= routing / eval の +1 は全て lint・実行・CI 由来)
- 大規模 wave は wave 自身が矛盾を持ち込む (= 3 箇所)。行動 eval と再評価が回収装置として機能した
- 配布 drift は 1 層直しても下の層で再発する。**merged → 配布 source → deployed の全層 hash 検証**が必要

## 12. 第 3 回評価 (2026-07-03 午後、同一手法 19 agents)

Epic #106 の残課題 wave (= 7 Issue #107-#113、全て Awaiting UAT / 9 open PR / 全 MERGEABLE) 実装後に §1 と同一手法で 3 回目の採点。採点規則を厳格化し、**main + deployed の landed state のみを採点、未 merge branch の改善は pending delta として分離** (= ハーネス自身の Done ≠ merged / deployed == SoT doctrine を評価にも適用)。judge の全 score / 新規 defect は敵対的検証を通過済み。

### 12.1 スコア (据え置き、上昇頭打ち)

| 次元 | 07-02 | 07-03 朝 | 07-03 午後 | 変動根拠 |
|---|---|---|---|---|
| context 経済性 | 3 | 3 | 3 | deployed==main sha256 一致は加点だが、常時 description 4,902 字・機械的長さ予算が main に不在 (lint は未 merge PR #24 のみ) |
| routing 信頼性 | 3 | 4 | 4 | anchor 4 の締結 3 件 (lint-agent-refs / frontmatter-lint exit 0 / description 1,459<1,535 render 実測) は main で有効。新規 3 hygiene 欠陥は verdict を反転せず 4 維持、5 には届かず |
| eval・観測性 | 2 | 3 | 3 | L0/L1 30/30・L2 baseline は main 実在だが、root-cause 修正・再 baseline・cost 会計は全て未 merge。push-to-main CI が赤で main signal が汚染 |
| 外側ループ自動化 | 3 | 3 | 3 | 配布 drift 解消 (9 skill hash 一致) は加点だが、中枢 gate は DRY_RUN=true 休眠・本日 wave が文書化経路を bypass・補償 CI 3/3 赤で相殺 |
| process 重量 vs 価値 | 3 | 4 | **3** | ceremony 削減 (XS 免除 / 軽量 UAT 形) は健在だが、「残した gate が実際に効く」前提が 3 点で崩れた (下記)。self-correction による健全な差し戻し |
| platform 適合 | 3 | 3 | 3 | 構造は正しいが、deployed==SoT が agents 層で機械破綻 (junction ENOENT)、chezmoi apply が stale mirror へ巻き戻し |

**総括:** 上昇は routing / eval の機械 gate 締結が牽引したが、landed state は据え置きに転じた。理由は明確 — **実質すべての改善が 9 open PR + 3 direct-push の branch 側に滞留し、main では逆に配布・CI 層の実 defect が露呈**。「機械 gate は landed したが、それらが本番で回る証拠 (status 遷移 / green CI / 文書化経路の完走) が 1 つも無い」天井に達している。

### 12.2 新規 defect (= 全て敵対的検証 valid、main/deployed 実在、§3/§11 未収録)

1. **push-to-main CI が構造上 3/3 赤 (最重要、process に PRIMARY 帰属)**: §11.2-4 が「direct main push 素通りを塞ぐ」として追加した `push: branches:[main]` trigger は、push event で `github.base_ref` が空になり future-plans lint step が `git diff origin/..HEAD` で fatal (exit 2)。追加以降の main push 3/3 (1a5d16a / be0c2d4 / da372d3) が全て failure、PR run は 6/6 success。**fix として足した gate が一度も pass せず**、赤い main CI を常態化する。修正 PR は存在しない。(eval / outerloop / platform でも波及計上されたが根本原因は 1 つ)
2. **deployed agents が file-targeting junction で runtime から読めない (platform に PRIMARY 帰属)**: `~/.claude/agents/*.md` 6 本が「ファイルを対象とする Windows junction」(junction はディレクトリのみ有効) で、Node (= Claude Code runtime) の `readFileSync` が全 6 で ENOENT。deployed==SoT が agents 層で機械破綻。**この junction は 06-29 作成 = 07-02 以前から存在した latent defect** であり、過去 2 run の platform 3 が両方甘かったことの露呈。MEMORY の「0/N linked は表示バグ・実害なし」認識とも矛盾する。
3. **dotconfig main の stale agents mirror が chezmoi apply 地雷 (platform に PRIMARY)**: `dot_config/skillshare/agents/` に 06-26 時点の 6 agent 古コピーが track されたまま (#82 YAML quoting fix / #95 dead MCP 除去の**前**)。`chezmoi status` = MM ×6、routine な `chezmoi apply` が live agents を修正前へ巻き戻す。§3.6 の RESOLVED 宣言 (07-02) は file-class を DRY_RUN に限定した部分解消で、mechanism 全体は未解消だった。
4. **本日の残課題 7 Issue が外側ループの文書化経路を bypass (process/outerloop)**: prepare-uat → Completion Check → cron 精査という設計経路を通らず、AI 代行 pick + 検証コメントのみで status が Awaiting UAT へ proxy 遷移 (🎯 UAT package も 🔍 cron verdict も 7 Issue 全てに不在)。対照の #82/#86 は full trail を持つ。**ハーネス自身が最重量 ceremony を skip した = 文書化 gate が enforce されていない直接証跡。**
5. **PR lane を 3 回 direct-to-main push で bypass (process)**: 1a5d16a / be0c2d4 / da372d3 が direct-to-main commit、うち 2 件が skills/ を変更 = PR-event でしか走らない deterministic CI (frontmatter / agent-ref / fixture-sync lint) を skill 変更が素通り。
6. **L2 run_set 互換キーに extractor version が無い (eval)**: `eval-behavioral.py` の compare は model / cli_version / trials の 3 項のみで互換判定し、VERDICT_RE 変更前後の baseline を silently comparable 扱い = regex 修正跨ぎの回帰比較が「行動変化」と「抽出変化」を区別できない。
7. **hygiene 残債 group (routing に PRIMARY、context と cross-reference・score 不動)**: task-slicing の description/body 起動条件矛盾 (SKIP 1-4 files vs body ≥2 files) / Step 3-4 が Worked example 配下に構造迷子 / ADR 例示名 drift ($adr-proposal vs $propose-adr)。いずれも verdict を反転せず context 予算 regression も無い hygiene debt。
8. **doc drift (eval)**: harness CLAUDE.md の eval-gate 契約と wip test-strategy が、main に landed 済みの L2 behavioral runner を反映せず「eval は skill を実行しない / L2 未実装」のまま。観測 stack の自己記述が実態より弱い。

### 12.3 盲点 (どの次元も未採点)

- **issue-status.ps1 が無テスト**: DRY_RUN=false 化で board を動かす唯一のコードに Pester/単体テスト 0 件。flip 瞬間に機械検証ゼロで本番化される。
- **security 露出面が main で稼働中**: #107 (injection 対策) は実装済みだが unmerged。一方 cron heartbeat は本日実走 (#72 stall 検出) = 自律 gh 経路自体は live。対策は branch・露出面は main という gap を誰も grade していない。
- **main 発散の管理不在**: 9 open PR + 3 direct-push が積み上がる一方、merge ordering / main 発散を指標化する次元が無い (process 射程外)。
- **chezmoi 地雷の recovery runbook 不在**: 巻き戻り後の復旧手順が配布層に存在するか未確認。検出のみで recovery 経路が無い。
- **評価ハーネス自身の meta コスト / anchor-lock バイアス未採点**: 2 日 3 回の評価プロセスの運用コストと、judge が自 run の anchor を hold する構造 (= §3.6 の RESOLVED 誤宣言のような早期誤判定を次 run へ伝播させる) が未計測。

### 12.4 教訓の追加

- **スコア上昇は「機械 gate の landed」で説明できるが、天井は「それが本番で回る証拠の不在」で決まる**。routing/eval の +1 は締結由来で正当。だが 4 次元が 3 連続据え置きなのは、gate が休眠 (DRY_RUN=true) / 空回り (CI 3/3 赤) / 自己 skip (wave の経路 bypass) しているため。**次の上昇には branch の merge ではなく「DRY_RUN=false 化 + push-CI green + 次 wave の CC 経路完走」という運用実績が landed で必要。**
- **配布 drift の mechanism は file-class ごとに個別解消が要る**。§3.6 の DRY_RUN 解消は agents mirror には及ばず、単発の RESOLVED 宣言は禁物 (別 file-class で再発する)。
- **「補償として gate を足す」時は、その gate が実際に pass する経路を 1 回確認する**。push-CI は fix として記録されたが一度も pass せず、赤い CI が「main CI は無視してよい」を訓練していた。
- **self-correction は健全に機能した** (process 4→3 差し戻しは同日午後の反証で 1 サイクル是正)。ただし latent defect (agents junction、06-29 発生) を 2 run 見逃した事実は、evaluation の網羅性に構造的な穴があることを示す。

## 13. 第 4 回評価 (2026-07-03 深夜、残課題 wave の merge 反映後)

第 3 回の残課題 (9 open PR) を全て merge し、DRY_RUN=false を本番化、chezmoi の stale agents mirror 地雷を除去した後に再採点。今回は改善が landed したため加点対象になったが、「landed かつ exercised (= 自コマンドで動作再現)」と「merged-but-unproven (= 着地は確認したが動作証跡なし)」を厳密に区別した。全 judge スコアは敵対的検証を通過。

### 13.1 スコア (3 次元が +1、landed の反映)

| 次元 | 07-02 | 07-03 朝 | 07-03 午後 | **07-03 深夜** | 上げ根拠の質 |
|---|---|---|---|---|---|
| context 経済性 | 3 | 3 | 3 | **4** | EXERCISED — description 長 lint が実データ (task-routing 1,459 字) で WARN 発火を自コマンド再現 |
| routing 信頼性 | 3 | 4 | 4 | **4** | lint 層は exercised だが deployed-runtime 層 (agent 不読) が未成立で 5 不可 |
| eval・観測性 | 2 | 3 | 3 | **3** | L2 runner は exercised (18 unittest pass) = 加点だが、doc-drift + CI 赤 + agent 不読が 4 を阻む |
| 外側ループ自動化 | 3 | 3 | 3 | **3** | 心臓 3 核 (本番 cron 実走 / CI green / agent 読取) が未達で 4 連続据え置き |
| process 重量 vs 価値 | 3 | 4 | 3 | **4** | EXERCISED — warn-first の非ブロッキング設計 + §17 狙い撃ち fix が「重さ相応」を実測 |
| platform 適合 | 3 | 3 | 3 | **4** | gate-tooling 層は exercised だが distribution 層 (junction) + CI 健全性が broken |

**landed-state vector 推移:** 07-02 `[3/3/2/3/3/3]` → 07-03 朝 `[3/4/3/3/4/3]` → 午後(strict) `[3/4/3/3/3/3]` → **深夜(4th) `[4/4/3/3/4/4]`**。

### 13.2 exercised による前進 (真の capability) vs merged-but-unproven

- **EXERCISED (加点正当、自コマンド再現済み):** description 長 lint (exit 0 + task-routing 1,459 字 WARN 再現、閾値 1,400/1,535) / L2 no-verdict fix (VERDICT_RE 全形式捕捉 + 18 unittest pass) / agent-ref lint + frontmatter parse (exit 0)。配布チェーン main→hub→deployed の sha256 byte-identical も確認。
- **MERGED-BUT-UNPROVEN (着地確認のみ、動作証跡ゼロ = 加点保留):** §17 prepare-uat 配線 (テキスト存在は確認、差し戻し発火 0 回) / injection hardening #114 (merge 確認、悪意入力を弾いた証跡なし) / **DRY_RUN=false 本番 cron (byte-identical deploy 確認、post-flip の production marker (↩️/✅/⚠️) が 0 件、flip から時間未経過)**。

### 13.3 merge しても残った defect (敵対的検証 valid)

1. **push-to-main CI が構造的に RED (未 track)**: merge 後も未修正。最新 push run (aaf5491/#26) が failure = `github.base_ref` が push event で空 → future-plans lint が `git diff origin/..HEAD` で fatal (exit 2)。**merge 直後の #23-25 の push run は `cancelled` (concurrency cancel-in-progress で pre-empt) であり green ではない** — main-push CI に緑 run が 1 つもない。landed した gate 群は PR-time でしか enforce されておらず、main deploy-time では緑シグナルを出していない。
2. **deployed agents が Node runtime から読めない (別 root cause で未修正)**: `~/.claude/agents/*.md` 6/6 が file-targeting junction で `readFileSync` が ENOENT。今回の mirror 修正は**内容の巻き戻り**を直したが、**junction link-mode の不読**は別問題。root cause は dotconfig の `13-skillshare-sync.ps1.tmpl` が agents に `--mode copy` を適用していないこと (copy-mode は scripts extras のみ)。chezmoi apply ごとに self-reproduce する。
3. **eval 自己記述の doc-drift 生存**: CLAUDE.md「eval は skill 本文を実行せず」と test-strategy「L2 未実装 (#97)」が、landed 済みの L2 runner を反映していない。
4. **Done ≠ closed の再発**: #107-#113 が board-Done だが GH issue state=OPEN (merge での auto-close 経路なし)。

### 13.4 次に上げるための具体条件 (critique の優先順)

1. **push-CI fix (最優先・最小工数・最大波及)**: eval-gate.yml の future-plans step に push-vs-PR guard (`if: github.event_name == 'pull_request'` か push 時 `--base origin/main~1` フォールバック)。YAML 数行で main 上の全 gate が初めて緑シグナルを出し、eval / platform / process / outer-loop の 4 次元に横断的に効く。**eval 3→4 / platform 4→5 の最有力トリガー。**
2. **本番 cron を実 1 周させる (outer-loop 3→4 の唯一の鍵)**: Completion Check 列に実 Issue を 1 件置き cron slot を 1 周させ、`✅`/`↩️` の本番 prefix comment を board に残す。心臓が landed-but-unproven → proven に変わる。誤判定リスクがあるので初回は 1 件で観測。
3. **agent junction を copy-mode 化**: skillshare の agent link mode を copy に変える (or dir-junction 化)。runtime が deployed path から agent を読めるようになり、routing の spawn 下流 / eval の agent 観測 / platform の distribution が同時成立。**platform 4→5 の必須条件。**
4. **doc-drift 解消 (低工数)**: CLAUDE.md と test-strategy を landed 実態に更新。

### 13.5 教訓の追加

- **「merged」と「exercised」は別物**。今回 3 次元 (context / process / platform) が上がったのは lint/L2 を**実際に走らせて再現できた**から。§17 配線・injection・本番 cron は着地したが動作証跡がゼロで、加点しなかった。次 eval で cron が 1 周した瞬間に outer-loop が +1 する「予約された上げ幅」が積まれている。
- **CI が構造的に赤いまま gate を積むと、PR-time でしか守られない**。push-CI 1 本の修正が landed gate 群の main-time enforcement を一括で有効化する — 最小工数で最大波及の典型。

## 14. 第 5・6 回評価 (2026-07-04)

### 14.1 第 5 回 (2026-07-04 午前、36 agents)

Epic #106 の残課題を全 merge した直後に採点。vector = **[4/4/3/4/4/4]** — 第 4 回 `[4/4/3/3/4/4]` から **outer-loop 3→4** の 1 次元上昇。実体: completion-check の rubber-stamp が independent-evidence 必須 (§2(d) fresh 再実行 + exit code) に置換 + DRY_RUN=false 化 + §17 body-append 配線 + 両 cron firing。生存 defect (severity 順): ①**critical** deployed agents 6/6 が file-junction で Node loader ENOENT (delegate chain 実機不発)、②③**high** trigger 契約 / prose→case drift が eval の diff 対象外、④**medium** push-to-main CI 赤、⑤-⑦ low。前回宿題 3 件 (push-CI / 本番 cron 1 周 / agent copy-mode) は当時 0/3 未完了。

### 14.2 第 6 回 (2026-07-04 午後、18 agents)

第 5 回の最重要 2 defect (①critical agents junction / ④push-CI 赤) を本セッションで解消・**実機実証**した後に採点。vector = **[4/4/3/4/4/5]** — 第 5 回から **platform 4→5** の 1 次元上昇。

| 次元 | 5th | 6th | 判定 |
|---|---|---|---|
| context 経済性 | 4 | 4 | 維持 (doc-drift + task-routing desc 1,459/1,535 で headroom 76 字) |
| routing 信頼性 | 4 | 4 | 維持 (trigger-flip が EXIT=0 silent + L2 unwired が 5 を阻む) |
| eval・観測性 | 3 | **3** | judge の 3→4 提案を **verify が反証** (fixture-sync は元々 push で success、green 化の実体は非 eval の future-plans lint)。6 eval 連続据え置き = 恒常ボトルネック |
| 外側ループ自動化 | 4 | 4 | 維持 (forward `✅` marker 未実証 / Done≠closed が #107-#113 で固着) |
| process 重量 vs 価値 | 4 | 4 | 維持 (future-plans lint が lefthook にも main-push にも無く direct push 無防備、low) |
| platform 適合 | 4 | **5** | **state-of-the-art 到達**。2 judge 独立 5 + verify 追認 |

**platform 4→5 の根拠 (全て command 再現、exercised):**
- 5th の critical (agents junction ENOENT) 根絶: `node fs.readFileSync` で `~/.claude/agents/*.md` 6/6 OK・全件実ファイル (LinkType null)
- 配布チェーン source→hub→deployed の raw sha256 が 6/6 byte-identical (三方 parity)
- sync script に 3 重防御 (`--agent-mode copy` + junction purge + `sync --force`)、自己再生欠陥を根絶
- main-push CI が全 6 eval で初めて green (push run 28697606611 = SUCCESS、直前 aaf5491 = failure の before/after 確認)

### 14.3 生存 defect (敵対的検証 valid、eval を縛る)

1. **trigger 契約が eval の diff 対象外 (high)**: `eval-regression.py` の comparator が baseline/current 双方を `.get('expected_output',{})` に slice するため、`expected_trigger`/`expected_no_trigger` の drift が不可視。case-1 の trigger を task-routing→intent-clarify に反転しても `exit 0 "no drift"` を実測。fields は baseline writer に追加されたが comparator が拡張されていない。
2. **SKILL.md prose→case source drift が fixture-sync 素通り (high)**: prose の変更を読む L1 script が無く、case の `source:` field を消費するものも無い。task-routing の L2 run のみが検出しうる。
3. **L2 coverage gap**: `eval-behavioral.py` は task-routing のみ (他 5 skill に baseline なし)、on-demand (どの gate にも未配線)、main baseline は no-verdict-line 率 20.8% + case-level fail 1 件。
4. **eval doc-drift**: CLAUDE.md L30 が今も「eval は skill 本文を実行せず」(L2/behavioral 言及ゼロ)、test-strategy L51 が「L2 未実装 (#97)」— landed 済みの `eval-behavioral.py` (skill を実行) と矛盾。

### 14.4 軌道と次に上げる鍵

6 eval / 3 日の vector 推移: `[3/3/2/3/3/3]` → `[3/4/3/3/4/3]` → `[3/4/3/3/3/3]` → `[4/4/3/3/4/4]` → `[4/4/3/4/4/4]` → **`[4/4/3/4/4/5]`**。

- **総括: 1 次元 (platform) が天井到達、1 次元 (eval) が恒常ボトルネック、4 次元が「健全だが 5 未満」の踊り場。**
- **harness は defect-fixing の天井に接近**。platform=5・routing content は near-SoTA・delegate 実行路も修復済み。残る 5 の障壁は correctness defect でなく「harness が自分の routing/skill 挙動の正しさを証明する能力」= eval-flywheel の深化。
- **次に上げる鍵 (最優先): eval 3→4** — `eval-regression.py` の comparator を `expected_output` slice でなく baseline_entry 全体を diff するよう広げ、trigger 契約を L1 で assert する (最小の code 変更で恒常ボトルネックが動く)。
- **outer-loop 4→5**: board-Done 到達時に gh issue を自動 close する主体を作り Done≠closed を解消 (#107-#113 が board-Done ∧ gh-OPEN で固着)。forward path 自体は既に exercised。

### 14.5 教訓の追加

- **「2 つ直った」が全次元に波及する誘惑を切り分ける**。agents readable + push-CI green は両方 exercised な本物だが、効いたのは platform (junction 根絶) だけ。push-CI green の実体は非 eval の future-plans lint の spurious failure 停止で、eval に効く fixture-sync は直前 push でも既に success だった。**step-level で before/after を割らないと「2 defect 解消 → 複数次元 up」という過大評価に流れる。**
- **監査 tool 自体が defect を隠す**。`gh project item-list` の default paging では最新 harness issue (#107-#118) が 1 ページ目から落ち、`--limit 300` で初めて Done≠closed 乖離が surface する。「解消した」の誤結論は naive query 由来。
- **score theater を正しく拒否できた**。#118 (本番 cron を実 1 周させ forward 証跡を作る) は、人為的お膳立てが必要と判明し close。cron の本番稼働は 03:30Z の #116 bounce (実 board move) で既に自然実証済みだった。

## 15. 第 7 回評価 (2026-07-06、残課題 wave の merge 反映後)

第 4-6 回で「次に上げる鍵」とした 2 項目 (eval 3→4 の trigger 契約 assert、outer-loop 4→5 の Done≠closed 解消) が実装・merge された後の再評価。手法は 5 次元 (前回 defect / 今回変更 / 多層防御 / 自律運用 / board hygiene) を qa-expert で並列 assess → high/critical finding を敵対的検証 → confirmed のみ roadmap 化。実 HEAD `146268d`。

### 15.1 このサイクルで land した変更

- **#127**: `issue-execute` に product→repo 解決 (Issue 操作=backlog 固定 / コード操作=着地 repo、cross-repo branch は `gh --branch-repo`)。「入口集約 × 着地分散」を §4.1 に明文化。
- **#129**: `issue-execute` を git worktree ベース化 (`~/code/.worktrees/<repo>/<N>`、`--name` 決定論命名 + stdout 捕捉)。同一 repo 同時着地の衝突を解消。
- **#122**: `done-close-routine` 新設 (Done→gh close 自動化 + #129 の worktree cleanup 兼任、cygpath -u で drive形/msys形を統一する安全弁)。outer-loop 4→5 の鍵。
- **#119**: `eval-regression.py` の comparator を trigger 契約まで拡張 (`CONTRACT_FIELDS` + `contract_view()`)。eval 3→4 の鍵。

### 15.2 前回 5 大 defect の決算

| defect | 判定 | 証跡 |
|---|---|---|
| agent 名 drift | 解消 | `lint-agent-refs.py` 実装・pre-push 配線・pass |
| YAML # 切断 | 解消 | `check-frontmatter-yaml.py` 実装・pass (task-routing description は非 blocking warning 圏に残るが実害なし) |
| needs-fix 不在 | 解消 | label 定義 + 過去実績確認 |
| eval 非実行 | 改善 | #119 で trigger 契約の穴を code 変異テストで fix 実証 (`--skill all` = 30/30 pass, drift 0)。L2 behavioral は実装済みだが今回未再実行 (CI 未配線は API key 回避で明示、運用規約上妥当) |
| Done≠merged | **問題設定の縮小** | §16 ADR で「Done⇒PR merged」保証を意図的に放棄し「Done⇒gh closed」のみに絞った。`done-close-routine` が board の「Done かつ OPEN」乖離を実データでゼロにした。PR merge の最終責任は人間側へ明示的に戻る |

### 15.3 landed but unproven (= 今サイクルの共通弱点)

**4 変更すべてコード/ロジックは正しく実装され main に land 済みだが、実運用で発火した証跡 (exercised) はゼロ**:

- #122 done-close: cron enabled (`3-59/15`) だが自動 close の形跡なし。直近の close は全て人間の手動一括操作。
- #129 worktree 化: skill 本文は実装済みだが、実 session (#72/#119/#122) は全てこのコミット以前に開始し**旧パス (main clone / `backlog-wt-N`) で発火**。
- #127 repo 解決: land 済みだが exercised 未確認。
- #119 eval trigger: 4 変更中**唯一 exercised に近い** (code 変異テストで fix が機能することを実地確認、Lead の UAT でも裏取り)。

→ **多層防御の implemented は依然 2/12** (層1 役割分離 / 層12 UAT 品質)。#122/#129 は score theater 回避のため層数の格上げに算入しない (exercised でないため)。

### 15.4 confirmed defect と roadmap 判定

敵対的検証で high の headline severity を再評価した結果、機能破綻レベルの confirmed defect は無し。以下は事実 confirmed だが実質 severity と対応方針:

| defect | 実質 severity | roadmap | 根拠 |
|---|---|---|---|
| Back pressure gate (層2) が prompt-text-only | medium | 様子見 | test 基盤の無い harness 本体に汎用 gate は投資対効果低。test は着地 repo (limn=Rust / ow-my-coach=TS) の責務 |
| running ラベル孤児 #72 (Ready のまま running+long-running 残留) | low-med | 即対応 | 真因は人間の give-up path (In Progress→Ready drag) が label/branch を掃除しない + pick 除外が `needs-human` のみで stale running を見ない latent gap。実害は intermittent な pick 空振り (self-limiting)。ラベル手動剥がし 1 分 + 設計修正は別 spike |
| backlog/CLAUDE.md L37 の stale drift + dangling §13 参照 | low | 即対応 | 「#122 削除実装は未 land」と誤記 (実際は land 済み、5 時間差で追い越された stale) + 「harness §13 leak window」が dangling (§13 は真逆の記述)。descriptive であり directive でないため cleanup パイプラインは壊れない。1 行修正 |
| 旧命名 worktree 5 件残存 + `.worktrees/harness/119-uat` 空 dir | medium | 様子見 | 安全弁が仕様通り旧命名を fail-safe skip。過渡期残骸で cron 挙動に波及なし。手動 remove で足りる |
| done-close の scheduled-tasks MCP runtime prompt 同期未確認 | medium | spike 先行 | dotconfig の絶対ルール (SKILL.md 編集後 `update_scheduled_task` 同期) が file-based 評価では検証不能。過去 #6 で同期漏れが leftover として実発生。次サイクルで実機 spike |

### 15.5 前回「未確定」項目の決算

- **#113 コスト会計**: 未確定でなく**確定済み**。`cost-accounting-2026-07-03.md` に実測値。
- **#109 DRY_RUN 切替基準**: 確定済み。completion-check の `DRY_RUN=false` 化は 8/8 一致の実績で本番化済み。

### 15.6 軌道と次に効く 1 手

- **総括: static な整合性は前回より高い** (Done≠OPEN ゼロ、cron 7 個の位相衝突なし、running ライフサイクル整合、eval 30/30 pass)。だが**今サイクルの品質判断の唯一の空白は「実装は正しいが exercised 証跡ゼロ」に集約される**。
- **次に効く 1 手: 「次回 cron 発火サイクルの実機観測」を 1 回通す**。(a) done-close が実 Done Issue を close + worktree 撤去する瞬間、(b) #129 worktree 化が次の実 pick で `~/code/.worktrees/<repo>/<N>` を実際に使うか、(c) scheduled-tasks MCP の runtime prompt が dotconfig source と一致するか (#6 同期漏れ再発チェック)。この 3 点を 1 セッションで潰せば、防御層の格上げを**初めて証跡ベースで主張できる**。Ready の product:harness Issue (#120-126) を 1 件流せば (a)(b) は自然に達成される。
- **本質的な設計変化**: defect4 の「問題設定の縮小」= 「board が Done でも main に merge されているとは限らない」を運用者が常に意識する前提へ。個人開発の統制粒度としては妥当だが、Done の意味が変わった。

### 15.7 教訓の追加

- **「landed」と「exercised」を厳格に割る**。今サイクルは 4 変更が全て merge されたが、実運用で発火したのは #119 のみ (しかも code 変異テストで、本番 cron 経由ではない)。merge を capability の前進と数えると過大評価になる。防御層の格上げは exercised を条件にする (前回 §13.2 の踏襲を今回も適用)。
- **敵対的検証が high の過大評価を正した**。board-hygiene #72 と new-changes 2 件は事実 confirmed だが、headline の因果 (「Ready で stuck 警告が出続け他の pick を阻害」) は反証され、実害は doc-accuracy と intermittent な空振りに限定。severity は敵対的検証を通してから確定する。
- **read-only 評価の原理的限界を明示する**。cron の runtime prompt 同期・実発火・worktree 実使用は file-based では埋められない。「実機 spike が要る」と正直に marking し、静的整合性の高さで exercised を代替しない。

## 16. 第 8 回評価 (2026-07-20、評価手法のメタ評価を適用 + 14 日無人運用の自然実験)

第 7 回 (07-06) と本 run の間に、評価プロセス自体のメタ評価を実施した (= `docs/wip/harness-meta-evaluation-2026-07-20.md`。過去 7 run の信頼性を H1-H5 で監査)。本 run はその改善提案を適用した初の評価。加えて 07-06 以降 14 日間は評価が停止し cron のみが走ったため、この期間を無人運用の自然実験として監査した。手法: 24 agents (= ledger 機械抽出 1 / evidence probe 7 (うち自由探索 2 + 14 日 runtime 監査 + security 構造監査) / 6 次元 judge / 対称 verify 6 / 独立 2 vector + 突合 / 盲点批評)、subagent 計 ~246 万 token、約 45 分。実 HEAD は評価時 main = `101b6c0`。

### 16.1 適用したメタ評価提案 (= 手法改革の開示)

| 提案 | 適用内容 |
|---|---|
| 脱結論化 CTX (提案 1) | Lead CTX から RESOLVED / VERIFIED / 上げ候補名指しを排除。過去 doc の記述は「主張」として渡し、採点に使う場合は自力 spot-check を必須化 |
| 機械台帳 (提案 5) | 持ち越し項目を過去 2 doc から severity 問わず機械抽出 (= 40 件、Lead の手選び廃止)。run 7 型の無音脱落を構造的に防止 |
| 旧台帳決算 (提案 6) | run 7 のスコア廃止で未決算だった繰延 (= eval 3→4 予約等) を本 run で全件決算 |
| transcript 経路 (提案 2) | exercised 判定に cron transcript 探索を必須化 (= 過小計上の防止) |
| 対称 verify (提案 10) | verify に過小方向 (= proven な前進の見落とし) 検査を新設 |
| 2 判断制 (提案 12) | 最終 vector を独立 2 判断 + 突合で確定 |
| script 保全 (提案 4) | 評価 workflow script 6 本を `docs/wip/eval-workflow-scripts/` に保全 |

### 16.2 スコア (= landed-state vector)

**vector = [context 3 / routing 4 / eval 4 / outer-loop 4 / process 3 / platform 4]**。独立 2 判断が全 6 次元で一致 (= disputes 0)。run 6 `[4/4/3/4/4/5]` からの delta: **eval +1 / context -1 / process -1 / platform -1**。

| 次元 | run 6 | 8th | 変動根拠 (= 全て自力 command 再現) |
|---|---|---|---|
| context 経済性 | 4 | **3** | 悪化 4 本柱が全て CONFIRMED: directive doc の stale が稼働中の自動化と逆内容 (= 修正 issue すら不在) / 無人 loop に context short-circuit がなく no-op が O(board) で燃える / description 予算超過 WARN が 14 日 live / memory 鮮度判定が placebo で汚染。供給系 (= 3 層 sha256 parity / §0 搭載 / eval green) 無傷で 2 は回避 |
| routing 信頼性 | 4 | 4 | 初の無人 end-to-end exercised (= `f05e64d9` の完全 Y-trace) + L19 決算漏れ回収が上げ材料だが、bypass 3/7 (= 中核契約「ALWAYS invoke BEFORE Edit/Write」の silent 違反、検知機構なし) が 5 を阻む。bypass 対象は XS/S の docs/config で misroute 実害ゼロのため 3 も不成立 |
| eval・観測性 | 3 | **4** | 6 run 据え置きの中核疑問「gate は本番で発火するか」に直接回答: pre-push 実ブロック 2 回 (= `d2c6df8e` の "push blocked" 実文字列) + 変異 kill (= regressions 1 / exit 1) + 31/31 pass。**L03 の予約上げ幅を正式決算** (= run 7 が無音消却したもの)。5 を阻む 3 盲点 (= source drift 素通り / --override 履歴非永続 / lineage 保全不全) は両 verify が独立再現 |
| 外側ループ自動化 | 4 | 4 | L04 完全成立 (= done-close の自動 close を transcript で確認) + #127/#129 の full lifecycle exercised で機構面は 5 相当。だが 14 日自然実験が露呈した機能面 high 4 件 (= escalation 誤診 / CI-green deadlock / backoff 不在 / 着地経路断絶) で相殺。「人間不在自体は減点しない」原則を適用 (= cron は正しく停止・通知、境界外 mutation 0) |
| process 重量 vs 価値 | 4 | **3** | 窓境界の会計に依存しない構造欠陥 3 点 (= CI-green deadlock で実装 chain を 2 回廃棄 / kill criterion が自己測定不能 / 飢餓時 backoff 不在) が run 6 に無かった exercised な負の証跡 |
| platform 適合 | 5 | **4** | run 6 の 5 根拠 4 点は再実測で全て復元 = 劣化ではない。下げ主因は run 6 当時**不可視だった**新規確定: 配布計装 (= CLAUDE_MEMORY_AUTOMATED) が設計時点から placebo (= automated marker 0/456) + §0 配備不均一 + 破壊操作 denylist 不在。機能不全が memory 計装層に限局する事実が 3 を防ぐ |

vector 推移: `[3/3/2/3/3/3]` → … → run 6 `[4/4/3/4/4/5]` → **8th `[3/4/4/4/3/4]`**。**score theater なし**: eval の上げは実ブロック証跡、context/process/platform の下げは 14 日運用が露呈した exercised な負の証跡に基づく。

### 16.3 台帳の全件決算 (= 提案 5/6 の成果、無音脱落ゼロ)

機械抽出した 40 件 (L01-L40) を全件決算: **回収 14 / 残存 18 / 繰延 7 / 消却 1**。過去 run が「無音脱落」させた項目が本 run で初めて明示決算された。主な決算:

- **回収**: L03 (= eval 3→4 予約、実ブロック証跡で決算)、L04 (= done-close 実発火、cron 初回自動 close を transcript で確認)、L06/L07 (= #129 worktree / #127 cross-repo が exercised)、L19 (= size 表 SoT は既に一本化済みだった = 決算漏れ)、L13 (= run 5 の無名 defect ⑤-⑦ を保存 script `0b7eb511` から全文復元 = 「復元不能」の反証)。
- **繰延 (= 恒常制約による)**: L08 (= injection 敵対的陽性 proof が read-only 制約で再繰延)。**これは無音消滅の新しい形**: 恒常制約 + 恒常繰延。次回は繰延回数を追跡し、N 回で「専用 setup を組む or 消却理由を明記」を強制する規則が要る。
- **narrative 訂正 (= git 実測)**: L05/§15.3 の「直近 close は全て人間の手動一括操作」は**事実誤認**。突合で `1f48814` の author date = 2026-07-14 を確認し、cron 自動 close (07-06T11:12Z) の 8 日後の執筆で、**commit 時点で既に虚偽**と確定。§15.3 に正誤表が要る。

### 16.4 14 日無人運用の自然実験 (= 過去 7 run が測らなかった signal)

「14 日無人」の実体は **machine-off 9-10 日 + 飢餓空転 + 実生産 ~2 夜**で、cron 稼働率は **~24%**。全 rate はこの 3 状態を分母分離しないと無意味。この期間が露呈した、系の律速に関する事実:

1. **系の bottleneck は AI 能力でなく人間応答時間**。Ready 列 3 件が全て needs-human で pick pool が飢餓し、~546 cron session が board 前進ゼロ (= 成果は警告コメント 1 件、消費は cache_read 274M token)。UAT 5 件が 14-18 日滞留、PushNotification 2 通が 13 日未応答。**人間側を測らない評価は系の律速を測っていない**。
2. **唯一の人間向け interface が誤情報を運びうる**。07-15 の staleness escalation が #124 の needs-human 封止理由を誤診 (= repo mismatch と報告、実際は CI-green deadlock)。助言どおり label を剥がすと既知の無限ループへ回帰する。**「行動の正しさ」と別軸の「人間向け要約の正しさ」は全 8 run で未測定 — 誤った escalation は沈黙より有害**。
3. **飢餓下でも cadence 不変で固定燃焼**。生産ゼロの 24h 稼働日でも ~$146/日。飢餓検知時に cadence を落とす backoff が無い。稼働 ~6 日で概算 ~$550/14 日。
4. **CI-green deadlock**: #124 の acceptance 契約 (= CI green) と CI trigger 設計 (= push:main + PR のみ) が構造矛盾で、AI が自己完了不能。pick→bounce を繰り返し needs-human で封止された。契約↔workflow の整合 lint が無い。
5. **判断の非永続化**: #72 の skip 判定が 24 分後に逆転 pick され実装 chain 1 本を廃棄。stateless な 15 分 run が毎回判断を再導出する系では、skip 判断の永続化率が測れるべき signal。
6. **健全側の証跡**: 境界外 board 操作 0 / injection 陰性 37/37 / §0 guard は backlog 3 routine の 794 run に 100% 搭載 / dedup 実効 (= escalation spam 0)。**「AI が暴走した」のではなく「人間が bottleneck になった」構図**。

### 16.5 confirmed defect (= 最終、severity 順)

| # | defect | sev | dim | roadmap |
|---|---|---|---|---|
| 1 | 07-15 escalation が #124 の封止理由を誤診 (= 唯一の人間 interface の内容が誤り、従うと無限ループ回帰) | high | outer-loop | escalation 生成時に needs-human 付与コメント原文の引用照合を必須化 |
| 2 | acceptance 契約 (= CI green) と CI trigger 設計 (= PR のみ) の構造矛盾 = AI 自己完了不能 deadlock | high | outer-loop | branch push / workflow_dispatch の CI 経路追加、または branch 段階の CI green を契約から除外 |
| 3 | cron 産修正 branch 4 本の着地経路欠落 = PR 未作成 14 日、無人期間の新規コードは CI 検査ゼロ | high | outer-loop | draft PR 自動作成を boundary 内に入れる、または当面は人間 UAT 1 回 |
| 4 | 飢餓 backoff / short-circuit / aging 再送の不在 = 稼働日 ~$146/日 固定燃焼 | high | process | 飢餓検知時 cadence 逓減 + Done 全 CLOSED の安価な先判定 + aging 再通知 |
| 5 | 破壊的 gh/git denylist 不在 + gh token 過大 scope (= 11 repo 到達) | high | platform | scope 縮小 + settings.json deny に gh/git 破壊系追加 (= 人間 10 分級)。**run 1 から 8 run 未解消の最古 defect** |
| 6 | CLAUDE_MEMORY_AUTOMATED 計装が設計時点から placebo (= automated 0/456、Bash export が hook process に届かない) | high | platform | hook process から観測可能な経路 (= marker file 等) へ変更 + 修正 issue 起票 |
| 7 | SKILL.md prose/case source drift が eval gate 素通り (= 変異 exit 0 を両 verify が再現) | high | eval | 修正 `check-case-source.py` (241 行) は完成済み、#120 の UAT 消化 + merge のみで着地 |
| 8 | 評価 lineage の三重保全不全 (= run 7 記録が未 merge branch のみ / meta doc + script が untracked / §15.3 虚偽未訂正) | high | eval | 評価 branch の PR 化 + untracked 一式 commit + §15.3 正誤表 |
| 9 | directive doc の stale が稼働中の自動化と逆内容 (= backlog/CLAUDE.md L37 + harness-design §13、修正 issue 無し) | med | context | docs-only 1 行修正 ×2 の即日 PR。既存 doc の実数 stale lint は起票 |

**最古 defect の生存機序 (= H5 の実証)**: #5 の security defect が run 1 から 8 run 生き延びた一因は、platform 次元が配布 parity (= 恒常健全) と security (= 恒常不健全) を同居させ、健全な半分が平均で不健全な半分を救い続けたこと。

### 16.6 手法改革の feedback (= メタ評価提案は機能したか)

- **脱結論化 CTX: ほぼ機能**。L05 の再導出が過去 doc の性格付けを覆し、L13 で他 4 次元の「復元不能」を routing が独力で覆した = 結論継承の遮断を実証。**残る漏れ**: Lead CTX の「14 日を無人運用の自然実験として扱う」という framing 自体が未検証の結論で、probe が「実は稼働 ~6 日」と訂正するまで全 probe を anchor した。**時間的 framing も evidence pointer 化の対象**。
- **機械台帳: 機能、ただし新死角**。40/40 決算・無音消滅ゼロ達成。だが L08 の「恒常制約 + 恒常繰延」という新しい無音消滅の形が露呈 (= 16.3 参照)。
- **対称 verify: 実効あり**。under 方向 5 系統の発見 (= L03/L19/L13 + pre-push 実ブロック + drift 修正 branch 自律起草) と over 方向の訂正 (= 13 日→6 日) が両立し theater ではない。
- **2 判断制: 本 run の最弱部**。A/B が全 6 次元一致・disputes 0。両判断は**同一 probe pool を消費**しており独立なのは解釈だけ。完全一致は「独立確認」でなく上流相関の期待値で、第 2 判断が買った弁別情報は実質ゼロ。probe subset を判断間で分けるか、片方を明示的に敵対役 (= 各次元 ±1 を主張) にし、dispute 率を手法の健全性 metric として追跡する。恒常 0 なら 1 判断 + verify に縮退してコスト回収。

### 16.7 盲点・次元セット・次に効く鍵

- **本 run の盲点 (= 次 run で probe 化)**: (1) **対話 session 層が完全欠落** — 本 run の exercised は全て cron transcript 由来で、harness の本来の入口 (= 対話での task-routing 発火 / intent-clarify の生涯 exercised 回数 ≈ 0) を一度も probe せず。しかも harness dir の session はほぼ評価 run 自身 = 評価が自分の証跡 store を汚染。(2) **memory 生成物の内容監査**: ai-memory の最終 commit = 06-28 (= 22 日 commit ゼロ)、「Basic Memory を Git 管理」の SoT 前提が事実上死んでいる可能性。(3) **escalation の配達検証**: 「人間が 13 日未応答」は通知が届いたことを未検証で前提化 (= 「無視した」と「届かなかった」は修正策が違う)。(4) 非 Claude vendor の消費実態がゼロ検証 (= user の学習目標に直結)。
- **次元セットの応力**: vector が 3-4 に収束し弁別力が落ちた。本 run の最大発見群 (= human↔AI interface) を所有する次元がなく outer-loop と process に分散した。提案 (= 次元数は増やさず再分割): outer-loop を「自律機構」と「human-interface / throughput」に割る / security は新次元でなく **platform への hard cap** (= 未解消 high security がある限り platform ≦ 3) / economics (= idle burn) はスコアでなく毎 run の tracked metric / memory は context の exercised 面と定義。
- **次に効く鍵**: (1) Awaiting UAT 3 件 (#120/#123/#125) + needs-human 3 件の人間 clearance = 系の律速の解除。(2) escalation 硬化 (= 引用照合 + aging + backoff) + memory placebo 修正。(3) denylist + token scope 縮小 + injection 陽性 probe。

### 16.8 教訓の追加

- **無人運用の律速は人間側にある**。14 日で board 前進ゼロの原因は AI の故障でなく人間 gate の飽和。**人間応答時間・escalation 内容の正確性・idle burn rate を測らない評価は、系の律速を測っていない** (= 過去 8 run が一度も持たなかった signal class)。
- **duty-cycle 正規化なしの rate は無意味**。「14 日無人」は machine-off 9-10 日を含み、稼働率は ~24%。加えて transcript の mtime は drift する (= 旧 session が後日 touch される) ため、内部 timestamp のみを正とする測定規則が要る。
- **placebo は当時不可視な形で landed する**。CLAUDE_MEMORY_AUTOMATED は設計時点から機能していなかったが、run 6 の platform 5 判定時には不可視だった。**スコアの下げが必ずしも劣化を意味しない** — 過去の過大評価の露呈でもある。
- **2 判断制は probe を分けないと独立でない**。完全一致は独立確認の証拠でなく上流 (= 同一 probe pool) 相関。判断の多重化は入力を分けて初めて弁別情報を生む。
- **メタ評価 → 適用のループは機能した**。本 run の最大の前進 (= eval のボトルネック突破 + 過小計上の是正 + human-interface signal の発見) は、いずれも前段のメタ評価が指摘した欠陥への直接対処から生まれた。
