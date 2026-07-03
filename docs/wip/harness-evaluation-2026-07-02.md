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
- completion-check cron の登録状態は reader 間で矛盾 (= 登録済み説 / 手動運用説) が未解決 — 要 1 コマンド確認
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

- reader 間矛盾 1 件が未解決のまま (= completion-check cron の登録状態、§4)
- 外部比較の「業界水準」は Web 調査 (= 35 ソース) に基づく snapshot であり、一次検証はしていない
- 本評価自体も AI 生成物。「確定」以外の項目 (= スコアの絶対値、業界比較の位置づけ) は判断材料であって証明ではない
