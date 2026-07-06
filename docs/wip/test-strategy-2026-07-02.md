# harness テスト戦略 (2026-07-02)

> 本 doc は docs/wip (= 検討資料)。ここに書くのは判断材料と規約のみで、**採否 / 実施順はすべて GitHub Issue 側で管理する** (= #80 配下 + #97 / #91 / #88 / #66)。本 doc に日程・順序を書かない。

## 0. TL;DR

- 現行 eval/ は **fixture 同期 diff** (= 手書き YAML 同士の比較) であり skill を一切実行しない。SKILL.md の prose 変更は無検証で通る (= eval・観測性 2/5 の根因)。この gate は fixture-sync lint へ改名して維持する (#88)。挙動 test へは拡張しない。
- 挙動検証は **verdict-contract test** として最小導入済み (= `eval/scripts/eval-behavioral.py`、#97 landed): task-routing の verdict 3 値のみを assert、runner は `claude -p` の薄い wrapper、N=3 多数決、held-out 2-3 case、**変更前 baseline 必須**。
- verdict 境界に触れる skill 編集 (#85 / #92 / #98 / 圧縮 refactor) は behavioral baseline の取得を先行条件とする。name-only rename (= #81) は不要。#82 (= description 復元) は trigger 面を変えるため trigger-baseline 必須 (§9)。
- 常設機構はすべて trigger / cost / kill criterion を持つ (§8)。hook 段には決定的 check のみを置き、LLM 実行は on-demand と PR の opt-in に限る。

## 1. スコープと非目標

対象:
- skills/*/SKILL.md の**挙動 contract**。対象 skill は task-routing のみ (= 出力が 3 値 verdict + 固定形式の判定行で、唯一 transcript から決定的に assert できる)。他 skill への拡大は failure-sourced (§6) に従い、管理は Issue 側。
- 既存 eval/ 資産の位置づけ再定義 (§3)。

非目標と理由:

| 対象外 | 理由 |
|---|---|
| agent .md (reviewer / qa-verifier 等) の E2E | 出力が自由記述で客観 contract がなく、assert が LLM judge 頼みになる (= 判定コスト > 信号)。誤動作は finish-task の主張 vs 証跡分離で拾う方が安い |
| backlog cron / Projects 遷移の挙動 | harness repo の外 (= backlog repo の運用領域)。本戦略の資産では観測できない |
| multi-turn workflow 全体の実走 (= finish-task の全工程等) | 1 run が長く flaky 要因が多層で、pass/fail の信頼度を確保できない |
| Y-trace 文言の品質 | 自由記述の意味評価は L3 judge の注釈対象。pass/fail 対象にしない |
| cross-skill 重複の削減 | 確定済: fresh-context 原則により重複は仕様 (§10) |

## 2. 現状資産 (= 何があって何が動いていないか)

| 資産 | 実態 | 根拠 |
|---|---|---|
| eval-run.py | **skill を実行しない**: run_case() が case の expected_output を deepcopy して actual_output に入れる。mode='static'、match は常に "match" | eval/scripts/eval-run.py:33-52 |
| eval-baseline.py | expected_output の凍結 copy を eval/baseline/ へ (git 管理)。snapshots/ は .gitignore | .gitignore:5 |
| eval-regression.py | baseline vs 現 cases/*.yaml の再帰 diff (= **手書き fixture 同士**)。tri-state pass/fail/acknowledged、--override は drift した case のみ再凍結、exit 0/1/2 | eval/scripts/eval-regression.py:28-49,146 |
| Ollama judge | qwen3:14b、temperature 0、120s timeout。--judge 指定 + 構造 diff 非空 + 疎通時のみ発火。結果は**注釈のみで exit code を変えない** | eval_common.py:100-152、eval-regression.py:109-116 |
| eval-gate.py | lefthook pre-push。SKILL.md 変更 → 当該 skill、agents/*.md 変更 → --skill all。常に judge なし | lefthook.yml:4-10、eval-gate.py:141-159,162-173 |
| case 資産 | 6 skill x 5 = 30 case + 30 baseline。schema: id / input / expected_trigger / expected_output (+ 任意 expected_no_trigger / source)、id 昇順必須 | eval_common.py:69,85-96 |
| **死んでいる field** | expected_trigger / expected_no_trigger は snapshot / baseline へ copy されるだけで、**どの script も assert しない** | eval-run.py:45-46 |
| 再利用部品 | eval_common.py (= stdlib + PyYAML のみ): load_cases / validate_all / judge_compare / write_yaml。run_case() が actual_output 生成の単一点 | eval/scripts/eval_common.py |

注: tri-state classify (#65) は main (= aa914fe) に merge 済。未了扱いにしない (board 上は Awaiting UAT だが code は入っている)。

結論: 「SKILL.md の prose を書き換えても、case YAML を触らない限り何も fail しない」が現状。gate が守っているのは fixture の整合であって skill の挙動ではない。

## 3. テスト層の定義

| 層 | 検知するもの | 検知できないもの | trigger | cost | 現状 |
|---|---|---|---|---|---|
| L0 static lint | case schema 崩れ (= 必須 field 欠落 / id 非昇順)、禁止語句 (check-future-plans.py) | 挙動全般 | regression 実行時の --validate / finish-task 内 | 秒 | 実装済 |
| L1 fixture-sync lint (= 現 gate、#88 で改名) | baseline と cases/*.yaml の乖離 (= fixture の編集漏れ / 意図しない編集) | **skill の実挙動。SKILL.md prose 変更は素通り** | pre-push (SKILL.md / agents/*.md 変更時のみ発火) | 数秒 | 実装済 |
| L2 behavioral verdict | SKILL.md 編集による verdict 変化、trigger 精度 (= expected_trigger の初 assert) | 判定理由の質、multi-turn 挙動 | on-demand (= SKILL.md の意図的変更の前後、§7) | run set あたり haiku < $2 / 5-15 分 (§8) | 実装済 (= `eval/scripts/eval-behavioral.py`、#97 landed。 対象は task-routing のみ) |
| L3 semantic judge | 構造 diff の意味的等価性 (= 言い換えか実質変更かの注釈) | 判定の正否 (= 注釈のみ、exit code 不変を維持) | on-demand --judge | local GPU (VRAM 競合注意) | 実装済 |

L1 は L2 の代替ではない (= 検知対象が直交する)。L1 を挙動 test に拡張しない、が確定済の判断 (#88)。

## 4. 行動 eval の設計 (= verdict-contract test)

**assert 対象**: task-routing の判定行から抽出した verdict ∈ {Lead-direct, delegate-single, delegate-slice} のみ。Y-trace の文言・根拠分類は assert しない (#97 と同スコープ)。

**抽出規約**: regex は `判定:\s*(Lead-direct|delegate-single|delegate-slice)` とし、直後の size 表記 `(XS|S|M|L|XL)` と `|` 以降のテキストを許容する (= SKILL.md:90-91 の実例は `判定: delegate-single (S) | ∵ ...` 形式)。判定行が固定形式 (SKILL.md:83-92) なのは Y-trace が出る場合のみで、SKILL.md:92 の escape valve (= 自明な Lead-direct は Y-trace 省略可) があるため無条件には決定的でない。よって: (a) 判定行が見つからない run は **extraction-fail** として verdict mismatch と区別して記録する — trial としては fail 扱いだが、trigger-fail (= Skill tool_use event 不在) とも区別する。(b) case input を escape valve 圏に入れない (input 規約参照)。

**case format**: 既存 eval/cases schema をそのまま使う。expected_output は verdict 1 key に絞る。

```yaml
- id: 6
  input: "auth module の login flow をリファクタして (対象 5 files、UI と API を跨ぐ)"
  expected_trigger: task-routing
  expected_output:
    verdict: delegate-slice
```

**file 配置と L1 との相互作用**: train case は eval/cases/task-routing.yaml に追記し、**同一 commit で eval-baseline.py により baseline を凍結する** (= baseline 欠落 case は eval-regression.py:146 で exit 1 になり pre-push を塞ぐ)。held-out case は eval/cases/ の**外** — `eval/holdout/task-routing.yaml` — に置く: eval_common.py:44 の `CASES_DIR.glob("*.yaml")` が cases/ 配下の全 YAML を skill として拾うため、cases/ 内に置くと agents/*.md 変更時の `--skill all` fan-out (eval-gate.py:141-159) が held-out の baseline 欠落で push を塞ぐ。holdout/ は L1 の対象外。

**input 規約**: 発話に file 数 / 規模の文脈を必ず含める。task-routing は size 見積で delegate-single / delegate-slice を分岐する (SKILL.md:69-73) ため、文脈のない発話は verdict が原理的に不定 (= flaky の温床)。Lead-direct case も escape valve 圏 (= README typo / 1 行 rename 級の自明変更) を避け、Y-trace が必須になる程度の実質 (= 対象 file の特定 + 変更内容) を持たせる。

**既存 case 1-5 の書き換え**: 現行 input の多くはこの規約を満たさない (= case 1 は escape valve の例そのもの、case 2 は verdict 曖昧の注記入り eval/cases/task-routing.yaml:26-27、case 3 / 5 は規模文脈ゼロ)。初回 baseline run set の前提として input を規約準拠に書き換え、`source` field に書き換えの旨を追記する。期待 verdict は変えない。input の変更は L1 を発火させない (= eval-regression は expected_output のみ比較、eval-regression.py:91-92)。

**起動方式**: 既定は自然発話を prompt にそのまま渡し、stream-json の Skill tool_use event で task-routing の発火を確認する (= expected_trigger をここで初めて assert)。trigger noise と verdict logic を切り分けたいときのみ明示起動 (= prompt 先頭に skill 名を埋め込む) を使う。

**試行数と pass 基準**:
- N=3 を既定とし、**多数決 verdict == expected** を pass とする。境界 case (= size 表の閾値付近) は N=5。
- pass^k (= k 回全一致) は棄却: 2-6pp の観測 noise 下では偽陽性を増幅し、「変更していないのに fail」を量産する。多数決は noise と regression を分離する (#97 の設計根拠)。
- 3 値割れ (= 1/1/1) は fail 扱いで quarantine 行き。

**flaky 規約**: 連続 2 run set で majority が入れ替わる case は quarantine (= gate 判定から除外)。対処は 2 択 — input の文脈を具体化するか、SKILL.md 側の判定基準の曖昧性として Issue 化する。quarantine の放置は §8 の kill criterion で拾う。

**baseline-before-modification (必須規約)**: SKILL.md を意図的に変更する前に、現行版で 1 run set を取得して結果を残す。評価は「変更前 majority vs 変更後 majority」の verdict 単位 diff。単発試行同士の比較は禁止 (= 単発では noise と regression を分離できない)。

**再現性の固定**:
- **model 固定**: runner 既定は haiku。正確な model id は runner 内の定数として固定し、全 run set 記録に model id + CLI version を echo する。両者が一致しない run set 同士の diff は runner が拒否する。sonnet は深掘り用の opt-in flag。model 未指定は不可 (= 本環境の headless 既定 model は haiku でなく、単発 $0.296 の実測: docs/wip/claude-p-probe-2026-07-02.json)。
- **CLI version 固定** (= 現 2.1.195)。
- `--max-budget-usd` を runner 既定に入れる。`--max-turns` は 2.1.195 の `claude -p --help` に存在しない (= 本環境で確認済) ため使わない。
- **skill 読込 (runner 前提条件)**: `--setting-sources project` (= 個人 ~/.claude の skill / CLAUDE.md を混入させない) を使うが、task-routing は user scope (= ~/.claude/skills、skillshare 配布) にしか存在せず harness repo に .claude/ はない。このままでは skill が読み込まれず全 case が trigger-fail する。runner 実行前に project scope の source を junction で用意する: `New-Item -ItemType Directory C:/Users/hiroki/code/harness/.claude` の後 `New-Item -ItemType Junction -Path C:/Users/hiroki/code/harness/.claude/skills -Target C:/Users/hiroki/code/harness/skills` (= repo の編集中 SKILL.md がそのまま読まれ、個人 skill 排除の目的も保たれる)。run set 冒頭の smoke assertion (= task-routing の Skill tool_use event を 1 回観測) を通過するまで trial を数えない。

## 5. tooling 判定

| 候補 | 実行形態 | Windows | verdict assert | 追加依存 | 評価 |
|---|---|---|---|---|---|
| skill-creator 行動 eval | live session 内で Lead が prose 手順を実行 (= subagent pair + grader)。headless command なし | 可 (subagent 駆動) | 可 (assertion grading) | plugin (未 install、session skill としては利用可) | 再現性が Lead の手順追従に依存し、決定的 gate にならない。runner script は同梱されない |
| skill-creator run_eval.py | `claude -p` subprocess | **不可** (= select() が Windows の pipe 非対応) | 不可 (= trigger 判定のみ) | 同上 | ubuntu CI / WSL 限定。測るのは発火率であって verdict でない |
| **`claude -p` 薄い runner (自作)** | CLI subprocess、--output-format json / stream-json | **可** (v2.1.195 でローカル検証済。保存 artifact: docs/wip/claude-p-probe-2026-07-02.json) | 可 (= result から判定行を regex 抽出) | **ゼロ** (eval_common.py を import) | **採用** |
| promptfoo (anthropic:claude-agent-sdk) | Node tool。skill-used assertion / --repeat / SDK version 要件は**一次資料未確認 (未検証)** | 可 (未検証) | 可 (未検証) | promptfoo + Agent SDK | SDK 駆動で CLI 固有挙動は対象外。新 tool は運用破綻点の確認前に採用しない方針に反する (= 棄却理由は未検証 cell に依存しない) |
| raw API + DeepEval | Python | 可 | 可 | DeepEval | skill の読込 / 展開を自前再実装する必要があり不採用 |

**推奨: `claude -p` 薄い runner**。根拠: (a) 環境で動作検証済かつ追加依存ゼロ、(b) eval/cases schema と eval_common.py (= load_cases / validate_all / judge_compare) をそのまま流用でき、fixture-sync lint と case 資産を共有できる、(c) skill は headless でも読み込まれる (= `--bare` を付けず、かつ §4 の junction 前提条件を満たした場合。`--setting-sources project` 単独では user scope の task-routing は読み込まれない) ため実挙動をそのまま観測できる。

skill-creator からは harness でなく**規律**を借りる: 2-3 case から始める / assertion は初回 run 後に足す / 両構成で常に pass する非判別 assertion は捨てる / 既存 skill の改善では「旧版 snapshot」を baseline にする (= no-skill 比較でなく)。

**vendor-neutral 境界**: 可搬資産は case YAML (= 発話 + 期待 verdict、tool 非依存の形式) と verdict contract 自体。runner は 100 行級の交換可能な adapter として扱い、runner 固有の記法を case に持ち込まない。

## 6. case 管理規約

- **failure-sourced growth**: 新 case の供給源は「実運用の誤判定 / UAT 差し戻し / eval fail」に限る。網羅目的の一括作成をしない (= 判別力のない case は保守コストだけ増やす)。
- **saturation**: SKILL.md 編集を跨いで全 pass が続き、編集でも差が出ない case は判別力なしと見なして退役させるか held-out へ転用する。判定は run 記録で行う。
- **held-out discipline**: 2-3 case を held-out として train 側と別ファイル (= eval/holdout/、配置規約は §4) で管理し、SKILL.md 編集 session のコンテキストに**入れない** (= description 最適化が train case に過適合しても検出できるようにする)。編集中に held-out を読んでしまったら、その case は train 側へ降格し、held-out を failure-sourced に補充する。
- 既存規約 (= id 昇順 / source provenance / expected_no_trigger は list) は eval_common.py の validate をそのまま維持する。

## 7. trigger 規約

| タイミング | 実行内容 | 規約 |
|---|---|---|
| commit | なし (現状)。置く場合も決定的 lint のみ許容 | LLM 実行禁止 |
| pre-push | fixture-sync lint (= eval-gate.py、judge なし、exit 0/1。下層の eval-regression.py は 0/1/2) | SKILL.md / agents/*.md 変更時のみ発火。数秒で終わること |
| PR (CI) | fixture-sync lint を ubuntu-latest で再実行 (#91)。paths filter: `skills/**/SKILL.md` + `agents/*.md` (= local gate の agents → `--skill all` fan-out、eval-gate.py:141-159 を CI でも落とさない) | LLM 不要なので API cost ゼロ。挙動 eval は必須 check にしない |
| on-demand | L2 verdict run set / L3 --judge / skill-creator 行動 eval (深掘り時) | SKILL.md の意図的変更の前後 (§4 baseline 規約)、および誤判定の発生時 |

原則: **hook 段は決定的 + 数秒のみ**。LLM 実行 (= L2 / L3) は人が明示的に起動する。理由: Ollama の VRAM 競合 (= ゲーム起動中に CUDA malloc fail の実績) と `claude -p` のコスト / 所要時間 (= 5-15 分) を push の前提条件にすると、gate 迂回の動機を作る。

## 8. コストと kill criteria

| 機構 | trigger | cost | kill criterion |
|---|---|---|---|
| fixture-sync lint | pre-push | 数秒 | --override / acknowledged が無検討で常態化し diff review が形骸化したら (= 目安: 直近 10 発火の 8 割以上が即 override)、削除して PR review に一本化 |
| L2 verdict run set | on-demand | 1 run set (= 5-8 case x N=3): haiku 5 case ≈ $1.0 / 8 case ≈ $1.6、sonnet $1-5、5-15 分 (逐次)。数値は client 側推計 | 直近 3 回の SKILL.md 編集で regression も判断材料も一度も出さなければ縮小 / 廃止。quarantine が case の過半に達したら設計をやり直す |
| L3 Ollama judge | on-demand --judge | local GPU のみ (API cost ゼロ)。VRAM 競合注意 | 注釈が採否判断に引用されない状態が続いたら削除 |
| CI fixture-sync (#91) | PR | Actions 無料枠内 (LLM なし) | 単一 Windows 機依存の懸念が別手段で解消されたら削除 |

cost の注記: 保存済み実測点は docs/wip/claude-p-probe-2026-07-02.json (= 2.1.195、model 未指定 = 環境既定、skill 非発火の単発、$0.296 / 4.4s。`total_cost_usd` は client 側推計であり課金実測ではない)。haiku 単発 $0.066 / 5.2s は artifact 未保存の参考値。skill 発火を伴う run は 20-40s / $0.05-0.10 (haiku) と仮置きする (= 単発実測は skill 非発火の下限であり、上表の 5-15 分 (逐次) はこの仮置きに基づく)。clean 環境では prefix が変わるため、**予算化の前に対象環境で model 固定して 1 回実測する**。runner 既定の `--max-budget-usd` で上限を機械的に固定する。

本戦略は「不安解消のための常設機構」を認めない。上表に載らない (= trigger / cost / kill を書けない) 仕組みは追加しない。

## 9. 既存チケット対応表

| Issue | 本戦略との関係 / 提案 |
|---|---|
| #97 | 本戦略 §4 の実体。**re-scope 提案**: 「圧縮前 1 回きり」でなく「SKILL.md の意図的変更に伴う標準 check (trigger は §7)」と定義し直す。N=3 / verdict-only diff / held-out 2-3 は Issue 記載と一致。採否は Issue 側 |
| #91 | fixture-sync lint の CI 化 (= 本戦略 §7 の PR 行)。L2 runner を同 workflow に workflow_dispatch job として同居させるかは #91 側で判断 (= その場合のみ API key secret が要る) |
| #88 | 確定済 (= 改名のみ、挙動 test 化しない)。本戦略は改名後の位置づけ (= §3 L1) を前提に書いてある |
| #66 | context metrics / description 警告。skill listing budget (= `skillListingBudgetFraction` 0.01 / `skillListingMaxDescChars` 1536、出典: docs/wip/testing-metrics-baseline-2026-07-01.md:174、公式 changelog 未掲載) が判定材料。Issue #66 側の数値 (= 2,000 token / 130 char / 16,000 char) と食い違いがあり、**数値の SoT は #66 側で確定**する。L2 とは独立に成立する |
| #85 | size 表の SoT 統一 = **verdict 境界に直結** → baseline 先行 (§4 規約) |
| #92 | XS review 免除 = task-routing SKILL.md:97-99 (= hand-off 行。判定ロジック行そのものではない) の変更 → 同一 file 編集の collateral drift 防護として baseline 先行 |
| #98 | 第 4 verdict (assess) 案を採る場合のみ verdict 空間が 3 → 4 値 → baseline 先行に加え、case / held-out の expected_output 更新を同一変更に含めること。明示 SKIP 注記案なら verdict 空間は不変で baseline 先行のみ。採否は Issue 側 |
| 圧縮 refactor | baseline 先行。圧縮幅 10-15% cap は確定済で本戦略は再交渉しない |
| #82 | description の YAML 切詰め復元 = **frontmatter description (= trigger 面) を変える** → verdict assert は省略可だが、**変更前の L2 run set で expected_trigger (= 発火率) を assert し、変更後と比較すること**を必須とする |
| #81 等の機械的変更 | baseline 不要。判定基準: **diff が verdict 分岐条件・size 閾値・frontmatter description のいずれかを意味的に変えるか** (= 変えるなら少なくとも trigger assert 必須)。#81 は size 表 (SKILL.md:72) 内の agent 名置換のみで分岐条件を変えない → 免除 |

順序の実管理は #80 (= epic) と各 Issue。本 doc は判定基準のみを持つ。

## 10. 本戦略が明示的にやらないこと

- cross-skill 重複の削減 / 共有 companion file 化 (= 確定済: fresh-context 原則。重複は仕様であり、テストで守る対象でもない)
- 既存 gate の挙動 test 化 (= fixture-sync lint として維持、#88)
- agent .md prompt の E2E eval、backlog cron の挙動 test (§1)
- dashboard / cloud judge への escalation (= Epic #62 の明示除外に従う)
- 全 skill への L2 一括展開 (= 対象追加は failure-sourced のみ、§6)
- hook 段への LLM 実行の追加 (§7)
- 圧縮 cap 10-15% の再交渉、および圧縮そのものの実施判断 (= Issue 側の領域)
