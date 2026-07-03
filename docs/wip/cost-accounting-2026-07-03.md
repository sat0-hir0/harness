# 自律運転コスト計測 (2026-07-03)

backlog 自律運転 (= cron heartbeat / completion-check / delegate 実装 chain / L2 eval) の初回コスト計測。session transcript (= `~/.claude/projects/*/*.jsonl`) の `usage` フィールドから token を集計し、API list price で USD 換算したクライアント側推定値。**請求データではない** (下部 Caveats 参照)。

## 使用モデルと単価

cron session (heartbeat / completion-check) と実装 chain の Lead は全 API call が **claude-opus-4-8** (1M context 変種、transcript の `model` フィールドで確認)。subagent は opus-4-8 / sonnet-5 / sonnet-4-6 / haiku-4-5 の混成。cache write は全サンプルで **1h TTL** (`cache_creation.ephemeral_1h_input_tokens`、5m TTL は 0)。

換算単価 ($/MTok): opus-4-8 = input 5.00 / output 25.00 / cache write (1h) 10.00 / cache read 0.50。sonnet 系 = 3.00 / 15.00 / 6.00 / 0.30。haiku 4.5 = 1.00 / 5.00 / 2.00 / 0.10。なお sonnet-5 には introductory pricing (= 2.00 / 10.00 / 4.00 / 0.20、2026-08-31 まで。pricing docs 記載) があり、本計測の「sonnet 系」単価は post-intro (= sonnet-4-6 と同額) で換算しているため、intro 期間中の sonnet-5 分は過大計上になっている。

## コスト表

| 項目 | 実測値 (n) | 単位換算 |
|---|---|---|
| issue-picking-heartbeat 1 cycle (silent) | $0.60 / $0.61 / $0.66 (n=3) | 平均 **$0.63/run** |
| completion-check-routine 1 cycle | $0.76 / $0.77 / $1.25 (n=3、$1.25 は精査実働あり) | 平均 **$0.93/run** (silent 下限 ~$0.76) |
| cron 1 日分 (現行 cadence: heartbeat `*/15` = 96 runs + completion-check `7-59/15` = 96 runs) | 96 × $0.63 + 96 × $0.76〜0.93 | **$133〜150/day** (30 日換算 $4,000〜4,500) |
| 実装 chain 1 ticket (heartbeat pick → issue-execute → 実装 → prepare-uat、subagent 込み) | #64: $13.87 / #76: $13.62 / #84: $10.93 (n=3) | 平均 **$12.8/ticket** |
| L2 eval 1 run (committed baseline) | $2.74 (committed 実測、今回再実行なし) | **$2.74/run** |
| L2 eval probe 1 発 | $0.19〜0.39 (probe JSON `total_cost_usd`、例: $0.296) | **$0.19〜0.39/probe** |

内訳の事実: cron 1 cycle のコストは 1h TTL cache write (~50%) + cache read (~30%) が支配的で、output token は少数派。実装 chain は cache read が支配的 (#64 で cache read 14.8M tokens = コストの 58%)。

## 計測方法 (各 1 行)

- **cron cycle**: `~/.claude/projects/C--Users-hiroki-code/*.jsonl` の先頭行 prompt 文言 (`automated backlog heartbeat` / `automated backlog completion-check`) で session を同定し、直近の各 3 サンプルの assistant 行 `usage` を `requestId` で dedup して合算 × list price。
- **per-day**: scheduled-tasks の cron 式 (`*/15` と `7-59/15`、いずれも 96 runs/day) × per-cycle 平均。
- **per-ticket**: heartbeat が pick して Completion Check まで到達した実装 session 3 件 (#64 = 2026-07-01 / #76 = 2026-07-02 / #84 = 2026-07-02〜03) を同手法で合算し、`<session-id>/subagents/*.jsonl` の subagent 分 ($1.19 / $5.19 / $1.52) を加算。
- **L2 eval**: committed baseline (`eval/baseline/`、`docs/wip/harness-evaluation-2026-07-02.md` L224 の $2.74) と probe JSON (`docs/wip/claude-p-probe-2026-07-02.json` の `total_cost_usd`) をそのまま引用。

## Caveats (明示)

- **クライアント側推定であり請求データではない**。transcript の `usage` × API list price の机上換算。実際の支払いは課金形態 (subscription plan / API 従量) に依存し、subscription 下ではこの数字は限界コストではなく「API 換算の消費量」として読む。
- **サンプルが小さい** (各カテゴリ n=3、直近 1〜3 日分)。completion-check は精査実働の有無で $0.76〜1.25 と振れる。実装 chain も ticket 難度で振れる (実測 range $10.9〜13.9)。
- **per-day は cron 固定費のみ**。pick が発生した日はその ticket の chain コスト (~$12.8/件) が上乗せされる。
- **dedup は `requestId` 単位**。retry / abort された request の計上漏れ・重複の可能性は排除しきれない。
- **per-ticket は heartbeat 起動分 (~$0.63) を含む** (pick と実装が同一 session のため分離不能)。wall-clock (#84 は 8.5h) には rate limit 待ちを含み、コストとは相関しない。
- **opus-4-8 1M context 変種は標準単価 (long-context premium なし) を仮定** (現行 docs 準拠)。
- **L2 eval の数字は committed 成果物の引用**で、本計測日での再実行値ではない。

## 再現手順

集計スクリプトは session 側 scratchpad で実行 (repo 非同梱)。ロジック: jsonl の `type == "assistant"` 行から `message.usage` を取得 → `requestId` で dedup → model 別に input / output / cache_write (5m / 1h 分離) / cache_read を合算 → 上記単価で USD 換算。同等の集計は `ccusage` 等の transcript 集計ツールでも再現可能。

Refs: sat0-hir0/backlog#113
