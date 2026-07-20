export const meta = {
  name: 'harness-eval-meta-evaluation',
  description: 'Meta-evaluate the 7-run harness evaluation methodology (H1-H5): verify effectiveness, anchor-lock, landed/exercised discipline, meta-cost, blind spots',
  phases: [
    { title: 'Extract', detail: 'structure the eval record + audit preserved workflow scripts' },
    { title: 'Reverify', detail: 're-verify sampled confirmed defects in real repos' },
    { title: 'Judge', detail: '5 hypothesis judges' },
    { title: 'Refute', detail: 'adversarial refutation, no protected classes' },
    { title: 'Synthesize', detail: 'memo-ready content' },
  ],
}

const H = 'C:/Users/hiroki/code/harness'
const EVAL_DOC = H + '/docs/wip/harness-evaluation-2026-07-02.md'
const COST_DOC = H + '/docs/wip/cost-accounting-2026-07-03.md'
const TEST_STRAT = H + '/docs/wip/test-strategy-2026-07-02.md'
const WF_SCRIPTS = [
  'C:/Users/hiroki/.claude/projects/C--Users-hiroki-code-harness/1a85a600-0c5c-44b8-b00e-12c0b61f5ac6/workflows/scripts/harness-reeval-4-wf_8da65798-3e4.js',
  'C:/Users/hiroki/.claude/projects/C--Users-hiroki-code-harness/1a85a600-0c5c-44b8-b00e-12c0b61f5ac6/workflows/scripts/harness-reeval-6-wf_0940a19b-af3.js',
  'C:/Users/hiroki/.claude/projects/C--Users-hiroki-code-harness/0b7eb511-9440-427a-8dd4-ec05273fc62c/workflows/scripts/harness-fifth-evaluation-wf_20acedac-bfb.js',
  'C:/Users/hiroki/.claude/projects/C--Users-hiroki-code-harness/41511280-7ba4-406d-a7eb-f2775024c0d2/workflows/scripts/harness-eval-2026-07-06-wf_41bd0224-2e6.js',
]

const CTX = `## メタ評価 (2026-07-20)
評価対象は harness そのものではなく、**2026-07-02〜07-06 に 7 回実施されたハーネス評価プロセス自体**。
記録: ${EVAL_DOC} (§1-§15、7 run 分)。過去評価の workflow script 4 本が保存されている (run 1-3 の script は消失、main transcript も retention で全消失):
${WF_SCRIPTS.map((p,i)=>`- script${i+1}: ${p}`).join('\n')}

検証する仮説:
- H1: 敵対的検証 (verify) は judge の過大評価を実際に削っているか、それとも追認儀式か
- H2: anchor-lock — prior score の prompt 埋め込みと Lead の結論事前注入が採点を歪めていないか
- H3: landed vs exercised の区別は加点を実際に止めたか、先送り装置になっていないか
- H4: 評価の meta コスト対効果 (7 run のコスト vs 生んだ確定 defect / roadmap の価値)
- H5: 構造的盲点 — なぜ security 盲点 (§8.1) が 7 run 生き残ったか、same-model 評価の限界、方法論 drift (run 7 でスコア消滅)

作法:
- read-only (file write 禁止 / gh mutation 禁止)。repo: ${H}, C:/Users/hiroki/code/backlog, C:/Users/hiroki/code/dotconfig。deployed: ~/.claude。
- 「主張」でなく「証跡」。引用は file:line か doc の §番号で。
- **保護クラスなし**: 過去評価が「settled / 覆さない」とした設計判断も、それが評価の歪みを生んだ可能性がある限り検討対象。ただし設計の再交渉ではなく「評価方法への影響」の観点に限る。
- 過去評価は自己批判的で、多くの限界を自認済み (§10/§12.3/§15.7)。自認済みの限界の再発見は低価値。「自認と実態のズレ」と「未自認の欠陥」が高価値。
- 出力の文章は日本語 (field 名は英語のまま)。`

const LEDGER_SCHEMA = { type:'object', required:['defects'], properties:{ defects:{ type:'array', maxItems:20, items:{ type:'object', required:['id','run','section','claim','status_claimed','how_to_verify','reverify_value'], properties:{ id:{type:'string'}, run:{type:'integer'}, section:{type:'string'}, claim:{type:'string'}, status_claimed:{type:'string',enum:['解消','部分解消','残存','未対応']}, files:{type:'string'}, how_to_verify:{type:'string'}, reverify_value:{type:'string',enum:['high','medium','low']} } } } } }

const STRUCT_SCHEMA = { type:'object', required:['runs','verify_events','rule_changes','summary'], properties:{
  runs:{type:'array',items:{type:'object',required:['run','date','agents_reported','scores'],properties:{run:{type:'integer'},date:{type:'string'},agents_reported:{type:'string'},scores:{type:'string'},key_claims:{type:'string'}}}},
  verify_events:{type:'array',items:{type:'object',required:['run','what','outcome'],properties:{run:{type:'integer'},what:{type:'string'},outcome:{type:'string',enum:['棄却','修正','追認','反証が judge 提案を止めた']},substance:{type:'string'}}}},
  rule_changes:{type:'array',items:{type:'object',required:['run','change'],properties:{run:{type:'integer'},change:{type:'string'},comparability_impact:{type:'string'}}}},
  roadmap_fate:{type:'string'}, summary:{type:'string'} } }

const AUDIT_SCHEMA = { type:'object', required:['per_script','cross_run_findings','summary'], properties:{
  per_script:{type:'array',items:{type:'object',required:['script','which_run','key_structures'],properties:{script:{type:'string'},which_run:{type:'string'},key_structures:{type:'string'}}}},
  cross_run_findings:{type:'array',items:{type:'object',required:['title','evidence','quote'],properties:{title:{type:'string'},evidence:{type:'string'},quote:{type:'string'}}}},
  summary:{type:'string'} } }

phase('Extract')
const [structure, ledger, audit] = await parallel([
  () => agent(`${CTX}\n\n役割: 評価記録の構造抽出。${EVAL_DOC} を精読し、次を構造化せよ:\n1. runs: 各 run の日付 / 自己申告 agent 数 / スコア vector (run 7 はスコア無しならその旨) / 主要主張\n2. verify_events: 敵対的検証が judge の推奨・採点を「棄却/修正/追認/反証が judge 提案を止めた」した事例を全て列挙 (§7 / §11 / §12 / §14.2 / §15.4 等)。棄却が実質的 (結論の反転) か表面的 (言い換え) かを substance に\n3. rule_changes: 採点規則の run 間変更 (例: run 3 の landed-only 化、run 4 の exercised/merged 分離、run 7 のスコア廃止)。スコア推移の比較可能性への影響\n4. roadmap_fate: run 1 の改善案 21 件 (§9) のうち後続 run で landed が確認されたものの割合の概算\n必要なら ${TEST_STRAT} も参照。`, { label:'extract:structure', phase:'Extract', schema:STRUCT_SCHEMA }),
  () => agent(`${CTX}\n\n役割: confirmed defect 台帳の抽出。${EVAL_DOC} から「敵対的検証済み / confirmed / valid」とされた defect を最大 20 件抽出せよ。各 defect に:\n- run: 初出 run 番号、section: §番号\n- claim: 当時の主張 (1-2 文)\n- status_claimed: 記録上の最終ステータス (後続 run で「解消」宣言されたか、残存か)\n- files: 関係ファイル、how_to_verify: 今日の実 repo でこの主張と解消宣言を再検証する具体手順 (grep / git log / gh コマンド)\n- reverify_value: 再検証の価値。high = 解消宣言があるが実機依存 / 過去に誤宣言歴 (§3.6 は RESOLVED 誤宣言の前科あり) / severity が高い。low = 自明・doc のみ\nrun をまたいで分散させること (run 1 の defect だけに偏らない)。`, { label:'extract:ledger', phase:'Extract', schema:LEDGER_SCHEMA }),
  () => agent(`${CTX}\n\n役割: 過去評価 workflow script の監査。保存された 4 script を全て Read し、評価の実装がレポートの主張と一致するか監査せよ。特に:\n1. 各 script がどの run に対応するか (レポートの日付・agent 数と突合)\n2. judge prompt の anchor 構造: prior score の埋め込み方、上げ下げの非対称な priming (「甘い採点は user の意図に反する」等)、Lead が結論を prompt に事前注入した箇所 (「この fix は exercised 済み — 上げてよい」型)、スコア移動の方向指示\n3. verify の実装: 対象範囲 (全 defect か high/critical のみか、run 間で違うか)、default 姿勢 (懐疑か追認か)、保護クラス (「設計意図を defect と誤認するな」型の棄却誘導)\n4. Evidence probe の既知 defect への偏り (「既知の事実: …」で seed された probe の割合 vs 自由探索)\n5. レポートに書かれていない実装上の特徴 (agentType / effort / model の使い分け、finding の severity 別の扱い)\n各 finding に script 名と直接引用 (quote) を付けよ。`, { label:'audit:scripts', phase:'Extract', schema:AUDIT_SCHEMA }),
])

if (!ledger || !structure || !audit) { log('extract 失敗あり — 継続するが欠損に注意') }

phase('Reverify')
const all = (ledger && ledger.defects) ? ledger.defects : []
const ranked = [...all].sort((a,b)=>({high:0,medium:1,low:2}[a.reverify_value]-{high:0,medium:1,low:2}[b.reverify_value]))
const byRun = {}
for (const d of ranked) { (byRun[d.run] = byRun[d.run] || []).push(d) }
const runKeys = Object.keys(byRun)
const sample = []
let ri = 0
while (sample.length < 6 && runKeys.some(k=>byRun[k].length)) {
  const k = runKeys[ri % runKeys.length]
  if (byRun[k].length) sample.push(byRun[k].shift())
  ri++
}
log(`reverify 対象 ${sample.length} 件 (台帳 ${all.length} 件から run 分散で抽出)`)

const REV_SCHEMA = { type:'object', required:['defect_id','claim_was_real','resolution_claim_accurate','evidence'], properties:{ defect_id:{type:'string'}, claim_was_real:{type:'string',enum:['yes','no','unclear']}, resolution_claim_accurate:{type:'string',enum:['yes','no','partial','n/a']}, evidence:{type:'string'}, notes:{type:'string'} } }

const reverified = (await parallel(sample.map(d => () =>
  agent(`${CTX}\n\n役割: 過去 confirmed defect の再検証者。以下の defect について 2 点を今日の実 repo で独立検証せよ:\n(a) claim_was_real: 評価時点 (run ${d.run}, 2026-07-0X) でこの主張は事実だったか。git log / git show <当時のsha>:<path> で当時の状態を確認\n(b) resolution_claim_accurate: 記録上のステータス「${d.status_claimed}」は今日の実態と一致するか\n\ndefect ${d.id} (§${d.section}):\nclaim: ${d.claim}\nfiles: ${d.files || 'N/A'}\n検証手順の示唆: ${d.how_to_verify}\n\n判定は証跡付きで。「レポートがそう書いている」は証跡でない — 実 repo / git history / 実コマンドの出力のみが証跡。`, { label:`reverify:${d.id}`, phase:'Reverify', schema:REV_SCHEMA })
))).filter(Boolean)

phase('Judge')
const digest = JSON.stringify({ structure, audit, reverified })
const JUDGE_SCHEMA = { type:'object', required:['hypothesis','verdict_summary','findings'], properties:{ hypothesis:{type:'string'}, verdict_summary:{type:'string'}, findings:{type:'array',maxItems:8,items:{type:'object',required:['title','assessment','evidence','confidence'],properties:{title:{type:'string'},assessment:{type:'string'},evidence:{type:'string'},confidence:{type:'string',enum:['high','medium','low']}}}}, recommendations:{type:'array',maxItems:5,items:{type:'string'}} } }

const HYPOTHESES = [
  { key:'H1-verify', prompt:`仮説 H1: 敵対的検証は judge の過大評価を実際に削っているか。\n判定材料: verify_events の棄却/追認比率と棄却の実質性、script 監査の verify 実装 (対象範囲の run 間差 / 保護クラス / default 姿勢)、reverify の結果 (過去の confirmed が今日も追認できるか = verify の精度の ground truth)。\n特に: (1) verify が Lead 提案を止めた実例 (§14.2 eval 3→4 反証) と、保護クラスによる棄却誘導の両面を秤にかけよ。(2) run 7 で verify 対象が high/critical のみに絞られ medium/low が無検証でレポートに載る構造の影響。(3) reverify で解消宣言の誤りが見つかれば、それは verify でなく「解消判定」の欠陥 — どちらの工程の欠陥かを区別せよ。` },
  { key:'H2-anchor', prompt:`仮説 H2: anchor-lock — prior score の埋め込みと Lead の結論事前注入が採点を歪めているか。\n判定材料: script 監査の anchor 構造 (prev score 埋め込み / 「甘い採点は user の意図に反する」型 priming / run 6 の「この fix は exercised 済み、上げてよい」型注入 / スコア移動の方向指示)、スコア推移 (7 run 中の据え置き率)、latent defect (agents junction、06-29 発生) の発見遅延 (2 run 見逃し)。\n特に: (1) anchor は noise 抑制 (毎回ゼロから採点すると振れる) と lock-in の trade-off — どちらに倒れているかを推移データで判定。(2) Lead 注入があっても verify が反証で止めた事例がある — 注入の実害は何件で顕在化したか。(3) 評価の独立性: 評価 workflow を書く Lead 自身が改善実装者でもある構造 (self-grading) の影響。` },
  { key:'H3-exercised', prompt:`仮説 H3: landed vs exercised の区別は加点を実際に止めたか、先送り装置か。\n判定材料: structure の rule_changes (run 3 で landed-only、run 4 で exercised/merged 分離)、加点保留の実例 (§13.2 / §15.3) と昇格の実例 (§14.2 platform 4→5)、「予約された上げ幅」概念 (§13.5)。\n特に: (1) 加点保留された項目が後続 run で exercised 昇格した率 — 先送りが回収されているか無限に積もるか。(2) 規則が run 途中で変わったことでスコア推移の解釈が壊れていないか (run 3 の「strict 化で下がった」は harness の悪化でなく規則変更)。(3) exercised の判定自体の質 — 「自コマンド再現」は本番発火と等価でない (§15.3 が自認)。` },
  { key:'H4-cost', prompt:`仮説 H4: 評価の meta コスト対効果。\n判定材料: ${COST_DOC} の単価 / 自己申告 agent 数 (run 1: 25 agents 195万 output token、run 2-4: 各 19、run 5: 36、run 6: 18、run 7: 小規模)、structure の roadmap_fate (run 1 の 21 案の landed 率)。\n特に: (1) 7 run 分の概算コスト (token 自己申告 × list price、opus 系前提) を幅付きで見積もれ。(2) 生んだ価値の側: 確定 defect のうち「評価がなければ発見されなかった」ものと「通常運用でもいずれ顕在化した」ものを分けよ (agents junction は delegate 不発で気づく類か?)。(3) 3 日で 6 run の頻度は情報利得逓減に対して過剰でなかったか (run 3→4 は同日 2 回)。(4) 評価プロセス自身の transcript が retention で消え、meta コストが事後測定不能になった事実 — 評価は自分の証跡保持規律 (evidence-first) を自分に適用していない。gh で backlog の Epic #80 / #106 を read-only 確認してもよい。` },
  { key:'H5-blindspot', prompt:`仮説 H5: 評価手法の構造的盲点。\n判定材料: §8.1 security 盲点が run 1 で指摘され run 7 まで「誰も grade しない」まま残った事実、script 監査の probe 偏り (既知 defect 再確認 vs 自由探索)、run 7 の方法論転換 (6 次元スコア廃止 → 5 assess 次元、推移の比較可能性切断)、same-model 問題 (評価者も被評価者も同 model 系列)。\n特に: (1) 盲点が「次元の定義」に由来するか「probe の seed」に由来するかを script から判定。(2) 6 次元という枠自体が run 1 で固定され、以後の run が枠の外を探さない構造 — 次元追加の検討がされた形跡はあるか。(3) 評価 doc 自身が次回評価の prompt に入る自己参照構造 (評価が評価を anchor する) の累積効果。(4) 過去評価が自認していない盲点を最低 1 つ新規に挙げよ (自認済みリスト: §10 / §12.3 / §15.7)。` },
]

const judged = await pipeline(
  HYPOTHESES,
  h => agent(`${CTX}\n\n役割: メタ評価 judge。\n\n${h.prompt}\n\n以下は抽出・監査・再検証の結果 (一次証拠に基づく):\n${digest}\n\n必要なら自分でも Read / Grep / Bash で裏取りせよ。findings は「自認と実態のズレ」「未自認の欠陥」「実は健全だった点」を含み、confidence を正直に付けよ。健全性の追認も価値ある結論 — 欠陥の捏造はするな。`, { label:`judge:${h.key}`, phase:'Judge', schema:JUDGE_SCHEMA, effort:'high' }),
  (j, h) => {
    if (!j) return null
    return agent(`${CTX}\n\n役割: 敵対的反証者。以下のメタ評価 judge の findings を REFUTE しようと試みよ。default は懐疑。実 repo / script / doc を自分で確認し、各 finding が (a) 証跡に支えられているか (b) 過去評価が既に自認していた限界の再発見に過ぎないか (c) 因果が逆・別の説明が立つか、を検討せよ。保護クラスなし — ただし反証も証跡ベースで。\n\njudge (${h.key}) の出力:\n${JSON.stringify(j)}\n\n各 finding に sustained / weakened / refuted を付け、weakened / refuted は理由を具体的に。`, { label:`refute:${h.key}`, phase:'Refute', schema:{ type:'object', required:['hypothesis','verdicts'], properties:{ hypothesis:{type:'string'}, verdicts:{type:'array',items:{type:'object',required:['title','verdict','reasoning'],properties:{title:{type:'string'},verdict:{type:'string',enum:['sustained','weakened','refuted']},reasoning:{type:'string'}}}}, overall_note:{type:'string'} } } }).then(r => ({ judge:j, refutation:r }))
  }
)

phase('Synthesize')
const surviving = judged.filter(Boolean)
const synthesis = await agent(`${CTX}\n\n役割: メタ評価の統合。以下の 5 仮説の judge 出力と敵対的反証を統合し、docs/wip 向けメモの内容を構造化せよ (file write はしない、内容を返すのみ)。\n\n${JSON.stringify(surviving)}\n\nreverify 結果:\n${JSON.stringify(reverified)}\n\n構成:\n1. TL;DR (5 行以内): 7 run の評価プロセスは信頼に足るか、最大の歪みは何か、最も健全だった機構は何か\n2. 各仮説 (H1-H5) の結論: verdict + 生き残った finding のみ (refuted は除外、weakened は明記)。証跡付き\n3. reverify 決算表: 6 件の再検証結果 (過去の confirmed / 解消宣言の精度)\n4. 評価手法への改善提案: user の 4 分類 (minimum-guardrail / common-standard / team-discretion / personal-experiment) で。評価プロセスへの提案であり harness 本体への提案ではない。「次回評価をどう変えるか」が中心。過剰な process 追加を戒める user のバイアス自覚と整合させよ (提案が新たな ceremony にならないこと)\n5. このメタ評価自身の限界 (same-model / read-only / メタのメタは省く、等)\n日本語で。主張と証跡を分離。`, { label:'synthesis', phase:'Synthesize', effort:'high' })

return { structure, audit_summary: audit ? audit.summary : null, reverified, judged: surviving.map(x => ({ hypothesis: x.judge.hypothesis, verdict: x.judge.verdict_summary, verdicts: x.refutation ? x.refutation.verdicts : null })), synthesis }