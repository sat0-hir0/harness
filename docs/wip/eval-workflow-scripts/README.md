# eval-workflow-scripts — 評価 workflow の実装保全

ハーネス評価 (= `docs/wip/harness-evaluation-2026-07-02.md`) とメタ評価 (= `docs/wip/harness-meta-evaluation-2026-07-20.md`) を実行した workflow script の保全 copy。

- 保全の動機はメタ評価の提案 4: 評価 session の main transcript は retention で消失済みで、script が「judge に実際に与えた prompt」を示す唯一の実装証跡。run 1-3 の script は保全前に消失した (= 欠番)。
- `run4`〜`run8` = 評価 run 4〜8 の実装。`meta-eval-2026-07-20.js` = メタ評価自体の実装。
- これらは記録であり、再実行用の maintained asset ではない (= path 等は実行時点のもの)。
