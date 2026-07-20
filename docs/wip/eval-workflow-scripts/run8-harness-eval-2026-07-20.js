export const meta = {
  name: 'harness-eval-8-2026-07-20',
  description: '8th harness evaluation applying meta-evaluation method fixes: no Lead conclusion injection, mechanical carry-over ledger, symmetric verify, dual final vector, 14-day unattended-operation audit',
  phases: [
    { title: 'Ledger', detail: 'mechanical carry-over extraction from prior docs' },
    { title: 'Evidence', detail: '7 probes incl. 2 free-exploration + 14-day runtime audit' },
    { title: 'Score', detail: '6 dimension judges, settle old ledger' },
    { title: 'Verify', detail: 'symmetric adversarial verify (over + under)' },
    { title: 'Vector', detail: 'two independent final vectors + reconcile' },
    { title: 'Critique', detail: 'blind spots + dimension-set review' },
  ],
}

const H = 'C:/Users/hiroki/code/harness'
const B = 'C:/Users/hiroki/code/backlog'
const D = 'C:/Users/hiroki/code/dotconfig'
const EVAL_DOC = H + '/docs/wip/harness-evaluation-2026-07-02.md'
const META_DOC = H + '/docs/wip/harness-meta-evaluation-2026-07-20.md'
const CRON_TX = 'C:/Users/hiroki/.claude/projects/C--Users-hiroki-code'

const CTX = `## 第 8 回ハーネス評価 (2026-07-20)
対象: AI 開発ハーネス。repos: ${H}, ${B}, ${D}。deployed: ~/.claude。cron transcript: ${CRON_TX}/*.jsonl (= scheduled-task session)。
記録: ${EVAL_DOC} (= run 1-7)。メタ評価: ${META_DOC} (= 評価手法自体の監査。本 run はその改善提案を適用する)。

本 run の手法 (= メタ評価提案の適用、開示用):
- Lead CTX は evidence pointer のみで、判定済み結論を含まない。過去 doc の記述は「主張」であり、採点に使う場合は必ず自力で spot-check する。
- exercised 判定は cron transcript (${CRON_TX}) と Issue 上の routine 署名コメントの探索を必須とする (= 過小計上の防止)。
- verify は過大・過小の両方向を対象とする。
- 前回スコア (= anchor、歴史的事実): run 6 (2026-07-04) [context 4 / routing 4 / eval 3 / outer-loop 4 / process 4 / platform 5]。run 7 (07-06) はスコア無し (= 方式変更)。run 7 の方式変更で未決算の繰延・生存 defect 台帳が残っており、本 run で全件決算する。
- 特記: 07-06 の run 7 以降 14 日間、評価は停止し自律運用 (= cron) のみが走った。この 14 日間を無人運用の自然実験として扱う。
- score theater 禁止。landed / exercised の区別は継続。read-only (= gh mutation / repo への file write 禁止)。
- 出力の文章は日本語 (field 名は英語)。証跡は file:line / §番号 / コマンド出力で。`

const LEDGER_SCHEMA = { type:'object', required:['items'], properties:{ items:{ type:'array', maxItems:40, items:{ type:'object', required:['id','source','title','type','status_claimed','dimension_hint'], properties:{ id:{type:'string'}, source:{type:'string'}, title:{type:'string'}, type:{type:'string',enum:['defect','reserved-raise','open-question','spike']}, severity_claimed:{type:'string'}, status_claimed:{type:'string'}, dimension_hint:{type:'string',enum:['context','routing','eval','outer-loop','process','platform','cross']}, verify_hint:{type:'string'} } } } } }

const PROBE_SCHEMA = { type:'object', required:['area','facts','summary'], properties:{ area:{type:'string'}, facts:{type:'array',maxItems:20,items:{type:'object',required:['claim','evidence'],properties:{claim:{type:'string'},evidence:{type:'string'}}}}, anomalies:{type:'array',maxItems:10,items:{type:'string'}}, summary:{type:'string'} } }

phase('Ledger')
const ledgerP = agent(`${CTX}\n\n役割: 持ち越し台帳の機械抽出 (= メタ評価提案 5 の実装)。${EVAL_DOC} と ${META_DOC} を精読し、**生存している全項目を severity 問わず機械的に列挙**せよ。curation 禁止 — 「後続 run で解消が明示宣言されていない」defect / 繰延 (= reserved-raise、例: eval 3→4 の予約) / open-question / spike を全件。メタ評価が「無音脱落」と指摘した項目 (= prose→case drift、eval doc-drift 等) と「メタ評価自身が新規に見つけた副産物」(= MCP description 不衛生等) も含める。各項目に source (= 初出 §)、status_claimed (= 記録上の最終状態)、dimension_hint、verify_hint (= 今日の確認手順) を付けよ。`, { label:'ledger', phase:'Ledger', schema:LEDGER_SCHEMA })

const PROBES = [
  { key:'FREE-harness', prompt:`役割: **自由探索 probe (seed なし)**。${H} と deployed ~/.claude を先入観なく探索し、壊れているもの・矛盾・劣化・不整合を何でも見つけよ。過去評価の defect リストは渡さない — 既知を再確認するのでなく、新しい目で見よ。skill 本文 / agent / eval / scripts / CI / git 状態 (branch 発散含む) を自由に。` },
  { key:'FREE-outer', prompt:`役割: **自由探索 probe (seed なし)**。${B}、${D} の scheduled-tasks、gh の backlog board (= project 1, --limit 300) を先入観なく探索し、外側ループの壊れ・矛盾・劣化を何でも見つけよ。既知リストなし。Issue / label / branch / worktree (~/code/.worktrees) / cron 定義を自由に。` },
  { key:'runtime-14d', prompt:`役割: 14 日間 (07-06〜07-20) の無人運用監査。${CRON_TX}/*.jsonl から scheduled-task session (= 冒頭に <scheduled-task name=...> ヘッダ) を同定し:\n1. heartbeat: 14 日間で Issue を pick したか。しなかったなら transcript 内の実際の判断理由を引用 (= Ready 在庫があるのに pick しない理由)\n2. completion-check / done-close: 実発火の頻度と結果 (= verdict / close / no-op)\n3. エラー・異常・rate limit・失敗 run の有無\n4. 各 cron の runtime prompt に Untrusted content guard (= §0) が実際に載っているか\n5. 14 日間の cron 概算コスト (= jsonl の usage を requestId dedup で集計、${H}/docs/wip/cost-accounting-2026-07-03.md の単価で換算)\nfile が多い場合は日付 sample (= 07-07 / 07-10 / 07-14 / 07-19 前後) で層化してよいが、pick 有無は全期間を確認せよ。` },
  { key:'board-state', prompt:`役割: board / git 実データ監査。gh で backlog board 全件 (--limit 300) + issue state 乖離 + running / needs-human / long-running label の残留 + open PR / 未 merge branch (harness / backlog 両方) + ~/code/.worktrees の残骸。harness repo の main と現 branch (docs/7th-eval-and-agents-md) の発散も。実データのみ。` },
  { key:'eval-infra', prompt:`役割: eval 基盤の現状監査。${H}/eval/ と scripts/ と .github/workflows/ を読み: L1/L2 の実カバレッジ、CONTRACT_FIELDS の範囲 (= allowlist 外 field の drift 可視性)、behavioral-baseline の鮮度、gate 配線 (= lefthook / CI に何が載っているか)、--override の現機構、eval 関連 doc (= CLAUDE.md / eval/README.md / test-strategy) と実装の drift。実行できる check (= eval-regression --skill all 等の read-only 実行) は実行して exit code を報告。` },
  { key:'security', prompt:`役割: injection surface の構造監査 (= 実攻撃はしない、read-only)。write 権限つき gh を持つ cron が 15 分毎に untrusted issue body を読む構造について:\n1. 各 cron SKILL.md の Untrusted content 経路 (= issue body / comment を prompt に流し込む箇所) と guard の実装 (= §0 配線が「読む」だけか「効く」構造か)\n2. gh token の scope / 到達可能な破壊操作 (= blast radius: close / label / comment / branch 削除?)\n3. 実際の 14 日間の transcript に外部由来 text が指示として解釈された形跡があるか (= sample 検査)\n4. 実攻撃テスト (= 無害 payload を test Issue に置き cron の挙動を観測する) の設計案 — 設計のみ、実行しない\n過去評価が 7 run 触れなかった領域なので、構造の事実を丁寧に。` },
  { key:'dist-parity', prompt:`役割: 配布層 parity 監査。harness main の skills/ agents/ → ~/.config/skillshare/ → ~/.claude/ の sha256 全件比較 (= 6 skill + 6 agent)。dotconfig の chezmoi status。scheduled-tasks MCP の登録 metadata (= list_scheduled_tasks を ToolSearch で load して呼ぶ、read-only) と dotconfig source の整合。backlog 3 skill の parity も。` },
]

phase('Evidence')
const [ledger, ...probes] = await parallel([ () => ledgerP, ...PROBES.map(p => () => agent(`${CTX}\n\n${p.prompt}`, { label:`probe:${p.key}`, phase:'Evidence', schema:PROBE_SCHEMA })) ])
const probeDigest = JSON.stringify(probes.filter(Boolean))
const ledgerJson = JSON.stringify(ledger || {items:[]})
log(`ledger ${ledger && ledger.items ? ledger.items.length : 0} 件 / probe ${probes.filter(Boolean).length}/7`)

const DIMS = [
  { key:'context', name:'context 経済性', anchor:4 },
  { key:'routing', name:'routing 信頼性', anchor:4 },
  { key:'eval', name:'eval・観測性', anchor:3 },
  { key:'outer-loop', name:'外側ループ自動化', anchor:4 },
  { key:'process', name:'process 重量 vs 価値', anchor:4 },
  { key:'platform', name:'platform 適合', anchor:5 },
]

const SCORE_SCHEMA = { type:'object', required:['dimension','score','rationale','ledger_settlement','defects'], properties:{ dimension:{type:'string'}, score:{type:'integer',minimum:1,maximum:5}, rationale:{type:'string'}, ledger_settlement:{type:'array',items:{type:'object',required:['ledger_id','resolution','evidence'],properties:{ledger_id:{type:'string'},resolution:{type:'string',enum:['回収','消却','繰延','残存']},evidence:{type:'string'}}}}, defects:{type:'array',maxItems:8,items:{type:'object',required:['title','severity','evidence'],properties:{title:{type:'string'},severity:{type:'string',enum:['critical','high','medium','low']},evidence:{type:'string'},file:{type:'string'}}}}, uncredited_progress:{type:'array',maxItems:5,items:{type:'object',required:['title','evidence'],properties:{title:{type:'string'},evidence:{type:'string'}}}} } }

const VERIFY_SCHEMA = { type:'object', required:['dimension','scoreChallenge','verdicts'], properties:{ dimension:{type:'string'}, scoreChallenge:{type:'string'}, verdicts:{type:'array',items:{type:'object',required:['title','direction','verdict','reasoning'],properties:{title:{type:'string'},direction:{type:'string',enum:['over','under']},verdict:{type:'string',enum:['CONFIRMED','PLAUSIBLE','REFUTED']},reasoning:{type:'string'}}}}, settlement_check:{type:'string'} } }

const judged = await pipeline(
  DIMS,
  d => agent(`${CTX}\n\n役割: 次元「${d.name}」の judge。anchor = run 6 の ${d.anchor} (= run 7 スコア無しのため直近の採点)。anchor から動かすには自力 spot-check 済みの証跡が要る — 上げ・下げ・据え置きのいずれも根拠を示せ。\n\n持ち越し台帳 (機械抽出、当次元 = dimension_hint が「${d.key}」または cross の項目は**全件** settle せよ。回収 = 解消を証跡で確認 / 消却 = 根拠付きで閉じる / 繰延 = 未証明のまま継続 / 残存 = defect として残る):\n${ledgerJson}\n\nEvidence probes (7 本、うち 2 本は自由探索):\n${probeDigest}\n\n注意: (1) 過去 doc の「解消」宣言は主張 — spot-check せよ。(2) exercised 判定は transcript 経路 (${CRON_TX}) を探索してから。(3) uncredited_progress = 記録に載っていないが証跡のある前進 (= 過小計上の防止) を明示的に探せ。(4) 14 日間の無人運用の実績はこの次元にどう効くか。`, { label:`score:${d.key}`, phase:'Score', schema:SCORE_SCHEMA, effort:'high' }),
  (s, d) => {
    if (!s) return null
    return agent(`${CTX}\n\n役割: 次元「${d.name}」の対称 verify。judge の採点 ${s.score} (anchor ${d.anchor}) を**両方向から**攻撃せよ:\n- over 方向: score / 回収判定 / defect が過大でないか。証跡を command 再現して崩す\n- under 方向: **proven な前進を見落としていないか** (= transcript / gh に証跡があるのに未計上、繰延にした項目に実は本番発火痕跡がある、defect の severity が過大)。過去評価は過小方向の検査を一度も持たなかった — ここが本 run の新設検査\njudge 出力:\n${JSON.stringify(s)}\n\n全 defect と全 settlement 判定に verdict を付けよ (= severity low も対象)。scoreChallenge には「この score が誤りだとすればどちら向きで、決定的な証跡は何か」を書け。`, { label:`verify:${d.key}`, phase:'Verify', schema:VERIFY_SCHEMA, effort:'high' }).then(v => ({ judge:s, verify:v, dim:d.key, anchor:d.anchor }))
  }
)

phase('Vector')
const jd = JSON.stringify(judged.filter(Boolean))
const VEC_SCHEMA = { type:'object', required:['vector','per_dim_rationale','top_defects','settlements_summary','next_keys'], properties:{ vector:{type:'object',required:['context','routing','eval','outerloop','process','platform'],properties:{context:{type:'integer'},routing:{type:'integer'},eval:{type:'integer'},outerloop:{type:'integer'},process:{type:'integer'},platform:{type:'integer'}}}, per_dim_rationale:{type:'string'}, top_defects:{type:'array',maxItems:8,items:{type:'object',required:['title','severity','dim'],properties:{title:{type:'string'},severity:{type:'string'},dim:{type:'string'},roadmap:{type:'string'}}}}, settlements_summary:{type:'string'}, next_keys:{type:'array',maxItems:3,items:{type:'string'}} } }

const [vecA, vecB] = await parallel([
  () => agent(`${CTX}\n\n役割: 最終 vector 判断 A (= 独立 2 判断の 1 人目)。judge + verify の全結果から、6 次元の最終 vector を確定せよ。verify の REFUTED は採用しない。over / under 両方向の verdict を反映せよ (= under CONFIRMED は加点方向に効き得る)。台帳決算の総括と、確定 defect の severity 順 top、次に効く鍵 (最大 3、そのうち 1 行に理由) も。\n${jd}`, { label:'vector:A', phase:'Vector', schema:VEC_SCHEMA, effort:'high' }),
  () => agent(`${CTX}\n\n役割: 最終 vector 判断 B (= 独立 2 判断の 2 人目)。A とは独立に、judge + verify の全結果から 6 次元の最終 vector を確定せよ。判定規律は同じ (= REFUTED 不採用、over / under 両反映)。証跡の解釈が分かれる箇所では自分の判断根拠を明示せよ。\n${jd}`, { label:'vector:B', phase:'Vector', schema:VEC_SCHEMA, effort:'high' }),
])

const reconcile = await agent(`${CTX}\n\n役割: 独立 2 判断の突合。vector A と B を次元ごとに比較し、一致次元はそのまま確定、不一致次元は両者の根拠を judge/verify の証跡に照らして裁定せよ (= どちらが証跡に忠実か。折衷でなく裁定)。裁定不能なら split として両論併記。\nA: ${JSON.stringify(vecA)}\nB: ${JSON.stringify(vecB)}\n元データ: ${jd}`, { label:'reconcile', phase:'Vector', schema:{ type:'object', required:['final_vector','agreements','disputes','final_defects','final_settlements','next_keys'], properties:{ final_vector:{type:'string'}, agreements:{type:'string'}, disputes:{type:'array',items:{type:'object',required:['dim','a','b','ruling','reason'],properties:{dim:{type:'string'},a:{type:'integer'},b:{type:'integer'},ruling:{type:'string'},reason:{type:'string'}}}}, final_defects:{type:'array',maxItems:10,items:{type:'object',required:['title','severity','dim','roadmap'],properties:{title:{type:'string'},severity:{type:'string'},dim:{type:'string'},roadmap:{type:'string'}}}}, final_settlements:{type:'string'}, next_keys:{type:'array',maxItems:3,items:{type:'string'}} } }, effort:'high' })

phase('Critique')
const critique = await agent(`${CTX}\n\n役割: 盲点批評 (= 出力は §16 に必ず収載され消費される)。本 run の全結果:\nreconcile: ${JSON.stringify(reconcile)}\nプローブ: ${probeDigest}\n\n(1) blindSpots: 本 run がカバーしなかった領域 (= 具体的に、次 run で probe 化できる粒度で)\n(2) dimension_set_review: 6 次元という枠は run 1 から固定 — 今の harness に対して欠けている次元・統合すべき次元はあるか\n(3) method_feedback: メタ評価提案の適用 (= 脱結論化 CTX / 機械台帳 / 対称 verify / 2 判断制) は実際に機能したか、形骸化した箇所はどこか\n(4) 14 日無人運用の自然実験から得られた、評価が今まで測ってこなかった signal は何か`, { label:'critique', phase:'Critique', schema:{ type:'object', required:['blindSpots','dimension_set_review','method_feedback','new_signals'], properties:{ blindSpots:{type:'array',maxItems:6,items:{type:'string'}}, dimension_set_review:{type:'string'}, method_feedback:{type:'string'}, new_signals:{type:'array',maxItems:5,items:{type:'string'}} } }, effort:'high' })

return { ledger, probes: probes.filter(Boolean).map(p=>({area:p.area,summary:p.summary,anomalies:p.anomalies})), judged: judged.filter(Boolean).map(x=>({dim:x.dim,score:x.judge.score,anchor:x.anchor,settlement:x.judge.ledger_settlement,defects:x.judge.defects,uncredited:x.judge.uncredited_progress,verify:x.verify})), vecA, vecB, reconcile, critique }