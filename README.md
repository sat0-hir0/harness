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

## docs

| doc | 用途 |
|---|---|
| [`docs/harness-design.md`](docs/harness-design.md) | 全体設計仕様 (= 工学原則 / 多層防御 / 構造 / workflow / session 透明性 / 採用判断、 15 節) |
| [`docs/diagrams/`](docs/diagrams/README.md) | 俯瞰図 2 枚 + 解説 (= backlog 側 board lifecycle / 内側 skill chain) |

## related repos

- `sat0-hir0/backlog` (= 個人の作りたいものリスト管理ハーネス、 本 harness の上に乗る外側レイヤー)
- `sat0-hir0/dotconfig` (= chezmoi 管理の dotfiles、 環境再現専用)
- `sat0-hir0/ai-memory` (= 個人 / プロジェクトをまたぐ AI memory)

## license

private. 個人用。
