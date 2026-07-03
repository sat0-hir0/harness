# eval — skill fixture-sync lint

6 skill (= `task-routing` / `intent-clarify` / `task-slicing` / `wave-status` /
`finish-task` / `commit-message`) の「代表発話 → 期待 output」を YAML case として
固定し、 その case (= `cases/`) と合意済み期待値 (= `baseline/`) が **同期している
か** を安く検知するための **fixture-sync lint** 基盤。

> **これは挙動回帰 test ではない (= 最重要)**。 skill 本文は一度も実行されない
> (= skill は Claude Code session 内でしか走らない)。 したがって SKILL.md を
> 変更して **実際の振る舞いが変わったこと** は本基盤では検知できない。 検知できる
> のは「手書きの `cases/` が commit 済みの `baseline/` からズレたか」だけ。 価値は、
> case を編集した author に **意識的な re-baseline を強制** し 2 つの fixture を
> 同期させ続ける点にある。 semantic な挙動照合が要るなら PR / nightly の judge
> (= §judge、 業界比較は `docs/wip/harness-evaluation-2026-07-02.md` §5.3) を使う。

各 skill の SKILL.md にある Worked example / Use when 代表発話 / Final Report
スキーマから case を抽出しているため、 追加創作は最小限。 現状 6 skill × 5 case =
**30 case**。

## ディレクトリ構成

```
eval/
├─ cases/                      # skill ごとの case ファイル (= 手で編集する source of truth)
│   ├─ task-routing.yaml
│   ├─ intent-clarify.yaml
│   ├─ task-slicing.yaml
│   ├─ wave-status.yaml
│   ├─ finish-task.yaml
│   └─ commit-message.yaml
├─ holdout/                    # L2 behavioral eval 専用の held-out case (= fixture-sync 対象外)
│   └─ task-routing.yaml
├─ baseline/                   # 合意された正しい期待 output (= git commit する基準)
│   └─ <skill>-<id>.baseline.yaml
├─ behavioral-baseline/        # L2 run set の記録 (= model id / CLI version / verdict tally)
│   └─ <skill>-<date>.yaml
├─ snapshots/                  # eval-run.py が生成する派生物 (= .gitignore、 commit しない)
│   └─ <skill>-<id>.snapshot.yaml
├─ scripts/
│   ├─ eval_common.py          # 共通ヘルパー (= case ローダ / judge クライアント / I/O)
│   ├─ eval-run.py             # case 実行 → snapshot 保存 + 期待/実 output 表示
│   ├─ eval-baseline.py        # 現状を baseline として固定
│   ├─ eval-regression.py      # baseline vs 現在の case を diff
│   └─ eval-behavioral.py      # L2 verdict-contract runner (= claude -p の薄い wrapper)
└─ README.md
```

## case の書き方

1 skill = 1 YAML ファイル。 各 case は代表発話 (`input`) と期待 output
(`expected_output`) を持つ。 `expected_output` の中身は skill ごとに異なる
(= task-routing は `verdict` / `qualitative_gate` / `scope_estimate`、
commit-message は `type` / `scope` / `breaking` / `subject`)。

```yaml
skill: task-routing
cases:
  - id: 1
    input: "README L42 の typo を直して"
    expected_trigger: task-routing
    expected_no_trigger: [task-slicing, wave-status]
    source: "skills/task-routing/SKILL.md Example 1"   # 抽出元
    expected_output:
      qualitative_gate:
        public_behaviour_changed: no
        harness_verifiable: yes
        design_judgement_needed: no
      file_count_proxy: 1
      scope_estimate: XS
      verdict: Lead-direct
```

case を追加・変更するときは、 必ず該当 SKILL.md の記述を `source` に控える
(= creative に作らず SKILL.md の事実を写す)。

## snapshot の考え方 (= skill は実行しない)

skill は Claude Code session 内でしか走らないため、 ローカルの python からは
実行できない。 そのため `eval-run.py` は skill を実行せず、 case の
`expected_output` を「その case が固定する正しい output」として snapshot に
書き出すだけ。 出力の `match: match` は「skill を実行して検証した」意味ではなく、
「期待値の snapshot を記録した」意味。

副作用検知は次の運用で成立する: skill / SKILL.md を変更したら、 その変更を case に
反映し、 `eval-regression.py` で baseline (= 変更前に固定した期待値) との差分を
確認する。 意図しない差分が出れば、 それが skill 変更の副作用。 外部依存なしで動く。

### judge (= optional、 eval-regression.py のみ)

`eval-regression.py --judge` はローカルの Ollama judge
(= [Issue #63](https://github.com/sat0-hir0/backlog/issues/63) で導入した Qwen) を呼び、
baseline と現在 case の **表記ゆれを許容した semantic 比較** を行う (= 構造 diff に
上乗せ)。 judge が意味を持つのは「baseline と現在」という異なる 2 者を比較する
regression のときだけなので、 `eval-run.py` には judge を持たせていない。 judge が
到達不可 (= daemon 停止 / モデル未 load / VRAM 競合) なら警告して構造 diff のみに
自動 fallback する。

- 接続先: `OLLAMA_HOST` 環境変数 (= 既定 `http://localhost:11434`)
- モデル: `EVAL_JUDGE_MODEL` 環境変数 (= 既定 `qwen3:14b`)
- judge 実行時は VRAM を掴む他 process (= ゲーム等) を閉じる (= `#63` の CUDA malloc fail 事故を参照)

## 使い方

```bash
cd eval/scripts

# case schema の検証だけ
python eval-run.py --validate

# 1 skill の 1 case を実行 (= 期待/実 output を YAML で並べて表示)
python eval-run.py --skill task-routing --case 1

# 1 skill の全 case
python eval-run.py --skill task-routing

# 全 skill の全 case (= 30 snapshot 生成)
python eval-run.py --skill all

# 現状を baseline として固定 (= 変更前に 1 回実行)
python eval-baseline.py --skill all

# baseline と現在の case を diff (= 差分ゼロなら exit 0、 ズレなら exit 1)
python eval-regression.py --skill all

# 表記ゆれを許容した semantic diff
python eval-regression.py --skill all --judge
```

## 典型ワークフロー (= skill 変更の副作用チェック)

1. skill を変更する **前** に `eval-baseline.py --skill all` で基準を固定する
2. skill / SKILL.md を変更する
3. 変更を case に反映する (= Worked example が変わったら case も更新)
4. `eval-regression.py --skill all` を実行し、 意図した差分だけが出るか確認する
5. 意図通りなら `eval-baseline.py --skill all` で baseline を更新して commit する

`snapshots/` は `.gitignore` 済みの派生物。 `baseline/` と `cases/` を commit する。

## pre-push fixture-sync gate (= 自動化)

`eval-regression.py` を **pre-push hook** に接続し、 skill / agent を触った push で
`cases/` と `baseline/` がズレたまま (= 未同期) なら自動ブロックする。 hook は
[lefthook](https://github.com/evilmartians/lefthook) 経由 (= repo root の
`lefthook.yml`) で `scripts/eval-gate.py` を呼ぶ。

- `eval-gate.py` は push する range の変更ファイルを検査し、 lint 対象を判定する:
  - `skills/<name>/SKILL.md` の変更 → その skill の fixture-sync 検査のみ起動
  - `agents/*.md` の変更 → 全 skill (`--skill all`) に fan-out
  - skill / agent の変更が無い push → skip (= exit 0)
- 対象 skill の `eval-regression.py` が未同期 / baseline 欠落を検出 (= exit 非 0) すると
  push をブロック (= exit 1)。 **反射的に re-baseline しないこと**: まず
  `eval-regression.py --skill <name>` で diff を確認し、 新しい期待 output が意図
  どおりだと確認してから `eval-baseline.py` で baseline を更新して push する
  (= この gate は挙動を保証しない。 保証するのは 2 fixture の同期だけ)。

```bash
lefthook install                              # .git/hooks/pre-push を生成
python scripts/eval-gate.py --range A..B       # 手動で range を検証 (= dry-run)
```

pre-push hook は git が push plan (`<local_ref> <local_sha> <remote_ref> <remote_sha>`)
を stdin で渡すのを読む。 手動検証では stdin を空にして `--range` を使う。

## L2 behavioral eval (= eval-behavioral.py、 verdict-contract test)

`docs/wip/test-strategy-2026-07-02.md` §4/§5 の実体。 fixture-sync lint (= 上記) が
「fixture 同士の同期」 しか見ないのに対し、 こちらは **task-routing を headless で
実際に実行** し、 判定行から抽出した verdict (= `Lead-direct` / `delegate-single` /
`delegate-slice`) を assert する。

### これは何であり、 何でないか

- **である**: task-routing の verdict 3 値だけを見る回帰 check。 SKILL.md の編集で
  verdict 境界が動いたかを、 変更前後の run set の **多数決 verdict 単位の diff** で検出する。
- **でない**: Y-trace 文言の品質評価 / 他 skill の挙動 test / multi-turn workflow の
  実走 / CI gate。 hook 段には置かない (= LLM 実行 + 数十分は push の前提にしない)。

### 実行タイミング (= trigger discipline)

**on-demand のみ**。 具体的には:

1. **verdict 境界に触れる SKILL.md 編集の前後** (= baseline-before-modification 規約)。
   変更前に現行版で 1 run set を取得してから編集し、 変更後の run set と
   `--compare` する。 単発試行同士の比較は禁止 (= noise と regression を分離できない)。
2. 実運用で誤判定 / UAT 差し戻しが出たとき (= failure-sourced に case を足して再実行)。

pre-push / CI には接続しない。 判定基準 (= どの編集が baseline 必須か) は
test-strategy §9 の対応表を参照。

### 前提条件 (= project-scope junction)

runner は `--setting-sources project` で個人 `~/.claude` (= user scope の skill /
CLAUDE.md) を排除する。 ただし task-routing は skillshare 配布で user scope にしか
存在せず、 harness repo に `.claude/` は無い。 そのままでは skill が読み込まれず
全 case が trigger-fail するため、 runner が実行前に repo 直下へ junction を自動作成する:

```
<repo>/.claude/skills  ->  <repo>/skills   (Windows junction / POSIX symlink)
```

repo の編集中 SKILL.md がそのまま読まれるので、 変更前後の比較がそのまま成立する。
`.claude/` は実行時派生物として `.gitignore` 済み (= commit しない)。 run set 冒頭の
smoke assertion (= 先頭 case で Skill tool_use event を 1 回観測) を通過するまで
trial は数えない。

### held-out case (= eval/holdout/)

train case (= `cases/`) への過適合を検出するため、 Worked examples 由来でない case を
`holdout/` に置く。 `cases/` の外に置くのは、 fixture-sync gate の `--skill all`
fan-out が baseline 欠落で push を塞ぐのを避けるため (= holdout/ は L1 対象外)。
**SKILL.md 編集 session のコンテキストに入れない**。 読んでしまった case は train 側へ
降格し、 failure-sourced に補充する。

### 使い方

```bash
cd eval/scripts

# 全 case (cases + holdout) を N=3 で実行し、 run set 記録を保存
# (= 既定出力は ../behavioral-baseline/<skill>-<date>.yaml。 同日 2 回目以降は
#    -2, -3, ... の suffix が付き、 既存 run set を上書きしない)
python eval-behavioral.py --skill task-routing

# 変更前後の run set を majority 単位で diff
# (= model / CLI version / trials_per_case 不一致、 NEW 側の case 欠落は exit 2 で拒否)
python eval-behavioral.py --compare \
    ../behavioral-baseline/task-routing-2026-07-03.yaml \
    ../behavioral-baseline/task-routing-<after>.yaml

# 境界 case だけ N=5 で深掘り / sonnet で深掘り
python eval-behavioral.py --skill task-routing --case 2 --trials 5
python eval-behavioral.py --skill task-routing --sonnet

# no-verdict-line / trigger-fail の postmortem: 各 trial の raw stream-json を保存
# (= fail した trial の実出力を再課金なしで検分できる。 DIR は commit しない)
python eval-behavioral.py --skill task-routing --case 5 --trials 1 --save-raw /tmp/raw
```

model は runner 内の定数で固定 (= 既定 `claude-haiku-4-5`、 opt-in `claude-sonnet-5`)。
run set 記録には model id + CLI version + trials_per_case + per-case verdict tally が
入り、 これらが一致しない run set 同士の `--compare` は runner が拒否する (= N=3
baseline vs N=1 probe の比較は単発試行比較と同じため trials も互換性条件)。 NEW 側に
OLD の case が欠けている partial run (= `--case` / `--no-holdout` の出力) も
「差分なし」 で通さず exit 2 で拒否する。 runner 自体の compare / 出力パス回りは
`test_eval_behavioral.py` の synthetic test (= claude 実行なし、 無課金) で検証できる。

### 実測コスト (= 2026-07-03 の probe run、 実測点)

- model `claude-haiku-4-5` / CLI 2.1.195 / 1 run あたり実測 60-106 秒・$0.17-0.22
  (= test-strategy §8 の仮置き 20-40s / $0.05-0.10 より重い。 skill 発火 + Y-trace
  生成まで含むため)。 実測 artifact:
  `eval/behavioral-baseline/task-routing-2026-07-03-probe.yaml`
  (= smoke 1 + case 1 x N=1 の縮小 run set、 合計 $0.39)
- ここから外挿すると、 標準構成 8 case (= train 5 + held-out 3) x N=3 + smoke 1
  = 25 run は逐次で **約 $4-6 / 40-50 分**。 `total_cost_usd` は CLI の client 側
  推計であり課金実測ではない
- 観測済みの noise: smoke で trigger-fail が 1 回発生 (= haiku が skill を呼ばず
  直答した)。 runner は smoke を上限 3 回まで再試行する。 case trial 側の
  trigger-fail は fail trial として tally に残る (= 多数決が noise を吸収する)

### no-verdict-line の根本原因 (= 2026-07-03 調査、 backlog #108)

2026-07-03 の run set で no-verdict-line が 24 trial 中 5 回 (= holdout#2 は 2/3 で
majority fail) 出た。 raw stream-json を採取した probe (= 同一 input x 6 trial) で
原因を確定した:

- **発火失敗ではない**: 全 probe で Skill tool_use (task-routing) を観測。
- **verdict 欠落でもない**: 全 probe の出力に verdict は明記されている。
- **真因は抽出 regex の取りこぼし** (= extraction-fail)。 haiku の実出力は
  1. `` **判定: `delegate-slice` (L)** `` (= verdict token を code span で装飾。 6 中 3)
  2. `## Verdict: **delegate-slice (L)**` (= label が英語。 6 中 1)
  の形を取ることがあり、 旧 regex (= `判定\**\s*[:：]\s*\**` のみ許容) はどちらも
  拾えない。 それでも大半の trial が pass していたのは、 Y-trace 行
  (= `` `判定: <verdict> | ∵ ...` `` の code span 内は plain 形式) が偶然 fallback に
  なっていたため。 Y-trace 自体も省略されることがあり (6 中 1)、 「主判定行が装飾形式」
  AND 「Y-trace 省略 / 装飾」 が重なった trial だけ no-verdict-line になる
  (= 観測率 ~20% と整合)。

対処は VERDICT_RE の superset 化 (= code span の backtick + 英語 `Verdict:` label を
許容)。 旧 regex が match していた text では抽出結果は変わらない (= 採取済み raw 6 件の
replay で確認、 verdict 差分なし)。 形式契約は `test_eval_behavioral.py` の
`VerdictRegexTests` (= 観測形式を fixture 化) が固定する。 同日の baseline
(`task-routing-2026-07-03.yaml`) の holdout#2 fail はこの測定 artifact であり、 修正後
extractor での再取得分は `task-routing-2026-07-03-2.yaml` (= 以後の --compare の基準。
holdout#2 は pass に転じ、 pass 7 / fail 1)。

残存 noise の扱い: 修正後 run set でも no-verdict-line は 4/24 trial 残る (= 修正前
5/24)。 該当 input の修正後 probe 12 本では再現せず (= 11 verdict / 1 trigger-fail、
extraction-fail 0)、 恒常的な形式取りこぼしではなく haiku の出力揺れ
(= 判定行自体の省略等) とみなす。 trigger-fail
(= skill を呼ばず直答) と同じく多数決が吸収する前提で、 これ以上は regex を広げない
(= false-positive 抽出のリスクの方が大きい)。 再調査が要る場合は `--save-raw DIR` で
全 trial の raw stream-json を保存して fail した trial の実出力を直接見る
(= 再課金なしで postmortem できる)。 唯一の fail (cases#5) は 1/1/1 の 3 値割れで、
trigger-fail + no-verdict-line の noise 同時発生によるもの (= verdict 自体の regression
ではない)。

## PR CI (= GitHub Actions での再実行)

pre-push gate は 1 台の Windows 機のローカル hook にしか存在しないため、 同等の検査を
`.github/workflows/eval-gate.yml` が PR ごとに ubuntu-latest で再実行する
(= backlog #91)。 中身は決定的 check のみで、 **LLM / API key / Ollama を一切使わない**
(= test-strategy doc §7 の trigger 規約: hook / CI 段は決定的 + 数秒のみ。 挙動 eval
は on-demand 専用で、 CI に置くと API key secret が必要になるため置かない)。

| CI job | 実行内容 | local 対応物 |
|---|---|---|
| lints | `check-frontmatter-yaml.py` / `lint-agent-refs.py` / `check-future-plans.py --base origin/<PR base>` | lefthook pre-push の frontmatter-lint / agent-ref-lint + $finish-task 経由の future-plans check |
| fixture-sync | `eval-regression.py --skill all` | lefthook pre-push の eval-gate (= `scripts/eval-gate.py`) |

local の `eval-gate.py` は push range の変更ファイルから対象 skill を絞るが、 CI は
常に `--skill all` を流す。 理由は 2 つ: (1) 全 30 fixture の構造 diff は数秒で終わる
ため絞る利点がない、 (2) `eval-gate.py` の対象 mapping は `skills/*/SKILL.md` と
`agents/*.md` にしか反応しないため、 `eval/cases/` や `eval/baseline/` だけを編集した
push は local gate を素通りする — CI の `--skill all` がこの穴を塞ぐ。
`--judge` (= Ollama semantic 比較、 §judge) は CI では使わない。

## 依存

- Python 3.11
- PyYAML
- (optional) ローカル Ollama + judge モデル
