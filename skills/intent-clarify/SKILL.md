---
name: intent-clarify
description: >-
  ALWAYS invoke when the user wants to discuss / ideate / stress-test / clarify intent BEFORE
  committing to an implementation. Triggers include Japanese phrasings like
  「相談したい」「観点ほしい」「整理したい」「迷ってる」「どう思う?」「ideate」「stress-test」「方針決めたい」「どっちがいい?」, English phrasings like "I
  want to discuss X", "let's think about X", "give me perspectives on X", "I'm torn between A and B", "what do you think about X?", or any request where what / why / success / constraint is not yet
  decided. Confirms the user's real intent on 6 axes (= Outcome / User / Why now / Success /
  Constraint / Out of scope), optionally summoning the 6 subagents (= architect / fullstack-engineer /
  qa-expert / security-auditor / performance-engineer / technical-writer) as parallel lenses. Hands the confirmed intent forward to
  $task-routing in one direction (no loop). SKIP for pure-info questions ("what is X?") and for
  already-specified implementation requests (use $task-routing directly).
---

# Intent clarify

## Use when

**user が相談 / 観点出し / 意図整理を求めているとき、 直接呼ぶ direct entry-point**。 description の trigger 列挙 (= 「相談したい」 「迷ってる」 「どう思う?」 等) に当てはまれば本 skill が起動する。

明確な実装タスクには使わない (= `$task-routing` の領分)。 純粋情報質問 (= 「X って何?」) にも使わない。

## Why this skill exists

人が言うことと本当に欲しいものは違う。 「ダッシュボード作って」 は convention であって解きたい問題そのものではない。 「速くして」 と言われたとき 「いくつまで速ければ OK か」 は語られていない。

このギャップが一番安く塞げるのは plan / spec / code が存在する **前**。 一度 build に入ると switching cost が現実化し、 user は間違ったものに 「まあ良いか」 と妥協してしまう。 不一致が固定される。

`$task-routing` は実装系タスクの交通整理に特化しているので、 相談 / ideation 段階は射程外。 本 skill はその隙間を埋める。

## Contract

- 出力は **確定 intent** (= Outcome / User / Why now / Success / Constraint / Out of scope の 6 軸) と user の明示 yes。
- 確定 intent ができたら **同 turn 内で** `$task-routing` を再起動して実装系統に渡す (= user 入力待ちはしない、 6 軸 yes は Phase 3-2 で既に取得済)。
- 本 skill で実装はしない。 spec / plan / 一行コードを生成する前に止める。

## Phase 1: 場の設計

### Step 1-1: relevant な観点を判断

- **Decide**: この相談に必要な lens は何か?
  - **1 軸で足りる** (= ほぼ user の意図確認だけ) → Lead 単独で対話、 subagent spawn しない。
  - **複数 lens 必要** (= 設計 / 失敗観点 / 実装制約 / 検証 / docs 化 等) → 既存 subagent (= architect / fullstack-engineer / qa-expert / security-auditor / performance-engineer / technical-writer) から関係するものを並列召集。
- **判定軸**: 「user が判断するのに、 どの専門家が何を言えば一番情報量が増えるか?」
- 召集は **既存 agent の専門性そのまま**。 prompt に 「ideation mode」 等のモード切替は付けない (= 各 agent は自分の lens で語る、 architect なら設計目線、 fullstack-engineer なら 「実装制約として何が」、 security-auditor なら 「どこから侵入できる? 攻撃者視点で穴はどこ?」、 performance-engineer なら 「どこが遅くなりうる?」、 qa-expert なら 「何が動けば OK の証拠か?」、 technical-writer なら 「残すべき決定は何か?」)。

### Step 1-2: 召集 (= 必要なら)

- **複数 lens のとき**: 各 subagent に **同じテーマ** を渡して並列 spawn。 prompt は短く、 「この相談に対し、 あなたの専門性の lens で気になる観点・質問・assumption を 3-5 個 bullet で出して」。
- **Lead 単独のとき**: spawn しない、 Lead が直接 user と対話を始める。
- **Phase 2 中に lens 追加が必要になったら**: 現在の round を閉じてから (= 1Q1A を中断せず) 次 round 冒頭で追加 subagent を spawn する (= mid-stream で召集追加すると対話が散らかる)。

## Phase 2: 対話

### Step 2-1: hypothesis + confidence

- **Output**: user の意図についての現時点 best read を 1 文、 + 0-100% の confidence number。
- confidence が ~70% 未満なら 1 行で 「何が不明か」 を添える (= 「success がまだ言語化されていない」 等)。
- 数字は honest に。 高い数字を書いておいて次の 3 質問への user 反応が予測できないなら、 数字が嘘。
- **各 round の冒頭で confidence を再宣言する** (= round 間の変動を内部 trace で残す、 公開はしない)。

### Step 2-2: 1 質問ずつ、 各質問に GUESS を添える

形式:

```
Q: <focused な質問 1 つ>
GUESS: <agent の現時点仮説と、 そう思う理由>
```

user の反応を待ってから次の質問。

- **batch しない**: 質問 3 つ並べると user は skim して surface な答えを返す。
- **guess を付ける**: user は agent の wrong guess に対する反応の方が、 zero から答えるより速い。 guess を出すことで agent 自身の assumption が user の目に見える。
- **lens が複数なら、 観点ラベルを添える**: 「[設計観点] ... 」 「[失敗観点] ... 」 のように、 どの subagent から出た質問かを明示する (= user が 「設計の話より失敗の話を先に詰めたい」 と redirect できるように)。
- subagent からの返答は **bullet 3-5 個で受け取り**、 Lead が重複排除して **最も confidence を上げる 1 つ** を Q として選ぶ。

### Step 2-3: want vs should-want を聞き分ける

最も危険な user 答えは **「ちゃんとした答えに聞こえる answer」** で、 実は user が本当に欲しいものではない。 検知シグナル:

**英語 user**:
- best practice 用語の連呼 (= 「scalable」 「clean architecture」 「modern」 「robust」) で specific な outcome がない。
- 「the way most apps do it」 「the standard approach」 など convention 引用。
- 「I should probably ...」 「I think I'm supposed to ...」 「good engineering practice says ...」。

**日本語 user**:
- buzzword 系: 「ちゃんとした」 「モダンな」 「クリーンな設計」 「ベスプラに沿った」 「スケーラブル」 「ロバストな」。
- convention 引用系: 「世間的には〜」 「普通は〜」 「業界では〜」 「定石的に〜」。
- 自己規範系: 「〜すべき気がする」 「〜が正しい気がする」 「ちゃんとやるなら〜」 「本来は〜」。

これを検知したら、 1 度だけ問う:

> 「もし誰にも説明する必要がなかったら、 本当は何が欲しいですか?」

この 1 質問が前の 5 質問よりも仕事をすることが多い。

## Phase 3: Restate

### Step 3-1: 6 軸で書き戻す

confidence が高くなったら、 user の言葉を使って書き戻す (= 5-8 行):

```
ここまでの理解:

- Outcome:      <1 行>
- User:         <誰のための、 1 行>
- Why now:      <何が変わって今なのか / trigger / 変化のきっかけ、 1 行>
- Success:      <どうなれば成功と分かるか、 1 行>
- Constraint:   <binding な制約、 1 行>
- Out of scope: <明示的にやらないこと、 1 行>

yes / no / refine ?
```

**Why now** は 「優先度の話」 ではなく **「user の状況 / 環境変化のトリガー」** を聞く軸。

**Out of scope は省略不可**。 silent disagreement の半分は 「何を作らないか」 で起きる。

### Step 3-2: 明示 yes 確認

以下は yes ではない:

**英語 user**:
- 「whatever you think is best.」 → user が判断を agent に丸投げしている、 user 側も 95% confidence にない。 2 つの具体的選択肢で問い直す。
- 「sounds good.」 → 曖昧。 「refine するところはありますか?」 と追問。
- 「sure, let's go.」 → 礼儀的退出のことが多い、 endorsement ではない。 同じ追問。
- 沈黙の後の 「okay let's start.」 → interview を諦めたサイン、 converge ではない。 「何か言い忘れていることがありますか?」 と止める。

**日本語 user**:
- 「お任せします」 「お好きに」 → 判断丸投げ、 2 つの具体的選択肢で問い直す。
- 「いい感じです」 「いいと思います」 → 曖昧、 「refine したい箇所はありますか?」 と追問。
- 「進めて大丈夫です」 「大丈夫そうです」 → 同じ追問。
- 「とりあえずいきましょうか」 「まあそんな感じで」 → 諦めサイン、 「何か言い忘れていることがありますか?」 と止める。
- 沈黙、 もしくは 「OK」 「は」 「うん」 だけの相槌 → yes ではない、 6 軸を 1 軸ずつ再確認する。

user の言い直しが入ったら fold して restate を更新、 explicit yes が出るまで loop。

## Exit criterion (= checkable test)

- user が 6 軸 restate を **明示的に yes** と言った (= Phase 3-2 の回避パターンを除外して残った yes)。
- **AND** Lead が 「次の 3 つの質問への user 反応を予測できる」 状態。

**「次 3 質問予測可能」 の operationalize 手順**:

1. Lead は内部で次に聞きたい質問を 3 つ挙げる。
2. 各質問に対して predicted user reply を **1 行ずつ書き出す** (= 想定回答を agent の output として明示)。
3. 過去 round の対話と比較して **回答 pattern が一致する** か self-check する。
4. 想定 reply が 1 質問でも書けない、 もしくは過去対話の pattern と乖離する → predict 不可、 round 継続。

「想定 reply を書き出す」 という output 行為を伴わせることで vibe gate を防ぐ。 書けない時点で 「予測できる」 と self-declare しない。

3 round しても confidence が visibly に上がらない (= 各 round 冒頭で再宣言した confidence number が動かない) なら止めて user に上げる: 「ここまで X 回聞いたけれど反応を予測できない、 何か foundational なことを見落としているかも」。

## Phase 4: Hand-off

### Step 4-1: 結果を user に提示

確定した 6 軸 intent を 1 メッセージで提示。 project に `docs/intent/` 等の慣習があれば保存を offer (= project 規約に従う、 個人 skill 側で path を hardcode しない)。 user 確認後にのみ保存。

### Step 4-2: task-routing への one-directional hand-off (= 同 turn 内、 user 入力待ちなし)

確定 intent (= 6 軸 + 明示 yes) を input として **同 turn 内で** `$task-routing` を呼ぶ。 user に 「これで実装に入って良いですか?」 は **追加で聞かない** (= 6 軸 yes を Phase 3-2 で既に取得済、 二重確認は user を疲れさせる)。

- これは **one-directional** = 本 skill → task-routing の単方向。 task-routing 側に Phase 0 / short-circuit は存在しない (= ループしない)。
- task-routing は受け取った intent を「確定済の implementation request」 として Phase 1 から通常通り処理する。
- **autonomous mode の例外**: 「ざっくり進めて」 等の autonomous モードでも、 intent-clarify から task-routing への hand-off 境目では **何もしない** (= 二重 surface 防止)。 ただし task-routing が次に出す verdict (= Lead-direct / delegate-single / delegate-slice) の宣言は通常通り surface する。

## Boundary

- **Never** intent が user の明示 yes で確定する前に `$task-routing` に戻さない。 「だいたい分かったので進めますね」 は禁止。
- **Never** 「whatever you think」 「sounds good」 「sure」 「お任せします」 「いい感じです」 を yes として受け取らない。 言い直しを求める。
- **Never** Out of scope を省略しない。 6 軸 restate のうち 1 軸でも空欄なら restate は incomplete。
- **Never** 1 message に 3 つ以上の質問を batch しない。 1 質問ずつ。
- **Never** subagent を spawn したら user に質問させる構造にしない (= subagent は agent 同士で context が断絶する、 user 対話は Lead が中継する)。 subagent は観点 / assumption の **生成** だけ担当、 user との直接対話は Lead。
- **Never** spec / plan / コードを 1 行でも書かない。 本 skill の出口は **確定 intent** だけ。 実装は hand-off 後の task-routing 側で始まる。
- **Stop** non-interactive 文脈 (= CI / `/loop` / autonomous loop) では invoke しない。 user との対話が前提なので、 live で応答できる user がいないと成立しない。 underspec なタスクが渡ってきたら **user surface する blocker** として上げる。

## Helper

orchestration のみ、 script なし。 Lead は user 発話が相談 / ideation の trigger に該当したら本 skill を直接呼ぶ (= description の direct entry-point 設計)。 subagent 召集 (= Step 1-2) は **必要なときだけ**、 1 軸で済むなら Lead 単独で対話して良い。

下記 YAML Final Report は内部記録用。 user 向けには 6 軸 restate (= Phase 3) と確定 intent (= Phase 4-1) を 1 メッセージで出すだけ。 Phase 4-2 で task-routing を呼ぶときに input として渡す。

## Final Report

```yaml
intent-clarify:
  request: <1 行サマリ>
  scope_judgement:
    lens_count: 1 | multiple
    spawned_subagents: [architect | fullstack-engineer | qa-expert | security-auditor | performance-engineer | technical-writer]
  interview:
    rounds: <N>
    initial_confidence: <0-100>
    final_confidence: <0-100>
    want_vs_should_want_probe_used: yes | no
    predict_check:
      next_q1: { question: <...>, predicted_reply: <...> }
      next_q2: { question: <...>, predicted_reply: <...> }
      next_q3: { question: <...>, predicted_reply: <...> }
  intent:
    outcome: <1 行>
    user: <1 行>
    why_now: <1 行>
    success: <1 行>
    constraint: <1 行>
    out_of_scope: <1 行>
    explicit_yes: yes | refined-then-yes | not-confirmed
  next_action:
    skill: $task-routing
    note: one-directional hand-off (= intent-clarify → task-routing、 ループしない)
```

## Related

- `$task-routing` — 実装系 request の direct entry-point sibling skill。 本 skill が確定 intent を出したら、 Phase 4-2 で task-routing を **同 turn 内で one-directional に呼ぶ** (= ループしない、 task-routing 側に Phase 0 / short-circuit は存在しない)。
- 既存 6 subagent (= architect / fullstack-engineer / qa-expert / security-auditor / performance-engineer / technical-writer) — 複数 lens 必要なときに召集。 各 agent の prompt は不変更、 既存の専門性のまま 「観点 / assumption 出し」 を担う。

## Attribution

本 skill の core mechanism は addyosmani/agent-skills (MIT License, Copyright (c) 2025 Addy Osmani) の以下 2 skill から抽出 + 日本語訳 + ハーネス統合のため構造化変更:

- **`interview-me`** から抽出: hypothesis + confidence (= Step 2-1) / 1 質問 + GUESS (= Step 2-2) / want vs should-want 検知 (= Step 2-3) / 6 軸 restate (= Step 3-1) / 明示 yes 確認 (= Step 3-2) / 次 3 質問予測可能 stop (= Exit criterion)
- **`idea-refine`** から抽出: Out of scope を必須 1 軸として 6 軸に組み込み (= Step 3-1) / 「Not Doing list の表面化」 概念

統合のため追加:
- 既存 6 subagent 召集パターン (= Phase 1)
- task-routing one-directional hand-off 統合 (= Phase 4 / Final Report)
- 日本語 user 用の検知パターン (= Step 2-3 / Step 3-2)
- Exit criterion の operationalize 手順 (= 想定 reply 書き出し)
