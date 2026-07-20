export const meta = {
  name: 'harness-eval-2026-07-06',
  description: 'Periodic harness evaluation: verify defects across dimensions, adversarially confirm, produce roadmap verdict',
  phases: [
    { title: 'Assess' },
    { title: 'Verify' },
    { title: 'Roadmap' },
  ],
}

const HARNESS = 'C:\\Users\\hiroki\\code\\harness'
const BACKLOG = 'C:\\Users\\hiroki\\code\\backlog'
const DOTCONFIG = 'C:\\Users\\hiroki\\code\\dotconfig'

const CONTEXT = `
## harness 定期評価 (2026-07-06、第7回相当)
AI 開発ハーネス (個人開発、Claude Code + backlog GitHub Projects v2 で自律運用) の read-only 評価。
main HEAD: 146268d。6 universal skill (task-routing/intent-clarify/task-slicing/wave-status/finish-task/commit-message)、6 agent (architect/fullstack-engineer/qa-expert/performance-engineer/security-auditor/technical-writer)。
cron 7個: issue-picking-heartbeat / completion-check-routine / done-close-routine (今回新設) / memory系4 / user-profile-sync。
boundary skill (backlog repo): issue-execute / issue-from-idea / prepare-uat。

## この評価サイクルで入った変更 (重点検証対象)
- #127: issue-execute に product→repo 解決 (Issue操作=backlog固定 / コード操作=着地repo)。cross-repo branch は gh --branch-repo。
- #129: issue-execute を git worktree ベース化 (~/code/.worktrees/<repo>/<N>)。--name 決定論命名 + stdout 捕捉。同一 repo 同時着地の衝突解消。
- #122: done-close-routine 新設 (Done→gh close 自動化 + #129 の worktree cleanup 兼任、cygpath -u で C:/→/c/ 統一の安全弁)。
- #119: eval-regression の comparator を trigger 契約まで拡張 (trigger 反転が検出されない穴を塞いだ)。

## 前回評価 (2026-07 まで) の5大 defect
agent 名 drift / YAML # 切断 / eval 非実行 / Done≠merged / needs-fix 不在。
評価履歴は docs/wip/harness-evaluation-2026-07-02.md (第6回まで)。

## 評価の作法
- read-only。実ファイル / grep / 実コマンドで裏取り。「主張」でなく「証跡」。
- score theater 禁止 (= スコアを上げるための人為的お膳立てをしない、自然に動いた証跡のみ主張)。
- 実装状態を implemented / prompt-text-only / not-built で分類 (前回の多層防御表と同じ語彙)。
`

const DIMENSIONS = [
  {
    key: 'prior-defects',
    prompt: `${CONTEXT}\n\n評価次元: **前回5大 defect の解消状況**。\n${HARNESS} と ${BACKLOG}, ${DOTCONFIG} を読み、前回評価の5 defect それぞれが今も残るか / 解消したかを実ファイルで確認せよ:\n1. agent 名 drift (skill が参照する agent 名と実 agents/*.md の乖離) — lint-agent-refs.py の有無と実行結果\n2. YAML # 切断 (description 内の # がコメント扱いで切れる) — check-frontmatter-yaml.py の有無\n3. eval 非実行 (eval が skill 本文を実行せず fixture-sync のみ) — L2 behavioral の有無、#119 で comparator は直ったか\n4. Done≠merged / Done≠closed — done-close-routine (#122) が本当に close するか、board と gh state の乖離が残るか\n5. needs-fix 不在 (差し戻しラベルが使われていない) — needs-fix / bounce プロトコルの配線\n各 defect に状態 (解消 / 部分解消 / 未解消 / 悪化) + 実ファイル証跡を付けよ。`,
  },
  {
    key: 'new-changes',
    prompt: `${CONTEXT}\n\n評価次元: **今回の変更 (#127/#129/#122/#119) の実効性と副作用**。\n実ファイル + 実コマンドで検証せよ:\n- issue-execute (${BACKLOG}/skills/issue-execute/SKILL.md): product→repo 解決、worktree 化、--name 決定論、cwd 伝播注意が一貫して破綻なく書かれているか\n- done-close-routine (${DOTCONFIG}/dot_claude/scheduled-tasks/done-close-routine/SKILL.md): Done→close + worktree cleanup の安全弁 (cygpath) が正しいか\n- これら4変更が互いに矛盾しないか (例: worktree path 規約が issue-execute / done-close / heartbeat / harness §10 §13 で一致するか)\n- 過渡期の穴: #129 前の旧 Issue (main clone 記録) と #129 後 (.worktrees 記録) の混在で cleanup / heartbeat が誤動作しないか\n- installed skill (~/.claude/skills/issue-execute) が最新か (sync drift)\n具体的な破綻・不整合を file:section で。実際に grep / diff して確認せよ。`,
  },
  {
    key: 'defense-stack',
    prompt: `${CONTEXT}\n\n評価次元: **多層防御スタックの実装状態** (前回の §3 表を再検証)。\n${HARNESS}/docs/harness-design.md §3 の12層防御表を読み、各層が implemented / prompt-text-only / not-built のどれか実ファイルで再分類せよ。特に:\n- Back pressure (test green まで前進不可) の gate は実在するか、prompt-text-only か\n- Out-of-process supervisor / Watchdog / Circuit breaker の実体\n- 今回 done-close が増えたことで防御層に変化があるか\n前回「implemented は12層中2層のみ」だったが、今回の変更で増減したか。score theater を避け、実装がある層だけ implemented と主張せよ。`,
  },
  {
    key: 'ops-autonomy',
    prompt: `${CONTEXT}\n\n評価次元: **自律運用の健全性**。\n${DOTCONFIG}/dot_claude/scheduled-tasks/ の cron chain を読み、end-to-end で矛盾なく回るか検証せよ:\n- heartbeat (pick) → issue-execute (着手) → 実装 → prepare-uat (UAT投入) → completion-check (screening) → done-close (close+cleanup) の chain が繋がっているか\n- 今回 done-close が増えて cron が7個。位相 (heartbeat */15 / completion-check 7-59/15 / done-close 3-59/15) が衝突しないか\n- WIP 上限 / race detection (running ラベル) / worktree 直列化が整合するか\n- 自律運用の cost 会計 (#113) / DRY_RUN 切替基準 (#109) など運用基準の未確定項目\n- prompt injection 対策 (§0 Untrusted content) が全 cron に配線されているか\n実際に SKILL.md を読んで chain の切れ目・矛盾を挙げよ。`,
  },
  {
    key: 'board-hygiene',
    prompt: `${CONTEXT}\n\n評価次元: **board / Issue lifecycle の一貫性** (実データ)。\n実際に gh コマンドで backlog board (project #1) の現状を取得し検証せよ:\n- board 各列 (Inbox/Ready/Epic/In Progress/Completion Check/Awaiting UAT/Done) の件数と、state (OPEN/CLOSED) の乖離が残るか (--limit 300 で全件、default paging の取りこぼしに注意)\n- Done かつ OPEN の乖離が今もあるか (done-close 導入後)\n- In Progress の滞留 (long-running / stuck)\n- Ready の harness Issue (#120-126) が自走 pick 可能な状態か (needs-human が残っていないか)\n- running ラベルの残留 (session 死亡後の孤児ロック)\ngh project item-list / gh issue list を実際に走らせて実データで報告せよ。`,
  },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['critical','high','medium','low'] },
          title: { type: 'string' },
          evidence: { type: 'string' },
          file: { type: 'string' },
          status_vs_prior: { type: 'string', enum: ['new','unchanged','improved','regressed','resolved'] },
        },
        required: ['severity','title','evidence'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['dimension','findings','summary'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: { confirmed: {type:'boolean'}, confidence: {type:'string',enum:['high','medium','low']}, reasoning: {type:'string'} },
  required: ['confirmed','confidence','reasoning'],
}

// Assess → Verify: pipeline, each dimension's findings verify as its assessment lands
const results = await pipeline(
  DIMENSIONS,
  (d) => agent(d.prompt, { label: `assess:${d.key}`, phase: 'Assess', schema: FINDINGS_SCHEMA, agentType: 'qa-expert' }),
  (assessment, d) => {
    const findings = (assessment.findings || []).filter(f => f.severity === 'critical' || f.severity === 'high')
    if (!findings.length) return { dim: d.key, assessment, verified: [] }
    return parallel(findings.map(f => () =>
      agent(
        `${CONTEXT}\n\n以下の評価 finding を敵対的に検証せよ。実ファイル / grep / 実コマンドで裏取りし、本当に defect が存在するか confirm/refute せよ。score theater (お膳立て) を疑い、「仕様上そう書いてある」だけでなく「実際に破綻するか」を見よ。デフォルトは疑い (confirmed=false 寄り)、実運用で実害があるなら confirmed=true。\n\nfinding (${d.key}, ${f.severity}):\n- title: ${f.title}\n- evidence: ${f.evidence}\n- file: ${f.file || 'N/A'}\n- 前回比: ${f.status_vs_prior || 'N/A'}`,
        { label: `verify:${d.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }
      ).then(v => ({ ...f, dim: d.key, verdict: v }))
    )).then(verified => ({ dim: d.key, assessment, verified: verified.filter(Boolean) }))
  }
)

phase('Roadmap')
const flat = results.filter(Boolean)
const allFindings = flat.flatMap(r => (r.assessment?.findings || []).map(f => ({ ...f, dim: r.dim })))
const confirmedHigh = flat.flatMap(r => (r.verified || []).filter(v => v.verdict?.confirmed && v.verdict?.confidence !== 'low'))
const dimSummaries = flat.map(r => ({ dim: r.dim, summary: r.assessment?.summary }))

// Roadmap synthesis from confirmed findings
const roadmap = await agent(
  `${CONTEXT}\n\n以下は各次元の評価と、敵対的検証で confirmed された high/critical finding。これを元に roadmap 判定を出せ。\n\n次元サマリ:\n${JSON.stringify(dimSummaries, null, 2)}\n\nconfirmed high/critical findings:\n${JSON.stringify(confirmedHigh.map(f => ({dim:f.dim, severity:f.severity, title:f.title, evidence:f.evidence, reasoning:f.verdict.reasoning})), null, 2)}\n\n全 findings (参考、severity 別):\n${JSON.stringify(allFindings.map(f => ({dim:f.dim, sev:f.severity, title:f.title, status:f.status_vs_prior})), null, 2)}\n\n出力: (1) 前回5大 defect の総括 (解消/残存)、(2) 今回サイクルの品質評価 (#127/#129/#122/#119 は健全か)、(3) confirmed defect を優先度順に並べ、各に「即対応/spike先行/様子見/落とす」の roadmap 判定 + 根拠、(4) 全体所見 (harness は自律運用に耐えるか、次に効く1手は何か)。score theater を避け、証跡ベースで。`,
  { label: 'roadmap', phase: 'Roadmap', schema: {
    type: 'object',
    properties: {
      prior_defects_status: { type: 'string' },
      cycle_quality: { type: 'string' },
      confirmed_defects: { type: 'array', items: { type: 'object', properties: {
        title:{type:'string'}, severity:{type:'string'}, roadmap:{type:'string',enum:['即対応','spike先行','様子見','落とす']}, rationale:{type:'string'},
      }, required:['title','severity','roadmap','rationale'] } },
      overall: { type: 'string' },
      next_best_action: { type: 'string' },
    },
    required: ['prior_defects_status','cycle_quality','confirmed_defects','overall','next_best_action'],
  }}
)

return {
  dimensionSummaries: dimSummaries,
  confirmedHighCount: confirmedHigh.length,
  totalFindings: allFindings.length,
  findingsBySeverity: {
    critical: allFindings.filter(f=>f.severity==='critical').length,
    high: allFindings.filter(f=>f.severity==='high').length,
    medium: allFindings.filter(f=>f.severity==='medium').length,
    low: allFindings.filter(f=>f.severity==='low').length,
  },
  roadmap,
}
