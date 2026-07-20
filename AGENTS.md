# harness — AI 開発ハーネスの SoT

universal な skill / agent / 設計 doc を 1 repo に集約し、 skillshare で各 vendor へ配布する source of truth。 個人 project 横断で使う入口 skill / subagent / eval / 検査 script の実体はここにある。

## SoT 警告 (= 最重要)

- skill / agent の正本は **この repo** (`~/code/harness/`)。 編集は必ずここで行う。
- `~/.config/skillshare/{skills,agents}/` は sync の中間先。 **直接編集禁止** (= 次の sync で上書きされる)。
- 各 vendor の配布先 (`~/.claude/skills/` 等) も **編集禁止** (= 生成物)。
- 反映は `skillshare sync --all` (= harness の正本を中間先 → 各 vendor へ展開)。

## リポ構成

- `skills/` = 6 universal skill (task-routing / intent-clarify / task-slicing / wave-status / finish-task / commit-message)。 各 `<name>/SKILL.md` が本体。
- `agents/` = 6 universal agent (architect / fullstack-engineer / qa-expert / performance-engineer / security-auditor / technical-writer)。
- `docs/harness-design.md` = 全体設計仕様。
- `docs/diagrams/` = 俯瞰図 (= lifecycle / skill chain の SVG)。
- `docs/script-placement.md` = script 配置原則。
- `docs/wip/` = 作業中の議論・評価メモ (= 確定事実ではない。 canonical fact として引用しない)。
- `eval/` = skill snapshot test (`cases/` 手書き入力 / `baseline/` 期待構造 / `scripts/` runner)。
- `scripts/` = eval-gate・check-future-plans 等の検査 script。

## eval-gate 契約 (= pre-push)

- lefthook の pre-push hook が `scripts/eval-gate.py` を呼ぶ (= 有効化は `lefthook install` を初回 1 回)。
- `skills/<name>/SKILL.md` 変更 → その skill の regression を起動。
- `agents/*.md` 変更 → 全 skill に fan-out (`--skill all`)。
- skill / agent 無変更の push → skip (= exit 0)。
- drift / baseline 欠落を検出したら push をブロック。 意図した変更なら `python eval/scripts/eval-baseline.py --skill all` で baseline 更新後に再 push。
- eval は skill 本文を実行せず、 `eval/cases/` (手書き) と `eval/baseline/` の構造 diff (= fixture-sync lint)。

## check-future-plans (= doc 規律)

- `scripts/check-future-plans.py` が diff を milestone 名 / 将来時制 / 拡張予定パターンで grep。
- AGENTS.md を含む doc は present-fact のみを書く (= このファイル自身も scan 対象)。

## build / verify

- `lefthook install` = pre-push hook を有効化 (初回 1 回)。
- `skillshare sync --all` = 正本を各 vendor へ展開。
- `python eval/scripts/eval-regression.py --skill all` = 全 skill の構造 diff を検査。
- `python scripts/check-future-plans.py --base main` = diff の doc 規律違反を検査。

## リポ地図 (= ~/code/ 配下、 全て sat0-hir0/* remote)

| repo | 役割 |
|---|---|
| harness | AI 開発ハーネスの SoT (= universal skill/agent/設計 doc を集約、 skillshare で配布) |
| backlog | やりたいこと / Issue の入口 (= Projects v2 で Issue lifecycle を AI 駆動、 UAT/PR は人間) |
| ai-memory | user-model / 協働スタイル / project 横断 private context の実体 (= Basic Memory を Git 管理) |
| dotconfig | chezmoi の dotfiles source (= 環境再現 + scheduled task 定義) |
| limn | 思考整理ツール (= block editing / keyboard-first / .md storage / Rust) |
| ow-my-coach | Overwatch 2 向け Overwolf in-game コーチングアプリ (= TypeScript) |
| youtube-subtitle | YouTube 字幕取得ローカル Web アプリ (= Python / FastAPI) |
