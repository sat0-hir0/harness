# ADR-0001: branch 段階の検証済み定義と CI green の位置づけ

## Status

Proposed

## Context

`.github/workflows/eval-gate.yml` の trigger は `push: branches: [main]` と `pull_request` のみで、 feature branch 単独の push では CI が起動しない。 AI は PR を作らない (= 人間の責務、 `docs/harness-design.md` §15 「AI 自己判定での PR merge」 不採用と同軸) ため、 「CI green」 を branch 段階の完了条件に含めると、 AI が branch 段階で満たせない条件になる。

backlog Issue #124 で、 branch 段階の 「検証済み」 の契約と CI trigger 設計が矛盾した状態のまま運用され、 pick → bounce が繰り返されて `needs-human` に封止される実害が発生した。

## Decision

branch 段階の 「検証済み」 の定義を **local lefthook gate (= eval-gate / frontmatter-lint / agent-ref-lint) の pass + test 通過** に固定する。 CI green は branch 段階の deliverable から除外し、 PR / Done 段階で人間が確認する事項とする (= `docs/harness-design.md` §16 の Done 定義 = PR merge と整合)。

`.github/workflows/eval-gate.yml` に `workflow_dispatch` を追加し、 AI が `gh workflow run eval-gate.yml --ref <branch>` で branch 段階でも CI を任意に起動できる経路を用意する。 この経路は opt-in の客観証跡取得手段であり、 完了条件ではない。

feature branch の `push` を trigger に追加しない。 追加すると future-plans lint の `github.base_ref` が `push` イベントで常に空になり base_ref 解決が破綻する (= 過去の #117 と同種の回帰)。 加えて、 CI と local lefthook gate が同一内容を feature branch push のたびに二重実行することになる。

## Consequences

- AI は branch 段階の完了条件として CI green を待たない。 local lefthook gate の pass のみで branch 段階を完了とみなせる。
- CI green の確認は PR 作成後、 人間が UAT / merge 判断の一部として行う。
- `workflow_dispatch` 経由の任意起動時は `BASE_REF` が `main` に fallback するため、 future-plans lint は dispatch でも base_ref malformed で fatal にならず動作する。
- feature branch push trigger を追加しないため、 branch 段階で CI green を客観的に確認したい場合は `workflow_dispatch` を明示的に呼ぶ必要がある (= 自動では回らない)。
