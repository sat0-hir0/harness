---
name: commit-message
description: ステージ済み diff から Conventional Commits 形式のコミットメッセージを生成する。`git commit` を打つ直前は MUST BE USED。メッセージを一貫・release-please 対応・pre-commit hook 互換に保つ。heredoc 形式で出力し、Lead が確認してコミットする。
---

# Commit message

## Use when

- feature / fix / chore / docs ブランチでの `git commit` の直前。
- `$finish-task` が完了報告を出し、変更がコミット可能な状態になったとき。
- ユーザーが「コミットして」「commit it」「commit」とだけ入力してメッセージを指定していないとき。

ユーザーがすでにメッセージの文面を決めている場合はスキップする。

## Why this skill exists

Conventional Commits は OSS コミットメッセージの事実上の業界標準であり、release-please / semantic-release / lerna / k8s / Angular / Cargo が採用している。フォーマットが揺れると下流の自動化が壊れる: CHANGELOG 生成・バージョンバンプ・breaking change 検出。

シングルメンテナのプロジェクトでもフォーマットは強制力になる — subject を 70 文字に収めようとすると、自分が何を変えたかを明確に言語化しなければならない。

## Contract

- subject 行は `<type>[(<scope>)][!]: <description>` に従う。
- subject は 70 文字以内。
- body は **why** に集中する (= diff がすでに what を示している; メッセージは why を記録する)。
- breaking change は subject に `!` を付け、かつ footer に `BREAKING CHANGE:` を書く。
- Co-authorship 表記はプロジェクトの `attribution.commit` 設定があればそれに従う。
- 出力は heredoc 形式 (= `git commit -m "$(cat <<'EOF' ... EOF)"` にそのまま貼れる)。

## Phase 1: Read the diff

### Step 1-1: Inspect staged changes

- **実行**: `git diff --cached --stat` でファイル一覧と行数を確認。
- **実行**: `git diff --cached` で実際の変更を確認 (= 最初の 200 行; 長い場合はサンプリング)。
- **実行**: `git status` で意図しないものがステージされていないか確認。

### Step 1-2: Decide the type

Conventional Commits canonical types:

| type | use when |
|---|---|
| `feat` | ユーザーから見える新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみの変更 |
| `style` | フォーマット・空白の変更 (= ロジック変更なし) |
| `refactor` | コードの再構成 (= 動作変更なし) |
| `perf` | パフォーマンス改善 |
| `test` | テストのみの変更 |
| `chore` | ツール・ビルド・依存関係 (= src・test 以外) |
| `ci` | CI ワークフロー・パイプラインの変更 |
| `build` | ビルドシステム・cargo・npm・ビルドに影響する依存関係 |
| `revert` | 過去のコミットの差し戻し |

複数の type が当てはまる場合は、**ユーザーから見た意図を最もよく表すものを選ぶ**。リファクタリングが新機能のための手段であれば `feat` が `refactor` に勝る。

### Step 1-3: Decide the scope (= optional)

scope は変更箇所を示す単一トークン: `(harness)` / `(adr)` / `(release)` / `(template)` など。明確さが増す場合のみ使用する。ワークスペース全体にまたがる変更の場合は省略する。

### Step 1-4: Detect breaking changes

以下のいずれかに該当する場合は breaking change:

- public API / config フィールド / CLI フラグ / 環境変数の削除またはリネーム
- 既存の入力に対するデフォルト動作の変更
- ユーザーが気づくレベルでのメジャー依存関係のバンプ
- 公開済みアーティファクトの削除

Breaking の場合 → scope の後に `!` (= `feat(api)!: ...`) AND footer に `BREAKING CHANGE: <説明>` を書く。

## Phase 2: Compose the subject

### Step 2-1: Write in present-imperative

- `add X` / `fix Y` / `update Z` — 正しい
- `added X` / `adds X` / `addition of X` — 誤り

### Step 2-2: Keep under 70 characters

`type(scope)!: ` のプレフィックスを含めてカウントする。70 文字に収まらない場合、コミット自体が大きすぎる可能性があるのでユーザーに伝える。

### Step 2-3: Lowercase, no period

`feat(harness): scope skills to OSS operating procedures` — 正しい
`Feat(Harness): Scope Skills to OSS Operating Procedures.` — 誤り

## Phase 3: Compose the body (= optional but recommended for non-trivial)

### Step 3-1: Lead paragraph — why

最初の body 段落は **なぜ** この変更が必要かを答える。diff が what を示す; body は動機を説明する。

- 「これまで X には問題 Y があった」 — 正しい
- 「関数 foo() を追加して X を行うようにした」 — 誤り (= diff の内容を重複して書いている)

### Step 3-2: Subsequent paragraphs — context

- 設計判断を制約した要因
- 却下した代替案 (= 1 文で)
- ADR・issue・過去コミットへの参照

### Step 3-3: Wrap at 72 chars

Markdown フレンドリーな折り返し。body は `git log` / GitHub PR ビュー / リリースノートで読まれる。

## Phase 4: Compose the footer

### Step 4-1: Co-authorship

プロジェクトの `attribution.commit` が設定されている場合 (= 例: `Co-Authored-By: Claude <noreply@anthropic.com>`) は必ず含める。

attribution 設定がなく AI ツールを使った場合は、AI が実質的なコードを生成したとき (= typo 修正のような trivial な変更を除く) のみ `Co-Authored-By` を含める。

### Step 4-2: BREAKING CHANGE block

Phase 1-4 で breaking change を検出した場合:

```
BREAKING CHANGE: <何が壊れるかを 1 段落で>

Migration: <移行方法を 1 段落で>
```

### Step 4-3: Issue / PR references

- `Closes: #123`
- `Refs: #456`
- `See-also: ADR-0004`

## Phase 5: Emit heredoc

### Step 5-1: Wrap in heredoc-ready form

```
git commit -m "$(cat <<'EOF'
<type>[(<scope>)][!]: <subject>

<body lead paragraph>

<body subsequent paragraphs>

<footer: breaking change, refs, co-authored-by>
EOF
)"
```

`<<'EOF'` (= シングルクォート) 形式で `$` とバッククォートのシェル展開を防ぐ。

## Stop condition

- subject が 70 文字以内、Conventional Commits に準拠、小文字、ピリオドなし。
- body (ある場合) が why を説明し、72 文字で折り返されている。
- breaking change を検出してマークしてある、または non-breaking と確認済み。
- プロジェクト設定に応じた attribution が footer に含まれている。
- 出力が heredoc 形式 (= そのまま貼り付け可能)。

## Boundary

- subject を **絶対に** 70 文字超にしない。長い subject = コミットが大きすぎる。
- body を **絶対に** 受動態で書かない。現在形の命令形で。
- プロジェクト設定を確認せずに `Co-Authored-By` を **黙って** 含めない。個人リポジトリなどはオプトアウトしている場合がある。
- diff が示していることを body に **書かない**。body は why のために使う。
- 存在しない issue / PR 参照を **作らない**。実在するものだけ引用する。
- breaking change を能動的に検出 **しなければならない**。見落とすと次のリリースのバージョンが誤分類される。
- プロジェクトに既存のコミットスタイルがある場合はそれに **合わせなければならない** (= `git log --oneline -20` を読む)。
- ステージ済みの変更が空の場合は **止める** (= まだ `git add` していない)。ユーザーに伝える。
- 無関係な変更が複数ステージされている場合は **止める**。複数コミットに分割することを提案する。

## Helper

このスキルはオーケストレーションのみで、スクリプトはない。Lead がこのスキルを呼び出し、ステージ済み diff を読んで heredoc ブロックを出力することでメッセージを組み立てる。その後 Lead が実際の `git commit` コマンドを実行する (autonomous mode でない場合はユーザーの確認を取る)。

プロジェクトに `commit-msg` hook がある場合 (= lefthook の `commit-msg` が Conventional Commits の正規表現を実行)、hook が検証ゲートとして機能する。hook が却下した場合はユーザーに伝えて再度ドラフトする。

## Final Report

```yaml
commit-message:
  type: feat | fix | docs | style | refactor | perf | test | chore | ci | build | revert
  scope: <optional token | null>
  breaking: yes | no
  subject: <≤70 char>
  body_present: yes | no
  attribution: <co-authored-by line | null>
  references: [<issue/PR/ADR>...]
  heredoc: |
    git commit -m "$(cat <<'EOF'
    <type>(<scope>): <subject>

    <body if present>

    Co-Authored-By: ...
    EOF
    )"
```

## Worked examples

### Example 1: feat with scope and breaking change

```
feat(api)!: replace synchronous read_file with async io::read

Synchronous reads on the editor's main thread caused the UI to stall
on large markdown vaults. The async path uses tokio::fs and preserves
encoding detection.

BREAKING CHANGE: `Vault::read_file` is now `async fn`. Callers must
`.await` the result; sync callers should use `block_on` from the
runtime entry point.

Migration: replace `vault.read_file(p)` with `vault.read_file(p).await`
inside any async context; otherwise wrap in `tokio::runtime::Handle::block_on`.

Refs: ADR-0009
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Example 2: chore with no scope

```
chore: bump cargo-deny to 0.16.4

The 0.16.3 release shipped a regression in the licenses check that
flagged dual-licensed Apache-2.0 OR MIT crates as conflicting. 0.16.4
restores the expected behaviour.

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Example 3: docs, minimal body

```
docs(adr): mark ADR-0005 as superseded by ADR-0009

ADR-0009 replaced the sync I/O decision recorded in ADR-0005.
```

### Example 4: fix with referenced issue

```
fix(release): release-please PR title pinned to v0.X format

Without the pin, release-please occasionally proposes a title that
break the conventional-commits check on merge.

Closes: #142
```

## Related

- `$finish-task` — このコミットがまとめる完了報告を生成するスキル。
- プロジェクト側の `conventional-commits-check` (= 存在する場合) — このフォーマットを強制する `commit-msg` hook。
- `$task-routing` — `Lead-direct` の verdict の場合、Lead がコミット前にこのスキルを直接呼び出す。
