# harness

AI 開発ハーネス (= universal skill / agent / 設計 doc / 俯瞰図) の集約 repo。 個人開発で使う Claude Code / Codex / Cursor / Gemini 系 vendor に [skillshare CLI](https://github.com/runkids/skillshare) 経由で配布する。

## 存在意義

これまで skill / agent / 設計 doc が以下に分散していた:

- `~/.config/skillshare/` (= **git 管理外**、 リモートバックアップなし)
- `~/code/dotconfig/` (= 環境再現用 dotfiles と混在)
- `~/code/backlog/docs/` (= backlog 固有 doc と混在、 内側 skill chain が fade out された曖昧表現)

この repo は **universal な harness 本体だけを集約**する場所。 具体的には:

- **6 skill** (= `task-routing` / `intent-clarify` / `task-slicing` / `wave-status` / `finish-task` / `commit-message`) — どのプロジェクトでも使う入口 + 共通フロー
- **6 agent** (= `architect` / `fullstack-engineer` / `qa-expert` / `performance-engineer` / `security-auditor` / `technical-writer`) — universal な役割定義
- **設計 doc** (= [`docs/harness-design.md`](docs/harness-design.md)) — 工学原則 / 多層防御 / システム構成 / workflow / session 透明性 / 採用判断 を 15 節で記述
- **俯瞰図 2 枚** (= [`docs/diagrams/`](docs/diagrams/README.md)) — 外側 board lifecycle + 内側 skill chain

プロジェクト固有の skill (= 例: backlog の `issue-from-idea` / `issue-execute` / `prepare-uat`) は **本 repo には置かない**。 各プロジェクト repo 配下 (= 例: `~/code/backlog/skills/`) に置く。

## install (= 新マシン / 別環境セットアップ)

前提: [skillshare CLI](https://github.com/runkids/skillshare) が installed であること。

```bash
skillshare install git@github.com:sat0-hir0/harness
skillshare sync --all
skillshare status   # 各 vendor が harness repo 由来で merged になっていることを確認
```

これで `~/.claude/skills/` / `~/.codex/skills/` / `~/.cursor/skills/` / `~/.gemini/skills/` / `~/.agents/skills/` の 5 vendor に同じ skill set が展開される。

## 更新

```bash
skillshare update --all     # 全 tracked source の git pull + 再同期
```

または skill を本 repo で編集 → commit → push した後、 各環境で:

```bash
cd ~/code/harness && git pull
skillshare sync --all
```

## Claude Code plugin build

skillshare 配布 (= 個人環境の cross-vendor 同期層) とは別に、 Claude Code 公式の
plugin 形式の成果物を repo からビルドできる。 組織が install / pin / update を
公式機構に乗せて配布するための出力層で、 skillshare 配布と併存する。

```bash
python scripts/build-plugin.py          # dist/claude-plugin/ を生成 (= gitignored)
python scripts/build-plugin.py --zip    # 加えて dist/harness-plugin-<version>.zip を生成
```

生成物の構造 (= [公式 plugin schema](https://code.claude.com/docs/en/plugins-reference) 準拠):

```
dist/claude-plugin/
├── .claude-plugin/plugin.json   # manifest (= name / version / description / author)
├── skills/<name>/SKILL.md       # repo の skills/ をそのまま同梱
└── agents/<name>.md             # repo の agents/ をそのまま同梱
```

### version の出どころ

repo root の `VERSION` ファイルが唯一の出どころ。 `git describe` でなく file にした理由:

- repo に tag が無いため `git describe` はそもそも失敗する
- zip 展開先や CI cache など git metadata の無い場所でも同じ version でビルドが再現する
- version bump が 1 行 diff としてレビューに乗る (= doc 規律と同じ扱い)

### 組織での install (= git-hosted marketplace 経由)

組織で配布する場合は、 ビルド成果物 (= `dist/claude-plugin/` の中身) を配布用 git repo
(例: `acme-corp/claude-plugins` の `plugins/harness/`) に置き、 その repo root の
`.claude-plugin/marketplace.json` で catalog 化する:

```json
{
  "name": "acme-plugins",
  "owner": { "name": "Acme" },
  "plugins": [
    {
      "name": "harness",
      "source": "./plugins/harness",
      "description": "AI development harness (skills + agents)"
    }
  ]
}
```

利用者側は Claude Code 内で 2 コマンド:

```shell
/plugin marketplace add acme-corp/claude-plugins
/plugin install harness@acme-plugins
```

private repo でも git 認証が通れば同じ手順で install できる。 pin は marketplace の
plugin entry 側で `ref` (= branch / tag) か `sha` (= commit) を指定する。 本 repo 自体は
marketplace を持たず、 成果物の生成までを担う。

## docs

| doc | 用途 |
|---|---|
| [`docs/harness-design.md`](docs/harness-design.md) | 全体設計仕様 (= 工学原則 / 多層防御 / 構造 / workflow / session 透明性 / 採用判断、 15 節) |
| [`docs/diagrams/`](docs/diagrams/README.md) | 俯瞰図 2 枚 + 解説 (= backlog 側 board lifecycle / 内側 skill chain) |

## pre-push eval gate

skill / agent を変更した push は、 [lefthook](https://github.com/evilmartians/lefthook)
の pre-push hook (= `lefthook.yml` → `scripts/eval-gate.py`) が eval regression を走らせ、
baseline からの drift を検出したら push をブロックする。 有効化は 1 回だけ:

```bash
lefthook install     # .git/hooks/pre-push を生成
```

`SKILL.md` の変更はその skill の、 `agents/*.md` の変更は全 skill の regression を
起動する。 詳細は [`eval/README.md`](eval/README.md) を参照。

同等の検査は PR でも走る (= `.github/workflows/eval-gate.yml`、 ubuntu-latest)。
lint 3 種 + fixture-sync (`eval-regression.py --skill all`) の決定的 check のみで、
LLM / API key は使わない。 CI と local gate の対応表は
[`eval/README.md`](eval/README.md) の「PR CI」節を参照。

## related repos

- `sat0-hir0/backlog` (= 個人の作りたいものリスト管理ハーネス、 本 harness の上に乗る外側レイヤー)
- `sat0-hir0/dotconfig` (= chezmoi 管理の dotfiles、 環境再現専用)
- `sat0-hir0/ai-memory` (= 個人 / プロジェクトをまたぐ AI memory)

## license

private. 個人用。
