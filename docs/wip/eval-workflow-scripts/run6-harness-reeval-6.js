export const meta = {
  name: 'harness-reeval-6',
  description: '6th harness eval after push-CI fix + agents copy-mode landed & exercised',
  phases: [
    { title: 'Read', detail: '5 parallel readers of current landed state' },
    { title: 'Judge', detail: '6 dimension judges, exercised>merged discipline' },
    { title: 'Verify', detail: 'adversarial verify per dimension' },
    { title: 'Critique', detail: 'blind spots + trajectory + honest vector' },
  ],
}

const CTX = `EVALUATION CONTEXT — SIXTH harness evaluation, 2026-07-04.
Prior landed-state vectors [context/routing/eval/outer/process/platform]:
- 07-02: [3/3/2/3/3/3]
- 07-03am: [3/4/3/3/4/3]
- 07-03pm (3rd, strict): [3/4/3/3/3/3]
- 07-03late (4th): [4/4/3/3/4/4]
- 07-04 (5th, 36 agents): [4/4/3/4/4/4] — outer-loop rose 3→4 (completion-check rubber-stamp replaced by independent-evidence + DRY_RUN=false flip + §17 body-append wired + both crons firing).

WHAT CHANGED since the 5th eval (all now LANDED on main + deployed AND exercised):
- **push-CI fix MERGED & EXERCISED** (harness #28, squash 8a7a20b): eval-gate.yml future-plans step now guarded with 'if: github.event_name == pull_request'. The 5th eval's #4 defect (medium: main-push CI red 3/3 from empty base_ref) is RESOLVED. VERIFIED: the post-merge main-push run (headSha 3849e55) = conclusion SUCCESS. main-push CI is now green for the first time across all 6 evals. All landed gates (frontmatter/agent-ref/fixture-sync lint) now enforce on main-push, not just PR.
- **agents copy-mode fix MERGED & EXERCISED** (dotfiles #17, dotconfig main 6b0cd9f): 5th eval's #1 defect (CRITICAL: deployed agents 6/6 file-junction ENOENT, delegate chain 実機不発) is RESOLVED. VERIFIED: node readFileSync on ~/.claude/agents/*.md = 6/6 OK (real files, LinkType null). qa-expert實機-verified idempotent, skills unaffected. The sync script now forces --agent-mode copy + purges stale junctions + sync --force. Self-reproducing junction defect eliminated.
- §13 fourth-eval report landed on main via PR #27 (squash 3849e55), Codex P2 (score-count 4→3) fixed.
- #116/#117 both Done+closed, #118 closed as not-planned (its goal — production cron moving the board — was already met naturally: the 03:30Z #116 bounce IS a real DRY_RUN=false board move; forward-marker theater was correctly declined).
- harness main head = 3849e55. dotconfig main = 6b0cd9f. backlog board: harness Issues #107-#118 all Done/closed.

STILL POTENTIALLY OPEN (verify current state, do not assume):
- 5th eval #2 (high): trigger contract (expected_trigger/expected_no_trigger) not in eval-regression.py diff surface — a flipped trigger stays silent. Check if still true on main.
- 5th eval #3 (high): SKILL.md prose→case source drift passes fixture-sync. Check if still true.
- 5th eval #5-#7 (low): Done!=closed (now mostly closed?), production cron forward-marker (bounce exists, forward may not), DRY_RUN re-sync manual dependency.
- eval doc-drift: does CLAUDE.md still say 'eval does not run skills / L2 unimplemented' despite L2 landed?

SCORING RULE: score = main + deployed landed state, and a dimension rises only if the gain is landed AND exercised (command-reproduced working), not merely merged. The two big fixes this round ARE exercised (main-push green + agents 6/6 readable, both command-verified above) — so they count. 5 = state-of-the-art solo-dev harness.
READ-ONLY: no gh mutations, no file writes outside scratch, no working-tree checkouts (use git show origin/<ref>:<path>). Repos at C:/Users/hiroki/code/{harness,backlog,dotconfig}. Deployed at ~/.claude.`

const READERS = [
  { id: 'ci-gates-exercised', task: 'Verify the push-CI fix on main is landed AND exercised: read .github/workflows/eval-gate.yml on main (the if-guard on future-plans step), then gh run list --workflow eval-gate.yml --repo sat0-hir0/harness (last ~8 runs, event+conclusion+headSha) — confirm the latest main-PUSH run is SUCCESS (not just PR runs). Report whether main-push CI is now green and whether all lint gates (frontmatter/agent-ref/fixture-sync) run on push. Also assess: does skipping future-plans on push leave a real gap (is it in lefthook pre-push? read lefthook.yml).' },
  { id: 'agents-runtime', task: 'Verify the agents copy-mode fix is landed AND exercised: node readFileSync loop over ~/.claude/agents/*.md (report OK/FAIL count and LinkType). Read the fixed sync script dotconfig .chezmoiscripts/run_once_after_13-skillshare-sync.ps1.tmpl on main — confirm --agent-mode copy + junction purge + sync --force are present. Hash-compare harness main agents/ vs ~/.config/skillshare/agents vs ~/.claude/agents (are they now real files matching source?). Assess: is the delegate/spawn chain now functional at the deployed path (the 5th-eval CRITICAL)?' },
  { id: 'eval-triggers', task: 'Assess eval observability on main: (1) do expected_trigger/expected_no_trigger fields get EVALUATED now, or still only recorded (read eval/scripts/eval-regression.py + eval-behavioral.py + a few eval/cases/*.yaml)? (2) does SKILL.md prose change get caught by fixture-sync, or can prose drift from cases silently (the 5th-eval #3)? (3) L2 behavioral runner state: which skills have baselines, N, known no-verdict rate. (4) CLAUDE.md eval-gate contract — does it still claim eval does not run skills / L2 unimplemented despite L2 landed? Report doc-drift.' },
  { id: 'outer-loop-live', task: 'Audit the outer loop LIVE post-5th-eval: gh backlog board column counts, Done/closed reconciliation for #107-#118 (are they now BOTH board-Done AND gh-closed, resolving the Done!=closed gap?). completion-check cron: deployed DRY_RUN value, recent production verdict comments (✅/↩️/⚠️ Completion Check prefixes) — is there a forward (✅) marker yet or only bounce (↩️, e.g. the 03:30Z #116)? Both crons lastRunAt today? Assess whether outer-loop 4 holds or moves.' },
  { id: 'context-routing-process', task: 'Assess context/routing/process on main: description-length lint live + task-routing description char count (still ~1459 WARN?); all 6 skills parse + agent-refs resolve (run lints); any NEW skill-body defects (the task-slicing Step 3-4 misplacement / trigger self-contradiction / $adr-proposal vs $propose-adr drift from prior evals — still present?); ceremony weight (XS exemption / light UAT form still there); §17 wiring symmetric on prepare-uat+completion-check. Report what is landed-and-working vs still-broken for these 3 dimensions.' },
]
const RSCHEMA = { type:'object', required:['area','summary','facts','stillBroken'], properties:{ area:{type:'string'}, summary:{type:'string'}, facts:{type:'array',maxItems:16,items:{type:'object',required:['claim','evidence'],properties:{claim:{type:'string'},evidence:{type:'string'}}}}, stillBroken:{type:'array',items:{type:'string'}} } }

const DIMS = [
  { key:'context', name:'context 経済性', anchor:'5th: 4' },
  { key:'routing', name:'routing 信頼性', anchor:'5th: 4' },
  { key:'eval', name:'eval・観測性', anchor:'5th: 3' },
  { key:'outerloop', name:'外側ループ自動化', anchor:'5th: 4' },
  { key:'process', name:'process 重量 vs 価値', anchor:'5th: 4' },
  { key:'platform', name:'platform 適合', anchor:'5th: 4' },
]
const JSCHEMA = { type:'object', required:['dimension','scoreNow','rationale','landedGains','stillBroken','selfVerification'], properties:{ dimension:{type:'string'}, scoreNow:{type:'integer',minimum:1,maximum:5}, rationale:{type:'string'}, landedGains:{type:'array',items:{type:'string'}}, stillBroken:{type:'array',items:{type:'object',required:['title','evidence'],properties:{title:{type:'string'},evidence:{type:'string'}}}}, selfVerification:{type:'array',items:{type:'string'}} } }
const VSCHEMA = { type:'object', required:['dimension','scoreChallenge','verdicts'], properties:{ dimension:{type:'string'}, scoreChallenge:{type:'string'}, verdicts:{type:'array',items:{type:'object',required:['title','verdict','evidence'],properties:{title:{type:'string'},verdict:{type:'string',enum:['valid','already-covered','questionable']},evidence:{type:'string'}}}} } }

phase('Read')
const readers = (await parallel(READERS.map(r => () =>
  agent(`${CTX}\n\nReader "${r.id}". ${r.task}\nCommand-verified facts only.`, { label:`read:${r.id}`, phase:'Read', schema:RSCHEMA })
))).filter(Boolean)
const digest = JSON.stringify(readers)
log(`readers: ${readers.length}/5`)

const judged = (await pipeline(
  DIMS,
  d => agent(`${CTX}\n\nJudge for "${d.name}" (5th-eval anchor: ${d.anchor}). Readers:\n${digest}\n\nMove the score from anchor ONLY with self-verified command evidence. This round's two big fixes (push-CI green, agents 6/6 readable) ARE exercised — if they lift your dimension, that is legitimate. But distinguish landed-and-exercised from merely-merged. Note especially whether platform can rise now that the CRITICAL agents defect is resolved, and whether eval can rise now that main-push gates actually enforce. List what is still broken. Rationale in Japanese.`,
    { label:`judge:${d.key}`, phase:'Judge', schema:JSCHEMA }),
  (j,d) => j ? agent(`${CTX}\n\nAdversarial verifier for "${d.name}" (anchor ${d.anchor}). Judge scored ${j.scoreNow}: ${j.rationale}\nClaimed landed gains: ${JSON.stringify(j.landedGains)}\nClaimed still-broken: ${JSON.stringify(j.stillBroken)}\n\nRefute: (1) is each 'landed gain' actually landed on main+deployed AND exercised (command-reproduce it: rerun the CI check, the node readFileSync, the lint)? (2) is each still-broken item actually still broken? run the command; (3) does the score hold? A dimension rises only if the gain is exercised-working, not merely merged. Be adversarial about score inflation — with two big fixes this round there is temptation to over-raise. Command-verified evidence per verdict.`,
    { label:`verify:${d.key}`, phase:'Verify', schema:VSCHEMA }).then(v=>({judge:j,verify:v})) : null
)).filter(Boolean)

phase('Critique')
const critique = await agent(`${CTX}\n\nCritique agent closing the 6th eval. Judges+verifies:\n${JSON.stringify(judged)}\n\nJapanese strings. (1) blind spots this round; (2) enforcement check: are the rises exercised-backed given push-CI green + agents readable are both command-verified this round? (3) trajectory across 6 evals in 3 days — honest final landed vector, and which dimensions rose because work got EXERCISED (not merely merged). Note that 2 of the 3 prior-round 'next to rise' items (push-CI, agents copy-mode) are now DONE — did the predicted rises materialize? (4) what are the top 2-3 things that must happen for the NEXT eval to rise — is the harness approaching a ceiling where remaining gains are eval-flywheel / trigger-contract depth rather than defect-fixing?`,
  { label:'critique', phase:'Critique', schema:{ type:'object', required:['blindSpots','enforcementCheck','trajectory','finalVector','nextToRise'], properties:{ blindSpots:{type:'array',items:{type:'string'}}, enforcementCheck:{type:'string'}, trajectory:{type:'string'}, finalVector:{type:'string'}, nextToRise:{type:'array',items:{type:'string'}} } } })

return { readers: readers.map(r=>({area:r.area,summary:r.summary,stillBroken:r.stillBroken})), judged, critique }