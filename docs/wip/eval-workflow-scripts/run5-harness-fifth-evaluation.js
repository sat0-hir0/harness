export const meta = {
  name: 'harness-fifth-evaluation',
  description: 'harness リポの第5回多角評価: 6次元採点 + 外部比較 + 敵対的検証 + 改善案',
  phases: [
    { title: 'Evidence', detail: '一次証跡の深掘り(CI/eval/agent copy-mode/skill精読)' },
    { title: 'Score', detail: '6次元を独立 reader が証跡ベースで採点' },
    { title: 'External', detail: '外部ハーネス実装との相対比較(Web調査)' },
    { title: 'Verify', detail: '各次元 finding を独立 skeptic が反証' },
    { title: 'Synthesize', detail: '検証済み finding + 改善案を4分類で統合' },
  ],
}

const REPO = 'C:/Users/hiroki/code/harness'

// --- schemas ---
const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    score: { type: 'integer', minimum: 1, maximum: 5 },
    prev_score: { type: 'integer', description: '第4回評価での点数(context4/routing4/eval3/outer3/process4/platform4)' },
    delta_reason: { type: 'string', description: '前回から変わった/変わらない理由' },
    evidence: { type: 'array', items: { type: 'string' }, description: 'file:line 付き証跡。実 repo 照合済みのみ' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          summary: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          file: { type: 'string' },
          evidence: { type: 'string', description: '具体的な失敗シナリオ or 実 repo での確認内容' },
        },
        required: ['summary', 'severity', 'evidence'],
      },
    },
    strengths: { type: 'array', items: { type: 'string' } },
  },
  required: ['dimension', 'score', 'evidence', 'defects'],
}

const EXTERNAL_SCHEMA = {
  type: 'object',
  properties: {
    comparison: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          external_impl: { type: 'string', description: '比較対象(例: Anthropic公式 agent SDK / OpenAI Swarm / LangGraph / claude-flow 等)' },
          what_they_do: { type: 'string' },
          harness_position: { type: 'string', enum: ['ahead', 'parity', 'behind', 'orthogonal'] },
          gap_or_lead: { type: 'string', description: 'このハーネスが勝る/劣る具体点' },
          source_url: { type: 'string' },
        },
        required: ['external_impl', 'what_they_do', 'harness_position', 'gap_or_lead'],
      },
    },
    net_assessment: { type: 'string', description: '相対位置の総括(near-frontier か / どこが独自か / どこが遅れか)' },
    adoptable_ideas: { type: 'array', items: { type: 'string' }, description: '外部から採り入れる価値のあるパターン' },
  },
  required: ['comparison', 'net_assessment'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['CONFIRMED', 'PLAUSIBLE', 'REFUTED'] },
    reasoning: { type: 'string' },
    corrected_severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'non-issue'] },
  },
  required: ['verdict', 'reasoning'],
}

// ============================================================
phase('Evidence')
log('Phase 1: 一次証跡の深掘り(CI RED原因 / eval L1-L2 / agent copy-mode / skill精読)')

const EVIDENCE_PROBES = [
  {
    key: 'ci-red',
    prompt: `harness リポ (${REPO}) の CI (.github/workflows/eval-gate.yml) について調査せよ。
既知の事実: main への push で future-plans lint step が BASE_REF 空により 'git diff origin/..HEAD' で exit 2 になり必ず失敗する。PR では base_ref が入るので通る。
確認すべきこと:
1. これが現時点(HEADのworkflow定義)でも未修正か。.github/workflows/eval-gate.yml を Read して該当 step の env と run を引用せよ。
2. push トリガの job で base_ref を使わない正しい書き方(例: git diff HEAD^ HEAD、または push では future-plans lint を skip)の候補を挙げよ。
3. scripts/check-future-plans.py が --base をどう使うか Read で確認し、push 時に成立する呼び出し形を特定せよ。
返すのは: 未修正か否か / 根本原因の1行 / 最小修正案。file:line で引用。`,
  },
  {
    key: 'eval-depth',
    prompt: `harness リポ (${REPO}) の eval 基盤を評価せよ。
2層ある: L1 (eval-run.py / eval-regression.py = 構造 snapshot diff、skill 未実行) と L2 (eval-behavioral.py = claude -p で skill を実 headless 実行し verdict を assert)。
確認すべきこと:
1. eval/scripts/*.py と scripts/eval-gate.py, eval/README.md を Read。
2. L2 は task-routing のみ対象か。他 skill (task-slicing/finish-task/intent-clarify/wave-status/commit-message) は L1 の構造 diff のみで挙動未検証か。
3. L2 は CI で走るか、それとも on-demand のみか(eval-gate.yml は --judge を渡さず deterministic のみ、と読める)。つまり「skill の実挙動を守る gate」が pre-push/CI に効いているか、それとも人手 on-demand 頼みか。
4. eval-gate.py の changed-file -> target マッピングを確認し、SKILL.md prose 変更が L1 の gate を素通りするか(前回 defect)を再確認。
返すのは: L2 のカバレッジ範囲 / gate に効いているか否か / 残る穴。file:line 引用。`,
  },
  {
    key: 'agent-copymode',
    prompt: `harness の deployed agents が Node から ENOENT になる問題(junction link-mode 不読)の現状を調査せよ。
既知: 修正は dotconfig の .chezmoiscripts/run_once_after_13-skillshare-sync.ps1.tmpl に agents を --mode copy で配置する対応。
確認すべきこと:
1. C:/Users/hiroki/code/dotconfig/.chezmoiscripts/run_once_after_13-skillshare-sync.ps1.tmpl を Read。skillshare が skills と agents をそれぞれどの mode (junction/copy) で配置するか特定せよ。特に 'extras scripts --mode copy' が agents 本体に適用されるのか、それとも別物(extras scripts)なのかを判別。
2. 実際に deployed agents が copy か junction か確認: C:/Users/hiroki/.claude/agents/ の中身が実ファイルか junction か (ls -la 相当) を Bash で確認。
3. junction のままなら Node fs (skill/agent loader) が読めるか読めないかを判定。
返すのは: 現状 copy か junction か / ENOENT が今も起きるか / 未解決なら残る修正箇所。`,
  },
  {
    key: 'skill-bloat',
    prompt: `harness リポ (${REPO}) の 6 skill を精読し、肥大と品質を評価せよ。
skills/task-slicing/SKILL.md (514行), finish-task (441), task-routing (346), commit-message (259), intent-clarify (237), wave-status (232) を Read。
重要な前提(memory 由来、覆さないこと): skill 間の重複(投稿フロー/同定フロー/無人禁止)は fresh-context-per-iteration 原則の帰結で「削れない」。doc 化・1skill集約は原則違反。圧縮上限は同skill内同文削除+短文化で10-15%。
確認すべきこと:
1. 各 skill が「単独で判断完結する」設計になっているか(fresh context 原則の遵守度)。
2. 同一 skill 内での同文2回掲載(削れる冗長)が残っているか。具体的な行番号ペアで。
3. description の YAML parse 安全性(unquoted #, 長さが render cap ~1535字を超えていないか)。
4. skill 間の SoT 矛盾(size 表など判定情報が2箇所で食い違っていないか)。
返すのは: 各 skill の設計品質 / 削れる冗長の具体箇所(行ペア) / 矛盾。原則違反の圧縮案は出さない。`,
  },
  {
    key: 'defense-stack',
    prompt: `harness の多層防御スタック(docs/harness-design.md §3)の実装状態の正直さを検証せよ。
§3 は12層中 implemented は2層(役割分離・UAT引き渡し)のみ、と自己申告している。
確認すべきこと:
1. docs/harness-design.md §3 を Read。各層の実装状態(implemented/prompt-text-only/not-built)の申告が実 repo と一致するか grep で裏取り。
2. 特に「層2 Back pressure = prompt-text-only」「層3 supervisor = prompt-text-only」の申告が正しいか。lefthook.yml / scripts/ / settings を確認し、test green まで前進を止める gate が本当に無いか。
3. この自己批判的な実装状態表は harness の強み(正直さ)か、それとも「実装が薄い」弱みか、両面で評価。
4. Completion Check routine(§13、性悪説 Checker)は実在する scheduled task か、doc 上の規約か。dotconfig の scheduled task 定義を確認。
返すのは: §3 申告の正確性 / 実際の防御実装数 / 正直さ vs 実装薄の両面評価。`,
  },
  {
    key: 'meta-recursion',
    prompt: `harness が「自分自身の開発に自分のハーネスを使えているか」(メタ再帰の健全性)を評価せよ。
確認すべきこと:
1. harness リポに CLAUDE.md はあるか(Read で確認、内側 skill が harness 自身の開発で発火するか)。
2. 現在の git 状態を Bash で確認: 第4回評価(§13)を含む docs/114-fourth-evaluation ブランチが main 未 merge か。評価レポート自体が Done≠merged 状態か。git log main..HEAD と HEAD..main。
3. harness 開発時に eval-gate(pre-push)が実際に効くか。lefthook install 前提が満たされているか。
4. 過去の評価で「改善が9 open PR + direct-push に滞留し main では逆に defect 露呈」という自己言及があった。現在の未 merge ブランチ数を git branch で数え、stale branch 累積を確認。
返すのは: harness 自身がハーネス doctrine(Done=merged, push=state on disk)を自分に適用できているか / 適用漏れの具体。`,
  },
]

const evidence = await parallel(
  EVIDENCE_PROBES.map(p => () =>
    agent(p.prompt, { label: `probe:${p.key}`, phase: 'Evidence', agentType: 'Explore' })
      .then(text => ({ key: p.key, findings: text }))
  )
).then(rs => rs.filter(Boolean))

const evidenceDigest = evidence.map(e => `### ${e.key}\n${e.findings}`).join('\n\n')

// ============================================================
phase('Score')
log('Phase 2: 6次元を証跡ベースで独立採点')

const DIMENSIONS = [
  { key: 'context', prev: 4, desc: 'context 管理 / fresh-context 原則の遵守 / skill が単独完結するか / 肥大コントロール' },
  { key: 'routing', prev: 4, desc: 'task-routing / intent-clarify の入口判定精度 / verdict 3-way の質 / L2 behavioral eval が routing を守れているか' },
  { key: 'eval', prev: 3, desc: 'eval 基盤の実効性 / L1構造diff + L2 behavioral のカバレッジ / gate が実挙動を守るか / rubber-stamp 訓練していないか' },
  { key: 'outer-loop', prev: 3, desc: '外側レイヤー(backlog boundary / Completion Check / heartbeat / needs-fix 差し戻し)の完成度 / 無人実行の完走規約' },
  { key: 'process-weight', prev: 4, desc: 'process の重さと実益のバランス / over-engineering していないか / 安全装置が実品質を上げているか(user の bias 自覚と整合するか)' },
  { key: 'platform', prev: 4, desc: '可搬性 / CI headless / plugin配布 / cross-vendor / deployed agent の健全性 / 単一Windows機依存の解消度' },
]

const scores = await parallel(
  DIMENSIONS.map(d => () =>
    agent(
      `あなたは AI 開発ハーネスの評価者。次元「${d.key}」(${d.desc})を 1-5 で採点せよ。
第4回評価(2026-07-03深夜)での点数は ${d.prev}。据え置き/上昇/下降を判定し理由を述べよ。

採点規律(harness 自身の doctrine を評価にも適用): main+deployed に landed した改善のみ加点。未 merge ブランチ / direct-push 滞留 / merged-but-unproven(本番未実走)は加点保留。exercised(自コマンド再現で実発火を確認した)もののみ上げる。

以下は一次証跡調査の結果(実 repo 照合済み)。これを踏まえて採点せよ。必要なら自分でも ${REPO} を Read/Bash して裏取りせよ:

${evidenceDigest}

厳格に。甘い採点は user の意図に反する(過去 evaluation は上昇頭打ちを正直に記録してきた)。defect は severity 付きで、実 repo で確認したもののみ挙げよ。`,
      { label: `score:${d.key}`, phase: 'Score', schema: SCORE_SCHEMA, effort: 'high' }
    ).then(s => ({ ...s, prev_score: s.prev_score ?? d.prev }))
  )
).then(rs => rs.filter(Boolean))

// ============================================================
phase('External')
log('Phase 3: 外部ハーネス実装との相対比較')

const external = await agent(
  `あなたは AI エージェントハーネス/オーケストレーションの専門家。以下の個人開発ハーネスの設計を、2026年時点の外部実装と相対比較せよ。

【評価対象ハーネスの特徴】
- 2層分離: 内側(vendor非依存の skill chain: task-routing → 設計/実装/検証 subagent → finish-task)+ 外側(project固有の Issue lifecycle)
- 工学原則: State on disk / One item per loop / Fresh context per iteration / Maker-Checker split / Out-of-process supervisor
- skill = markdown で phase 詳細内蔵、description match で発火(Claude Code の Skill 機構)
- subagent 6種(architect/fullstack/qa/security/perf/tech-writer)を role で分離、tools 制限
- 多層防御12層フレーム(実装は2層のみと正直に自己申告)
- eval 2層: L1 構造 snapshot diff + L2 behavioral(claude -p で実 headless 実行し verdict assert)
- 外側: GitHub Projects で Issue を AI 駆動、cron heartbeat で pick、性悪説 Completion Check で自己申告を裏取り、needs-fix で人間 UAT 差し戻し
- Claude Code plugin として marketplace 配布可能な build script あり
- 個人1名 + Windows 環境、semi-autonomous(全自律ではない: budget cap / AI自己merge / 破壊的操作は意図的に持たない)

WebSearch/WebFetch で以下を調査し、それぞれとの相対位置を出せ:
1. Anthropic 公式の agent 構築パターン(Claude Agent SDK, "Building effective agents" の原則, subagent/skill 機構, context engineering)
2. マルチエージェント orchestration OSS(claude-flow, LangGraph, CrewAI, OpenAI Swarm/Agents SDK, AutoGen 等)
3. eval / harness testing の業界プラクティス(promptfoo, LLM-as-judge, behavioral eval)
4. "loop engineering" / autonomous coding agent の運用パターン(Devin, SWE-agent, OpenHands, Aider 等)

各比較で harness_position を ahead/parity/behind/orthogonal で判定し、具体的な gap または lead を述べよ。最後に net_assessment(near-frontier か、独自性はどこか、明確に遅れている点はどこか)と、外部から採用価値のある idea を列挙せよ。`,
  { label: 'external-compare', phase: 'External', schema: EXTERNAL_SCHEMA, effort: 'high' }
)

// ============================================================
phase('Verify')
log('Phase 4: 各次元の defect を独立 skeptic が反証')

const allDefects = scores.flatMap(s =>
  (s.defects || []).map(d => ({ ...d, dimension: s.dimension }))
)

const verifiedDefects = await parallel(
  allDefects.map(d => () =>
    agent(
      `あなたは敵対的検証者。以下の defect 主張を REFUTE しようと試みよ。デフォルトは懐疑。実 repo (${REPO} と C:/Users/hiroki/code/dotconfig) を Read/Bash で確認し、主張が実際に成立するか検証せよ。

次元: ${d.dimension}
主張: ${d.summary}
申告 severity: ${d.severity}
証跡: ${d.evidence}
${d.file ? `該当ファイル: ${d.file}` : ''}

検証観点:
- この defect は実 repo で本当に再現するか(file:line で確認)
- severity は妥当か、過大評価/過小評価でないか
- 既に別ブランチ/dotconfig で修正済みではないか
- fresh-context 原則など harness の設計意図を「defect」と誤認していないか(重複は原則の帰結であり defect でない)

CONFIRMED(実 repo で再現確認) / PLAUSIBLE(もっともらしいが未確認要素あり) / REFUTED(誤り or 設計意図の誤認 or 修正済み)で判定。`,
      { label: `verify:${d.dimension}:${(d.summary || '').slice(0, 20)}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' }
    ).then(v => ({ ...d, ...v }))
  )
).then(rs => rs.filter(Boolean))

const survivingDefects = verifiedDefects.filter(d => d.verdict !== 'REFUTED')

// ============================================================
phase('Synthesize')
log('Phase 5: 検証済み finding + 改善案を統合')

const synthesis = await agent(
  `あなたは EM の技術参謀。AI 開発ハーネスの第5回評価を統合レポートにまとめよ。

【6次元の採点結果】
${JSON.stringify(scores.map(s => ({ dimension: s.dimension, score: s.score, prev: s.prev_score, reason: s.delta_reason, strengths: s.strengths })), null, 2)}

【敵対的検証を通過した defect(REFUTED は除外済み)】
${JSON.stringify(survivingDefects.map(d => ({ dim: d.dimension, summary: d.summary, severity: d.corrected_severity || d.severity, verdict: d.verdict, reasoning: d.reasoning })), null, 2)}

【外部比較】
${JSON.stringify(external, null, 2)}

以下を統合せよ:
1. **総合 vector**: [context / routing / eval / outer-loop / process / platform] の6点と第4回[4/4/3/3/4/4]からの delta。上昇頭打ちか、後退か、進展か。
2. **確定 defect ランキング**: severity 順。各 defect に「最小工数で最大波及する修正」の1行。
3. **改善案の4分類**: user の慣習に従い各改善を minimum guardrail / common standard / team discretion / personal experiment のどれかに分類。会社への Codex/Claude 導入を見据えた観点も含める。
4. **外部との相対位置**: near-frontier か。独自の強み(2層分離 / 性悪説 Checker / 正直な防御スタック申告)と明確な遅れ(あれば)。
5. **次に点を上げる鍵**: 前回は「push-CI fix / 本番 cron 実1周 / agent copy-mode化」だった。今回時点で何が landed し何が残るか。

厳格・高信号で。user は「網羅より判断に効く短い説明」を好む。主張と証跡を分離せよ。`,
  { label: 'synthesis', phase: 'Synthesize', effort: 'high' }
)

return {
  scores: scores.map(s => ({ dimension: s.dimension, score: s.score, prev: s.prev_score, delta_reason: s.delta_reason })),
  defect_count: { total: allDefects.length, surviving: survivingDefects.length, refuted: allDefects.length - survivingDefects.length },
  surviving_defects: survivingDefects.map(d => ({ dim: d.dimension, summary: d.summary, severity: d.corrected_severity || d.severity, verdict: d.verdict })),
  external_position: external.net_assessment,
  synthesis,
}
