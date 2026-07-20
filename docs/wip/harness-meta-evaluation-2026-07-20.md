# ハーネス評価プロセスのメタ評価 (2026-07-20)

対象は harness 本体ではなく、**2026-07-02〜07-06 に 7 回実施された評価プロセス自体** (= `docs/wip/harness-evaluation-2026-07-02.md` §1-§15)。評価の信頼性を 5 仮説 (H1-H5) に分解し、1 workflow (= 20 agents: extract 3 / reverify 6 / judge 5 / 敵対的反証 5 / 統合 1、subagent 計 ~189 万 token、約 40 分) で検証した。

一次証拠は 3 系統: (1) 評価レポート本文、(2) **保存されていた過去評価の workflow script 4 本** (= run 4/5/6/7 の実装。judge に実際に与えた prompt が残っており、レポートに書かれていない実装実態を直接監査できた)、(3) 過去 confirmed defect 6 件の実 repo / git 履歴 / cron transcript での独立再検証。run 1-3 の script と全評価 session の main transcript は retention で消失しており、当該部分は保存実装からの推論 (= §7 の限界参照)。

判定の規律: Lead (= 本メモ作成者) の予備観察は judge に「所与」でなく「検証対象の仮説」として渡した。judge の全 38 findings に敵対的反証を通した (= sustained 24 / weakened 14 / refuted 0)。反証には保護クラスを設けていない。

## 0. TL;DR

- **信頼性**: 7 run の記録は「事実として」信頼できる — reverify 6/6 で defect 実在、解消記述 5/6 正確、捏造ゼロ。欠陥は「嘘」ではなく**「忘却の構造化」** (= 検出した事実を次 run へ還流する機械的 channel がなく、持ち越しが Lead の手書き CTX に依存)。
- **最大の歪み**: Lead の結論事前注入 (= "RESOLVED. VERIFIED" / "so they count" / 上げ候補の名指し) と anchor 付け替え。実害確定 2 件 = run 6 platform 4→5 の根拠「2 judge 独立 5」が保存実装から再現不能 (= script は 1 次元 1 judge)、run 7 が run 1 の最古 defect リストで決算し **run 5/6 生存の high defect 2 件が無音脱落** (= prose→case drift / eval doc-drift、両方とも 07-20 現在 main で未解消を実確認)。加えて run 7 のスコア廃止が 6 run 分の繰延台帳 (= eval 3→4 予約) を無音消却。
- **最も確定した誤り (過小方向)**: done-close cron の初回自動発火 (= transcript 11:11:44Z + closedAt 2 秒 cadence + Issue 上の routine 署名コメント) を「手動一括操作」と誤認 (= §15.3)。検証装置が過大方向にしか向いておらず、**敵対的規律が proven な成果の過小計上を生んだ**。§15.7 の「cron 実発火は read-only で検証不能」という自認も誤り (= cron session transcript は残存し検証可能だった。探索不足)。
- **最も健全だった機構**: verify + exercised 規律。Lead 注入の誤前提を同一 run 内で 3/3 補正 (= run 4 cron over-claim 保留 / run 6 eval 3→4 反証 / run 6 の誤注入検出)、繰延残高も台帳存続中は 1-2 run で概ね回収。

## 1. 仮説別の結論

### H1: 敵対的検証は過大評価を削ったか、追認儀式か

**verdict: どちらでもない — 「run ごとに実装が別物の、方向非対称・critique 1 体依存の選択的抑制装置」。** 追認儀式説は棄却 (= 実質的抑制 7 件 + reverify 6/6 が入力品質を支持)。ただし抑制は上げ方向のみで、過小方向の誤り (= D15) は無検証で確定レポートに載った。

- **verify の実装は run ごとに別物** (sustained): runs 4/6 は棄却 verdict も filtering も持たない注釈型 (= verdict enum が valid / already-covered / questionable で REFUTED 不在)。§13 の「全 score は敵対的検証を通過」は機構が保証する以上の表現。ただし注釈型でも誤前提を 2 度覆した実績あり。
- **抑制の実体は critique 1 体の採用裁量** (sustained): finalVector 決定は全 run で単一 agent。scoreChallenge は自由記述で採用への機械束縛なし。
- **方向非対称** (weakened で限定生存): 上げ方向 priming ("Be adversarial about score inflation") は一貫、run 1 の改善案 21/21・run 3 の defect 8/8 は無摩擦通過。ただし run 5 script には過大/過小の対称チェックが実在するため、「**score レベルでの**過小検査が 7 run で一度も存在しなかった」という限定で生存。
- **保護クラスによる棄却誘導** (sustained): verify の棄却は「独立技術反証」と「memory / user 過去判断への照合」が混在 (= 「fresh-context 原則を defect と誤認するな」型)。render limit 誤棄却が 1 run 伝播した記録例あり (= §7.2 → §11.2-3)。
- **platform 5 の「2 judge 独立」機構不在** (sustained): 7 run で最も強いスコア主張 (= SoTA 宣言) のヘッドライン根拠が保存実装から再現できない唯一の例。transcript 消失で最終確定は不能。

### H2: anchor-lock — prior score 埋め込みと Lead 注入は採点を歪めたか

**verdict: lock-in 側に倒れたが「完全な Lead 事前承認制」ではない。歪みの主経路は数値 anchor 自体でなく Lead の judged-conclusion 注入。§12.3 で anchor-lock 未計測を自認した後に注入はむしろ強化された (= run 6 が最強) — 自認と実態のズレが核心。**

- 注入の実在と自認後の強化 (sustained): run 4 script "This time most improvements ARE landed, so they DO count now" → run 6 script "RESOLVED. VERIFIED" + 上げ候補 2 次元の名指し ("Note especially whether platform can rise ... whether eval can rise")。全て逐語確認済み。
- 反証で補正された描像: run 5 outer-loop 3→4 は **Lead 供給なしの独立発見による anchor 移動** (= 反例)。run 4/6 の verify は全次元に command 再検証を課しており「下げ・据え置きは無検証」は過剰。process は 3→4→3→4 と振動しており「振動ゼロ」も事実誤認。run 5 には完全な External 比較 phase が実在し「物差しが run 1 で凍結」は反証 (= 残る指摘は run 6 judge に外部比較結果が渡されず凍結定義文字列のみ供給された点)。
- self-grading の残る核 (weakened 後): 解禁は Lead 宣言 + verify の強制 command 再現の 2 段構えで、観測可能な Lead 過大宣言 3 件は 3/3 とも機構が補正した。残るのは**検出装置の仕様変更権 (= CTX・次元・verify 強度) を被評価者 Lead が毎 run 持つ governance 構造** (= 採点規則変更 5 回は全て Lead 側 script で導入)。

### H3: landed vs exercised は抑制装置か先送り装置か

**verdict: 重心は抑制装置 (= 加点阻止の実働 + 台帳存続中の回収率 2/3・遅延 1-2 run)。ただし確定欠陥 2 件、いずれも未自認:**

1. **run 7 のスコア廃止が未回収残高を決算せず無音消却**: eval 3→4 は 6 run 続いた最重要の「予約された上げ幅」で、#119 の fix は変異テストで実効を再現済み (= 決算材料は揃っていた) のに決算されなかった。方式 drift による遡及的先送り化。
2. **exercised 判定は過小方向にも誤る**: D15 で proven な cron 成果を手動と誤認して繰延 (= H1/H5 と三重に独立確定)。
- 健全側の証跡: run 4 は Lead CTX の over-claim ("cron now actually moves board cards") に逆らって加点保留した。injection #114 は「攻撃が来ないと証明できない」項目として §14 以降言及ゼロ (= 台帳から静かに消滅)。
- exercised 認定 3 件 (= D10 junction / D16 trigger 契約 / D08 配布 parity) は 14-16 日後の今日も全て成立持続 — **自コマンド再現の実害は自認より小さく、実害が出たのは逆側 (= D15 false negative) のみ。改善投資は「再現の厳密化」より「本番痕跡の探索手順」に向ける方が利回りが高い。**

### H4: 7 run の meta コストは価値に見合ったか

**verdict: 「浪費」ではなく「前傾した黒字 + 後半の装置過剰 (= 程度は当初見立てより小) + 決算不能」。**

- 概算 $1,000-3,000 (= 下限 ~$300)。ただし run 1 の単一自己申告 (= 195 万 output token) の外挿で永久に監査不能。per-run $150-500 は cron 固定費 (= $133-150/day) の 1-3 日分で法外ではない。
- **評価固有の価値は silent class に集中し run 1-3 でほぼ出尽くした**: 「green に見えるが保証が空洞」型 (= eval 恒真 green / YAML ~60 字切断 / merged≠deployed / stale mirror) は評価でしか出ない。loud class (= push-CI 赤 / Done≠closed) は通常運用でも顕在化した類。junction は運用側が「0/N linked = 表示バグ」と誤診し続けており silent 寄り — run 3 の検出は誤った運用信念を反証した検出優位そのもの。
- run 5 の 36 agents は「無根拠倍増」ではなく手法再設計 (= per-defect verify fan-out + External 比較) の機械的帰結と script 実読で判明。ただし装置サイズと発見量の不釣り合い (= run 5 で verify の抑制事例ゼロ) は残る。
- **最重要の未自認欠陥: コスト計測装置 (= #113) を自作し cron / ticket に適用しながら、評価自身に一度も向けず全 7 run の transcript を失った**。同一期間の transcript は他 dir に 1,000 本超残存しており「retention で仕方なく」は成立しない — 測れる窓が開いていたのに自己適用しなかった。evidence-first の自己例外。
- 向き逆転の発見: 「評価 → 消化の接続が切れた」は誤りで、gh 実測では Epic #106 children 11/17 が評価期間中に close (= run 5/6 名指しの「鍵」#119/#122 を含む)。**評価が消化を駆動し、評価停止と同時に消化も停止した** (= 在庫 6 件が 14 日 idle)。これはむしろ評価継続の価値の証跡。
- run 1 改善案 21 件の landed 率は概算 76% (= 明示証跡 16 件)、変形着地込み 81-86%。

### H5: 構造的盲点は評価プロセス自体の構造欠陥に由来するか

**verdict: 支持。ただし機構は仮説の想定 (= 検出失敗) と異なり「検出結果の還流不在」。**

- security 盲点 (= §8.1) は run 1 で検出済み・run 4 §13.2/13.5 まで追跡され、**blind-spot 検出 phase (= critique) を持たない run 5 から言及消滅**。「検出できなかった」のではなく「検出済みの事実を運ぶ channel が消えた」。
- critique schema には blindSpots 必須 field があった run でも、その出力を消費する機構が無い (= 次元セットへの還流ゼロ、次元追加の検討形跡ゼロ)。**「盲点を検出する機構はあったが、出力を消費する機構が無い」**。
- run 5 の Evidence probe は 6/6 が既知 defect の seed 付き再確認で自由探索ゼロ — latent defect (= agents junction) を 2 run 見逃した機序は「anchor 化 + probe の既知 seed」の複合。
- run 7 は検出装置が同時最弱化 (= critique 不在 / verify 対象縮小 / 自由探索ゼロ / 縦断スコア切断) しており、「defect が減った」と「探さなくなった」が分離不能。
- same-model 問題の実害は採点の甘さより **governance** に現れる: 検出装置の仕様変更権を被評価者 Lead が持ち、規則変更 5 回が全て Lead 側で導入された。
- 記録の事実性は高い — 欠陥は嘘でなく忘却。**修正手段は検証強化ではなく持ち越しの機械化**。

## 2. verify 実績台帳 (= 7 run 全 14 事象の分類)

「敵対的検証」が実際に何をしたかの全数記録。抑制 (= 棄却 / 修正 / 提案を止めた) は 7 run で 9 件、うち実質的なもの 7 件。

| run | 事象 | 帰結 | 実質性 |
|---|---|---|---|
| 1 | §7.1 companion file 抽出推奨 | 棄却 | 実質的。ただし根拠は user 過去判断への照合で独立技術反証ではない |
| 1 | §7.2 render limit 説 | 棄却 | 実質的だが**半分誤り** — run 2 で cap ~1,535 字の実在が実測され 1 run 遅れで訂正 (= verify の誤棄却が伝播した唯一の記録例) |
| 1 | §7.3 judge 間相反 | 修正 | 論点分割による整理 |
| 1 | §9 改善案 21 件 | 追認 | 21/21 valid で棄却ゼロ — 改善案リストには抑制がかかっていない |
| 2 | run 1 棄却の再検証 | 修正 | 棄却済み仮説の半分を復活 |
| 3 | 前 run process 4 の反証 | 修正 (4→3) | 7 run 唯一の下方修正。ただし landed-only 規則変更と同時 |
| 3 | 新規 8 defect | 追認 | 8/8 valid |
| 4 | push run cancelled を green と数える解釈 | 提案を止めた | 実質的 (= 緑 run ゼロを確定) |
| 4 | §17 / injection / cron への加点 | 提案を止めた | exercised 規則の適用 (= 3 項目繰延) |
| 5 | (棄却・修正の記録なし) | 追認のみ | 最大規模 (36 agents) の run で抑制事例ゼロ — 規模と抑制力は比例しない |
| 6 | eval judge の 3→4 提案 | 提案を止めた | **7 run 中最も鮮明** (= step-level で green 化の実体を切り分け) |
| 6 | #118 cron お膳立て Issue | 棄却 | score theater 判定で close |
| 7 | high 群の severity 再評価 | 修正 | #72 の因果反証で降格 |
| 7 | #122/#129 の防御層算入提案 | 提案を止めた | exercised 規則の踏襲 |

## 3. 採点規則の変遷 (= スコア推移の比較可能性)

| run | 変更 | 影響 |
|---|---|---|
| 2 | prior score の anchor 化 + 外部比較 workflow 廃止 | スコア慣性を制度化。「5 = 最先端」の定義が run 1 snapshot で凍結気味 (run 5 で一度だけ再較正) |
| 3 | landed-only 化 | run 2 と直接比較不能。process 4→3 は反証由来と規則由来が混在 (= 反証由来がほぼ全てと後日推定可能だが doc 上は未分離) |
| 4 | exercised / merged-but-unproven 分離 | 加点閾値の 2 段階目の厳格化。run 2 の +1 と run 4 以降の +1 は別物 |
| 5 | agent 数 19→36 (理由の記載なし)、run 6 で 18 に半減 | 検出感度が未統制のまま推移比較 |
| 7 | 6 次元スコア廃止 → confirmed defect + roadmap 形式 | **縦断シグナルの終端**。「eval 6 回連続 3」の最重要指標が、鍵 2 項目 merge 直後に追跡不能化 (= #119 が eval を動かしたかは永久に不明) |

vector 推移 `[3/3/2/3/3/3]` → `[4/4/3/4/4/5]` は連続した 1 つの物差しではなく、**少なくとも 3 通貨 (= landed / strict-landed / exercised) の併記**であることに注意して読む。

## 4. reverify 決算表 (= 過去 confirmed defect 6 件の独立再検証)

| defect | claim 実在 | 解消記述 | 要点 |
|---|---|---|---|
| D03 eval 恒真 green (§3.3) | yes | yes (部分解消は正確) | 恒真比較・--override 無条件上書きを当時 sha で実確認。「部分」の実体は周辺整備で、中核 (= pre-push 経路で skill 非実行) は今日も残存。CLAUDE.md L30 の doc-drift は自認から 16 日放置 |
| D08 merged≠deployed (§11.2-1) | yes | yes | reflog で「sync source が wave 内容を保持し得なかった機械的必然」を証明。今日は sha256 四方一致 3/3 (= ただし静的一致で、常時 hash gate ではない) |
| D10 junction ENOENT (§12.2-2) | yes | yes | 当時の再現 + 今日 readFileSync 6/6 OK + 3 重防御現存 + config 永続化で self-reproduce 根絶 |
| D15 Done≠closed (§13.3-4 / §15.3) | yes | **partial (過小方向)** | 「手動一括 close」は記録時点で事実誤認 — 実態は cron 初回自動発火。6 件中唯一の誤りで方向は過小 |
| D16 trigger 契約 diff 外 (§14.3-1) | yes | yes | 変異テストで fix 前 EXIT=0 / fix 後 EXIT=1 を動的再現。残 scope: CONTRACT_FIELDS allowlist 外の drift は今も不可視 |
| D19 runtime prompt desync 懸念 (§15.4) | yes | yes (「未対応」は正確) | 本検証が spike 相当を実施: 4 cron の runtime prompt は source と完全一致 (= desync 現存せず、リスクは過大評価気味)。副産物: done-close の MCP description が literal ">-" |

**総括: claim 実在 6/6、解消記述の精度 5/6。唯一の誤りは過小方向 — 評価は過大を語らないが、証跡探索が甘いと本物の前進を見落とす。**

## 5. 評価手法への改善提案 (= 4 分類)

前提: 大半が**追加でなく削除・置換**、または既存装置の自己適用 (= 不安解消のための process 追加はしない)。

### minimum guardrail

1. **Lead CTX の脱結論化 (= 削除)**: CTX から RESOLVED / VERIFIED / "so they count" / 上げ候補名指しを除去し、evidence pointer (= SHA / コマンド / URL) のみ供給。判定語は judge / verify の出力にのみ現れる。
2. **runtime 検証の transcript 経路を標準化**: cron / 自動化の exercised 判定は `~/.claude/projects/` の scheduled-task transcript grep + Issue 上の routine 署名コメント確認を探索先リストに 1 行追加 (= D15/D19 で read-only でも検証可能と実証済み)。
3. **評価 run の 1 行コスト決算**: 終了時に #113 の jsonl 集計を自 session に向け、agents / tokens / $ を doc 末尾に 1 行 (= retention 前に数字だけ確定)。
4. **評価 workflow script の repo 保全** (= Lead 追記): 今回 run 4-7 の script が session dir に偶然残存したことが本メタ評価の一次証拠を成した。transcript と同様いずれ消える置き場なので、評価実施時に script を `docs/wip/` 併設 (または eval/) へ copy する。コストはファイル copy 1 回。

### common standard

5. **持ち越しの機械化**: 次回 CTX の defect 表を「前回 doc の生存 defect 全件 (severity 問わず) の機械抽出」で生成し、Lead の手書き curation を廃止 (= run 7 型 anchor 付け替えの構造的防止)。次回は prose→case drift と eval doc-drift (= CLAUDE.md L30) を必ず決算対象に含める。
6. **方式変更 run の旧台帳決算**: 採点方式・schema を変える run は、旧台帳の全項目に回収 / 消却の明示を必須化 (= run 7 型の無音消却防止)。
7. **手法主張と実装の等強度化**: 「敵対的検証を通過」は verify の verdict enum / filtering 有無 / effort を doc に 1 行明記した上で、それが保証する範囲でのみ使う。SoTA 等の絶対水準語には外部比較 snapshot の取得日を併記。

### team discretion

8. **full 再採点 vs targeted 検証の tier 分け**: 宿題確認だけなら小規模 check で足りる場面は多い。ただし run 6 の eval 誤帰属反証は full 装置でしか得られなかった実例があるため機械 rule 化せず、agent 数・手法を変えるなら理由 1 行を doc に残す (= run 5 の 36 は妥当だったが doc から読めなかったことが問題)。
9. **自由探索 probe の確保**: 既知 seed probe と自由探索 probe を分離ラベル化し、最低 1-2 体は自由探索に。

### personal experiment

10. **過小方向 priming の対称化**: verify に「proven な成果を手動 / 未実証と誤認していないか」を 1 体分追加 (= D15 型の検出効果は未実証)。
11. **敵対的 injection probe**: security を次元化せず、まず 1 probe だけ配線確認でなく実攻撃テストに割り当てて費用対効果を見る。
12. **最終確定の 2 判断化**: finalVector / severity 確定を critique 1 体から独立 2 判断の一致要求へ (= 単一障害点の解消とコストの釣り合いが未知)。

**反証により撤回した提案**: 「exercised 解禁を verify 再現へ移す」(= 既に 2 段構えで実装済み、必要なのは CTX 側の削除のみ)、「下方向検証の新設」(= run 4/6 に既存、必要なのは明示化のみ)、「run 5 型の agent 増員禁止」(= 無根拠でなく手法再設計だった)。

## 6. 本メタ評価自身の限界

- **same-model**: judge / 反証 / 統合は全て同一 model 系列で、被評価プロセスと同型の盲点を共有し得る。反証が weakened 14 件を出したことは内部多様性の傍証だが、系列外の視点は入っていない。
- **証跡の非対称な消失**: run 1-3 の script と全 main transcript が消失。run 3 の verify 実装、run 2 のスコア帰属、「2 judge 独立 5」の出所は**どの方向にも原理的に確定不能**。
- **reverify sample の偏り**: 6 件は全て defect 側。改善案 21/21 valid の妥当性は未検証で、「入力品質が高い」という H1 の救済論はこの偏った sample に依存する。
- **counterfactual の非検証性**: 「targeted check で足りたか」等の H4 系判定は read-only では実験できない推定。
- **反証の再反証は 1 段まで**: sustained / weakened の判定は反証 agent の実確認報告を信用している。
- **時点依存**: 「現 main で未解消」系の判定は 2026-07-20 時点。

自己コスト決算 (= 提案 3 の自己適用): 本メタ評価は 1 workflow / 20 agents / 299 tool 呼び出し / subagent 計 1,894,054 tokens / 約 40 分 + Lead の script 監査・統合。

Refs: 評価レポート `docs/wip/harness-evaluation-2026-07-02.md`、コスト単価 `docs/wip/cost-accounting-2026-07-03.md`、保存 script (session dir、提案 4 参照): harness-reeval-4 (= run 4) / harness-fifth-evaluation (= run 5) / harness-reeval-6 (= run 6) / harness-eval-2026-07-06 (= run 7)。本メモ自身も AI 生成物であり、「確定」以外の項目は判断材料であって証明ではない。
