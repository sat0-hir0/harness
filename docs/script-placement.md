# Script の配置原則

AI CLI 周りの script を作るとき、 4 つの起動経路のどれに該当するかで配置先が決まる。
現状の暫定線引きを以下に記す (= 経緯 / 検証中 item は backlog Issue #59 で管理)。

## 5 行ルール

| 起動経路 | 配置先 | 配布手段 | 例 |
|---|---|---|---|
| **harness skill / agent から呼ばれる** (= cross-OS / cross-vendor で配布したい) | **harness** (= `~/code/harness/scripts/` or `skills/<name>/`) | skillshare で全 vendor に同梱配布 | [`scripts/check-future-plans.py`](../scripts/check-future-plans.py) (= `$finish-task` Phase 4-5 から呼ばれる) |
| **`~/.claude/settings.json` の hook 経由で発火する** (= UserPromptSubmit / PreToolUse / Stop / SubagentStop など) | **dotconfig** (= `~/code/dotconfig/dot_local/share/scripts/` or `dot_claude/hooks/`) | chezmoi が settings.json と script を両方配置 | `dotconfig/dot_local/share/scripts/memory-*.ps1` (= memory lifecycle hook) |
| **personal CLI として手で叩く** (= alias / PATH 通したい / user 専用 utility) | **dotconfig** (= `~/code/dotconfig/dot_local/bin/`) | chezmoi が PATH 通る `~/.local/bin/` に配置 | `dotconfig/dot_local/bin/issue-status.ps1` (= GitHub Projects v2 Status field 更新) |
| **特定 project 専用** (= 例: limn の verify chain / その project の build pipeline) | **その project repo** (= `<project>/scripts/`) | project repo の中だけで完結 | `<project>/scripts/pr-review.sh` (= `$pr-review.sh` で呼ばれる) |
| **AI 駆動の cron / scheduled task** (= 人間不在で動く Claude Code session) | **dotconfig** (= `dot_local/share/scripts/`) | chezmoi が scheduled task 定義と script を一緒に配置 | `dotconfig/dot_local/share/scripts/setup-memory-task.ps1` |

## なぜこの線引きか

- **「設定と script は一緒に管理されるべき」**: settings.json の hook は path を hard-code するので、 settings.json と script が別 repo にあると drift する。 dotconfig は chezmoi が両方配置するので必然的にここに置く。
- **「skill が呼ぶ script は cross-OS / cross-vendor」**: harness は universal repo として `skillshare install` で別マシンに転送される前提。 skill が呼ぶ script は harness 内に置くことで、 別マシンでも同じ手順で動く。
- **「project 固有 script は project repo に閉じる」**: harness skill が `<project's verifier suite from scripts/ or CI>` と書いているのは、 project ごとに verify chain が違うため。 これを harness 側に置くと universal 性が崩れる。
- **「個人 CLI は dotconfig」**: PATH 通したい便利 script (= `gh` 拡張のような直叩き utility) は user 環境前提なので dotconfig 側で完結。

## 判定フローチャート

```
script を作りたい
    │
    ├── skill / agent の SKILL.md から呼ばれる? ── YES ──→ harness (= scripts/ または skills/<name>/)
    │   NO
    │
    ├── settings.json の hook で発火する? ── YES ──→ dotconfig (= dot_local/share/scripts/ or dot_claude/hooks/)
    │   NO
    │
    ├── 特定 project の verify / build chain? ── YES ──→ その project repo (= <project>/scripts/)
    │   NO
    │
    ├── PATH 通して手で叩きたい CLI? ── YES ──→ dotconfig (= dot_local/bin/)
    │   NO
    │
    └── scheduled task / cron? ── YES ──→ dotconfig (= dot_local/share/scripts/)
```

## 言語選択

| 配置先 | 推奨言語 | 理由 |
|---|---|---|
| **harness** (= cross-OS) | **Python 標準ライブラリのみ** | Win / Mac / Linux で 1 ファイル動作、 user 環境に Python は既にある (= claude.exe / uv.exe が動く前提) |
| **dotconfig** (= Windows 個人マシン専用) | **PowerShell 7 (pwsh)** | chezmoi の `.tmpl` 連携と Windows ガード前提 (= `{{ if eq .chezmoi.os "windows" -}}`) |
| **project repo** | **project の慣例に従う** | limn は bash / Rust project 共通 helper、 OW プロジェクトは pwsh + nodejs 等、 project ごとに違う |

## 関連

- [`scripts/check-future-plans.py`](../scripts/check-future-plans.py) — 本原則に基づき harness 配下に置いた universal helper の実例
- backlog Issue #59 — 配置原則の確立と既存 script 移管対象の検証
- [`harness-design.md`](harness-design.md) — harness 全体の設計仕様
