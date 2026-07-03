# wave-status per-vendor resolution 検証記録 (2026-07-03)

> 本 doc は docs/wip (= 検証記録)。sat0-hir0/backlog#112 の実施証跡であり、確定仕様は skills/wave-status/SKILL.md 側にある。

## 目的

wave-status SKILL.md の per-vendor 解決規約 (= File location の `<vendor-home>` 自己判定 + SSOT 規約の cross-vendor lookup) が、Claude Code 以外の第 2 vendor でも文書どおりに解決できるかを 1 回検証する。

## 環境 (= 2026-07-03 時点の実測)

| 項目 | 実測値 |
|---|---|
| vendor A | Claude Code (= 本検証の実行 agent 自身、vendor-home `~/.claude/`) |
| vendor B | codex-cli 0.139.0 / model gpt-5.5 (= `codex --version`、vendor-home `~/.codex/`) |
| skill 配布状況 | `~/.codex/skills/wave-status/SKILL.md` あり (= skillshare sync 済) |
| その他 CLI | cursor.cmd あり (未使用)、gemini CLI なし (= `~/.gemini/` dir 自体は存在) |

vendor home / state dir の事前状態 (= PowerShell `Test-Path` で確認):

| vendor home | home 存在 | state/ 存在 | slice-portability-check-112.md |
|---|---|---|---|
| `~/.claude/` | True | True | False |
| `~/.codex/` | True | False | False |
| `~/.cursor/` | True | False | False |
| `~/.gemini/` | True | False | False |
| `~/.agents/` | True | False | False |

= 検証 slug は全 vendor home に不在、state/ を持つのは `~/.claude/` のみ (クリーンな初期条件)。

## 手順と結果

### Step A: vendor A (= Claude Code) で init

実行 agent が Claude Code 自身のため、ここは本物の vendor A 実行。SKILL.md の File format どおりに scratch file を作成:

- path: `C:\Users\hiroki\.claude\state\slice-portability-check-112.md`
- frontmatter に `path:` (= SSOT 規約) を記録、Wave 1 件 (= `todo`)、Log に init 行。

### Step B: vendor B (= codex CLI) から cross-vendor resolution — 実 CLI 実行

コマンド (= prompt は stdin 経由、下記「運用上の注意」参照):

```
codex exec --sandbox read-only --skip-git-repo-check -C C:\Users\hiroki -o <scratch>/codex-last-message.txt - < codex-prompt.txt
```

prompt の要旨: 「vendor home は `~/.codex`。`~/.codex/skills/wave-status/SKILL.md` を読み、slug `portability-check-112` に対して Read 操作 (= SKILL.md の Step 3-1 / 3-2) のみを実行。自 vendor home の state/ を先に見て、無ければ skill 記載の他 vendor home を順に探し、見つけた file を複製せず SSOT として採用。read-only 厳守」。

codex の最終報告 (= `-o` 出力そのまま):

```
1. Paths checked, in order:
   - C:\Users\hiroki\.codex\state\slice-portability-check-112.md - absent
   - C:\Users\hiroki\.claude\state\slice-portability-check-112.md - found
   - C:\Users\hiroki\.cursor\state\slice-portability-check-112.md - absent
   - C:\Users\hiroki\.gemini\state\slice-portability-check-112.md - absent
   - C:\Users\hiroki\.agents\state\slice-portability-check-112.md - absent

2. Resolved SSOT path:
   - C:\Users\hiroki\.claude\state\slice-portability-check-112.md

3. Step 3-2 summary:
   - [ ] Wave 1: resolve this file from a second vendor context - todo
```

検証点の結果:

- 自 vendor home (`~/.codex/state/`) を最初に確認 → 不在 → 文書記載の一覧を walk → `~/.claude/state/` で発見 → **元 path のまま SSOT として採用** (= 複製 / 移動なし)。SKILL.md Step 2-1 / SSOT 規約どおり。
- codex は配布済み `~/.codex/skills/wave-status/SKILL.md` を実際に読んでいる (= session log `rollout-2026-07-03T18-43-02-*.jsonl` に read 参照 2 件)。
- read-only sandbox は保持された: 実行後も `~/.codex/state/` ほか他 vendor home に state dir / file は一切作成されていない (= 全 home で `Test-Path` False)。

### Step C: vendor B 文脈での mark (= filesystem walkthrough、codex 実行ではない)

Mark 操作 (= SKILL.md の Step 2-1 / 2-2) は書き込みを伴うため codex には実行させず (= read-only sandbox の範囲外)、Claude Code が vendor B 文脈をシミュレートして filesystem レベルで実施:

1. Step 2-1 lookup: `~/.codex/state/slice-portability-check-112.md` 不在 → cross-vendor lookup で `~/.claude/state/` の file に解決 (= Step B と同一の解決結果)。
2. Step 2-2: 解決した SSOT path の file を **その場で** 編集 (= Wave 1 `[ ]`→`[x]` done、Log に mark 行を追記)。
3. 事後確認: slug の file は全 vendor home 中 `~/.claude/state/` の 1 個のみ (= `~/.codex/` 側に複製は発生していない)。

### Step D: 後片付け

- scratch file `~/.claude/state/slice-portability-check-112.md` を削除。
- `~/.claude/state/` は検証前の 13 file に復元 (= 実測)。他 vendor home は無変化。

## 検証できたこと / できていないこと

**検証できたこと (= 実 CLI + 実測)**:

- 第 2 vendor (= codex CLI) が、vendor A (= `~/.claude/`) で init された state file を、文書の lookup 順 (= 自 home → `~/.claude/` → `~/.cursor/` → `~/.gemini/` → `~/.agents/`) どおりに発見し、複製せず元 path を SSOT として採用できる。
- skillshare 配布済みの SKILL.md を codex が読み込み、その規約を実行できる (= 文書の解決規則は第 2 vendor で実行可能なままの記述になっている)。
- mark の in-place 更新は SSOT path 側にのみ発生し、vendor B 側に複製 file を作らない (= walkthrough レベル)。

**検証できていないこと (= 本記録の限界、現在形の事実)**:

- prompt 側で lookup 規則の要旨を再掲したため、「codex が SKILL.md 単独・無誘導で lookup を導出する」ことの証明ではない (= 証明されたのは規約が第 2 vendor で文書どおり実行可能なこと)。
- mark の書き込みは codex 自身では未実行 (= simulated walkthrough のみ)。init 時の Step 1-2 adopt 判断 (= 既存発見時に新規作成しない) も real init としては未実行。
- 重複 slug の mtime tie-break、cursor / gemini / `~/.agents/` を vendor B としたケースは未検証。

## 副次的観測 (= 本検証の対象外だが記録)

- codex session 開始時に skill load error が 2 件出る: `~/.config/skillshare/skills/{intent-clarify,task-routing}/SKILL.md` が `invalid description: exceeds maximum length of 1024 characters` で **codex に読み込まれていない**。wave-status を含む他 skill は load error なし。
- Windows での codex exec 運用上の注意 2 点: (1) stdin が開いた pipe のままだと `Reading additional input from stdin...` で無期限 block する (= stdin を閉じるか `-` で明示する)。(2) npm の `codex.cmd` wrapper は複数行 prompt を引数渡しすると最初の改行で切り捨てる (= prompt は stdin 経由で渡す)。
