export const meta = {
  name: 'harness-reeval-4',
  description: '4th harness eval after merging the #106 wave + DRY_RUN flip + chezmoi landmine fix — score the new landed state',
  phases: [
    { title: 'Read', detail: '5 parallel readers of the now-merged state' },
    { title: 'Judge', detail: '6 dimension judges, strict landed-state scoring' },
    { title: 'Verify', detail: 'adversarial verify per dimension' },
    { title: 'Critique', detail: 'blind spots + trajectory + honest vector' },
  ],
}

const CTX = `EVALUATION CONTEXT — FOURTH harness evaluation, 2026-07-03 late.
WHAT CHANGED since the 3rd eval (all now LANDED on main + deployed):
- All 9 open PRs MERGED: harness#23-26 (L2 no-verdict fix, description-length lint, wave-status vendor record, cost accounting), backlog#114-115 (injection hardening in issue-execute + §17 wiring in prepare-uat), dotfiles#14-16 (DRY_RUN flip criterion + false, cron injection hardening, §17 body-append).
- Issues #107-#113 all moved to Done.
- DRY_RUN flipped to false IN PRODUCTION: deployed completion-check-routine SKILL.md line 19 = DRY_RUN=false (verified). The cron completion-check now actually moves board cards.
- chezmoi stale-agents-mirror landmine FIXED: dotconfig commit 3b37501 synced dot_config/skillshare/agents/ to current hub; chezmoi status no longer lists agents; a routine apply is now a no-op on them (no more revert of #82/#95 fixes).
- heartbeat + completion-check deployed SKILL.md re-synced to main (injection §0 present, body-append present).
- harness main head = 2a8fa11 (includes §12 third-eval report at 712efec). dotconfig main = 3b37501 (pushed). backlog main includes #114/#115.

STILL BROKEN (verify these are UNCHANGED — do not assume the merge fixed them):
- push-to-main CI: eval-gate.yml future-plans step uses github.base_ref which is EMPTY on push events -> 'git diff origin/..HEAD' fatal. Latest push run (aaf5491) = FAILURE. NO merged PR touched this. Confirm with: gh run list --workflow eval-gate.yml --repo sat0-hir0/harness.
- deployed agents junctions: ~/.claude/agents/*.md are FILE-targeting Windows junctions; Node readFileSync -> ENOENT. The mirror fix corrected CONTENT drift but NOT the junction-unreadable defect (different root cause: skillshare agent link mode). Confirm: node -e readFileSync on a deployed agent.

SCORING RULE: score reflects main + deployed landed state. This time most improvements ARE landed, so they DO count now. But newly-merged-yet-unexercised runtime (e.g. DRY_RUN=false has not yet completed a real production cron cycle) is 'landed but unproven' — note it. Prior score vectors: 07-02 [context3 routing3 eval2 outer3 process3 platform3]; 07-03am [3/4/3/3/4/3]; 07-03pm(3rd, strict) [3/4/3/3/3/3]. 5 = state-of-the-art solo-dev harness.
READ-ONLY: no gh mutations, no file writes outside scratch, no working-tree checkouts (use git show origin/<ref>:<path>). Repos at C:/Users/hiroki/code/{harness,backlog,dotconfig}. Deployed at ~/.claude.`

const READERS = [
  { id: 'merged-skills-gates', task: 'On harness main (2a8fa11): read the now-MERGED description-length lint (scripts/check-frontmatter-yaml.py — confirm warn>1400/fail>=1535 is live, run it, report where task-routing 1459 lands: warn or pass). Read the L2 no-verdict fix (eval/scripts/eval-behavioral.py VERDICT_RE + new baseline). Re-check all 6 skills parse + agent-refs resolve. Confirm which previously-pending items are now landed vs still absent.' },
  { id: 'ci-push-bug', task: 'Verify the push-to-main CI bug is STILL live post-merge: gh run list --workflow eval-gate.yml --repo sat0-hir0/harness (last ~8 runs, event+conclusion+headSha). Read .github/workflows/eval-gate.yml on main — quote the exact future-plans step and how BASE_REF/github.base_ref is used on push vs pull_request. State definitively whether any merged PR fixed it and whether main-push CI is green or red now.' },
  { id: 'dryrun-live', task: 'Audit the now-PRODUCTION outer loop: deployed completion-check-routine SKILL.md DRY_RUN value (grep line 19), and whether a real production cron cycle has run yet (gh: recent completion-check comments on backlog issues — look for ✅/↩️/⚠️ Completion Check prefixes posted AFTER the merge time ~16:13Z today vs the old 🔍 dry-run prefix). Board state now: gh backlog columns, Done count, any Awaiting UAT. Did the flip actually exercise, or is it landed-but-unproven?' },
  { id: 'deployed-drift', task: 'Hash-audit the FULL distribution chain post-fix: harness main skills/agents vs ~/.config/skillshare vs ~/.claude/skills; backlog skills vs deployed; dotconfig scheduled-tasks source vs ~/.claude/scheduled-tasks (DRY_RUN value!). CRITICAL: test whether ~/.claude/agents/*.md are readable by Node (node -e readFileSync) — the junction-ENOENT defect; and whether chezmoi status still flags agents (the landmine). Report every remaining drift and whether the agents-readability defect persists.' },
  { id: 'design-doc-eval-meta', task: 'Read harness docs/harness-design.md + CLAUDE.md eval-gate contract + docs/wip (esp the §12 third-eval just committed). Check: (a) does §17 design now match the merged prepare-uat/completion-check wiring? (b) does CLAUDE.md still describe eval as "does not run skills / L2 unimplemented" despite L2 being landed (the doc-drift defect from 3rd eval)? (c) is the push-CI-broken finding recorded anywhere as a tracked issue, or is it an untracked known-defect? Report design-vs-reality gaps that survive the merge.' },
]
const RSCHEMA = { type:'object', required:['area','summary','facts','stillBroken'], properties:{ area:{type:'string'}, summary:{type:'string'}, facts:{type:'array',maxItems:16,items:{type:'object',required:['claim','evidence'],properties:{claim:{type:'string'},evidence:{type:'string'}}}}, stillBroken:{type:'array',items:{type:'string'}} } }

const DIMS = [
  { key:'context', name:'context 経済性', anchor:'3/3/3' },
  { key:'routing', name:'routing 信頼性', anchor:'3/4/4' },
  { key:'eval', name:'eval・観測性', anchor:'2/3/3' },
  { key:'outerloop', name:'外側ループ自動化', anchor:'3/3/3' },
  { key:'process', name:'process 重量 vs 価値', anchor:'3/4/3' },
  { key:'platform', name:'platform 適合', anchor:'3/3/3' },
]
const JSCHEMA = { type:'object', required:['dimension','scoreNow','rationale','landedGains','stillBroken','selfVerification'], properties:{ dimension:{type:'string'}, scoreNow:{type:'integer',minimum:1,maximum:5}, rationale:{type:'string'}, landedGains:{type:'array',items:{type:'string'},description:'improvements that are now landed AND count toward the score'}, stillBroken:{type:'array',items:{type:'object',required:['title','evidence'],properties:{title:{type:'string'},evidence:{type:'string'}}}}, selfVerification:{type:'array',items:{type:'string'}} } }
const VSCHEMA = { type:'object', required:['dimension','scoreChallenge','verdicts'], properties:{ dimension:{type:'string'}, scoreChallenge:{type:'string'}, verdicts:{type:'array',items:{type:'object',required:['title','verdict','evidence'],properties:{title:{type:'string'},verdict:{type:'string',enum:['valid','already-covered','questionable']},evidence:{type:'string'}}}} } }

phase('Read')
const readers = (await parallel(READERS.map(r => () =>
  agent(`${CTX}\n\nReader "${r.id}". ${r.task}\nCommand-verified facts only.`, { label:`read:${r.id}`, phase:'Read', schema:RSCHEMA })
))).filter(Boolean)
const digest = JSON.stringify(readers)
log(`readers: ${readers.length}/5`)

const judged = (await pipeline(
  DIMS,
  d => agent(`${CTX}\n\nJudge for "${d.name}" (prior anchors ${d.anchor}). Readers:\n${digest}\n\nMove the score from the 3rd-eval anchor with SELF-VERIFIED command evidence only. Now that the wave is merged, landed gains DO count — but distinguish 'landed & exercised' from 'landed but unproven' (e.g. DRY_RUN=false that has not completed a real cron cycle). List what is still broken on main/deployed. Rationale in Japanese.`,
    { label:`judge:${d.key}`, phase:'Judge', schema:JSCHEMA }),
  (j,d) => j ? agent(`${CTX}\n\nAdversarial verifier for "${d.name}". Judge scored ${j.scoreNow}: ${j.rationale}\nClaimed landed gains: ${JSON.stringify(j.landedGains)}\nClaimed still-broken: ${JSON.stringify(j.stillBroken)}\n\nRefute: (1) is each 'landed gain' actually landed on main+deployed AND exercised, or just merged-but-unproven? reproduce; (2) is each still-broken item actually still broken post-merge? run the command; (3) does the score hold? A dimension should only rise if the gain is landed AND the evidence shows it works, not merely merged. Command-verified evidence per verdict.`,
    { label:`verify:${d.key}`, phase:'Verify', schema:VSCHEMA }).then(v=>({judge:j,verify:v})) : null
)).filter(Boolean)

phase('Critique')
const critique = await agent(`${CTX}\n\nCritique agent closing the 4th eval. Judges+verifies:\n${JSON.stringify(judged)}\n\nJapanese strings. (1) blind spots this round; (2) is the score now enforcement-backed given the merge, or are dimensions rising on merged-but-unexercised work? (3) trajectory across 4 evals in 2 days — give the honest final landed-state vector and say explicitly which dimensions rose because work got EXERCISED vs merely MERGED. (4) what are the top 2-3 things that must happen for the next eval to rise (name them concretely — e.g. push-CI fix, a real production cron cycle, agents junction fix).`,
  { label:'critique', phase:'Critique', schema:{ type:'object', required:['blindSpots','enforcementCheck','trajectory','finalVector','nextToRise'], properties:{ blindSpots:{type:'array',items:{type:'string'}}, enforcementCheck:{type:'string'}, trajectory:{type:'string'}, finalVector:{type:'string'}, nextToRise:{type:'array',items:{type:'string'}} } } })

return { readers: readers.map(r=>({area:r.area,summary:r.summary,stillBroken:r.stillBroken})), judged, critique }