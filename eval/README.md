# eval — skill snapshot test

6 skill (= `task-routing` / `intent-clarify` / `task-slicing` / `wave-status` /
`finish-task` / `commit-message`) の「代表発話 → 期待 output」を YAML case として
固定し、 skill / agent / hook を変更したときに **意図しない振る舞いのズレ** を安く
検知するための snapshot test 基盤。

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
├─ baseline/                   # 合意された正しい期待 output (= git commit する基準)
│   └─ <skill>-<id>.baseline.yaml
├─ snapshots/                  # eval-run.py が生成する派生物 (= .gitignore、 commit しない)
│   └─ <skill>-<id>.snapshot.yaml
├─ scripts/
│   ├─ eval_common.py          # 共通ヘルパー (= case ローダ / judge クライアント / I/O)
│   ├─ eval-run.py             # case 実行 → snapshot 保存 + 期待/実 output 表示
│   ├─ eval-baseline.py        # 現状を baseline として固定
│   └─ eval-regression.py      # baseline vs 現在の case を diff
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

## 依存

- Python 3.11
- PyYAML
- (optional) ローカル Ollama + judge モデル
