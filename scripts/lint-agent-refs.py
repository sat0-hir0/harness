#!/usr/bin/env python3
"""Lint skill / eval spawn references against the agents that actually exist.

Sister guard to the agent-name drift fixed in Issue #81 (sat0-hir0/backlog).
The skills spawn sub-agents by name; when a skill names an agent that has no
`agents/<name>.md`, the Lead spawns a phantom and the chain silently degrades.
This script collects the real agent names from the `name:` frontmatter of
`agents/*.md`, then scans spawn-context lines in skills + eval fixtures for
kebab-case tokens that do not resolve to a real agent. Standard library only
(no PyYAML — frontmatter `name:` is extracted with a regex).

Two checks run against every scanned file:

1. **unresolved**: a spawn-context line names a kebab-case token (e.g.
   `qa-verifier`) that is not one of the real agent names.
2. **bare-reviewer**: a spawn-context line uses the bare word `reviewer`
   (not followed by `系`), which is the exact drift this issue removed.
   `reviewer 系` (the role-category umbrella term) is allowed.

Scope: `skills/**/*.md` + `eval/cases/*.yaml` + `eval/baseline/*.yaml`.
`docs/wip/*.md` (discussion logs) is intentionally excluded.

Usage
-----
    python scripts/lint-agent-refs.py          # scan the default target set
    python scripts/lint-agent-refs.py --json    # JSON output

Exit codes
----------
    0   no violations
    1   at least one violation found
    2   invocation error (no agents dir, bad glob root)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Force UTF-8 on stdout so that Japanese / em-dash / etc. survive Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Extract the `name:` value from an agent frontmatter (MULTILINE over full text).
AGENT_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)

# A line is a "spawn context" line when it mentions actually dispatching agents.
SPAWN_CONTEXT_MARKERS = ("spawn", "召集", "Agent chain", "subagent", "spawned_subagents")

# kebab-case token: at least one hyphen, lowercase alnum segments.
KEBAB_RE = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b")

# Agent-chain notation: kebab-case tokens joined by whitespace-padded ` + ` /
# ` → ` / ` / ` chain separators (e.g. "architect + fullstack-engineer + qa-expert",
# "fullstack-engineer / qa-expert"). Such lines enumerate an agent pipeline even
# without a spawn/召集 keyword, so they must also be scanned — this is the coverage
# hole that let a phantom name hide on a plain enumeration line (task-routing:72).
#
# Precision guards against false positives:
# - the separator MUST be padded by whitespace on both sides, so GitHub paths
#   (`sat0-hir0/backlog`) and slashless joins are excluded;
# - at least one operand token MUST be a real agent name, so generic slash
#   enumerations (`public-behaviour / private-only`, `trade-off / follow-up`)
#   do not qualify a line — only lines that actually name an agent are scanned,
#   which is exactly where a phantom sibling would sit.
_CHAIN_TOKEN = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_CHAIN_SEP = r"\s+(?:\+|→|/)\s+"


def _has_agent_chain(line: str, real_agents: set[str]) -> bool:
    """Detect an agent-chain enumeration anchored on at least one real agent.

    Scans every ` + ` / ` → ` / ` / `-separated run of kebab tokens and returns
    True only when the run has 2+ operands AND at least one operand is a known
    agent. Anchoring on a real agent keeps unrelated slash lists from being
    treated as spawn context, while still catching a phantom that sits beside a
    real agent (e.g. "architect + qa-verifier").
    """
    for m in re.finditer(rf"\b{_CHAIN_TOKEN}\b(?:{_CHAIN_SEP}\b{_CHAIN_TOKEN}\b)+", line):
        run = m.group(0)
        operands = [t for t in re.split(r"\s+(?:\+|→|/)\s+", run)]
        if len(operands) >= 2 and any(op in real_agents for op in operands):
            return True
    return False

# `$skill-name` records (leading `$`) are skill references, not agent names.
SKILL_REF_RE = re.compile(r"\$[a-z][a-z0-9-]+")

# Bare `reviewer` not immediately followed by `系` (the allowed umbrella term).
BARE_REVIEWER_RE = re.compile(r"\breviewer\b(?!\s*系)")

# Allowlisted kebab-case tokens that appear on spawn-context lines but are NOT
# agent names — verdict names, generic adjectives, harness vocabulary, and the
# `reviewer` role-category umbrella noun. Everything kebab-case that is NOT here
# and NOT a real agent is flagged, so a genuinely new phantom agent name (e.g. a
# future `qa-verifier` typo) still trips the check.
#
# Deliberately does NOT include concrete phantom agent names such as
# `qa-verifier` / `docs-curator` — those MUST resolve to real agents or fail.
ALLOWLIST_TOKENS = {
    # role-category umbrella noun
    "reviewer",
    # verdict / routing vocabulary
    "delegate-single",
    "delegate-slice",
    "lead-direct",
    # generic adjectives / nouns that happen to be kebab-case
    "read-only",
    "hand-off",
    "stress-test",
    "pure-info",
    "already-specified",
    "mid-stream",
    "entry-point",
    "split-pane",
    "in-process",
    "one-directional",
    "self-review",
    "sub-agent",
    "future-proofing",
}


@dataclass
class Violation:
    file: str
    line: int
    token: str
    category: str  # "unresolved" | "bare-reviewer"


def collect_agent_names() -> set[str]:
    """Return the set of real agent names from agents/*.md frontmatter."""
    agents_dir = REPO_ROOT / "agents"
    if not agents_dir.is_dir():
        print(f"error: {agents_dir} is not a directory", file=sys.stderr)
        sys.exit(2)
    names: set[str] = set()
    for md in sorted(agents_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = AGENT_NAME_RE.search(text)
        if m:
            names.add(m.group(1))
    return names


def target_files() -> list[Path]:
    """Collect the files to scan: skills markdown + eval yaml fixtures."""
    files: list[Path] = []
    files.extend(sorted((REPO_ROOT / "skills").glob("**/*.md")))
    files.extend(sorted((REPO_ROOT / "eval" / "cases").glob("*.yaml")))
    files.extend(sorted((REPO_ROOT / "eval" / "baseline").glob("*.yaml")))
    return files


def is_spawn_context(line: str, real_agents: set[str]) -> bool:
    """Return True when the line describes dispatching an agent.

    Two signals qualify a line:
    1. an explicit spawn/召集/Agent chain/subagent/spawned_subagents keyword, or
    2. agent-chain notation — 2+ kebab-case tokens joined by `+` / `→` / `/`
       with at least one operand being a real agent, which enumerates a pipeline
       even when no keyword is present.
    """
    if any(marker in line for marker in SPAWN_CONTEXT_MARKERS):
        return True
    return _has_agent_chain(line, real_agents)


def scan_file(path: Path, real_agents: set[str]) -> list[Violation]:
    """Scan one file for spawn-context references to non-existent agents."""
    out: list[Violation] = []
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    for idx, line in enumerate(text.splitlines(), start=1):
        if not is_spawn_context(line, real_agents):
            continue
        # Strip `$skill-name` tokens so they are not mistaken for agent names.
        scrubbed = SKILL_REF_RE.sub(" ", line)
        # Check 1: unresolved kebab-case tokens.
        for token in KEBAB_RE.findall(scrubbed):
            if token in ALLOWLIST_TOKENS:
                continue
            if token not in real_agents:
                out.append(Violation(file=rel, line=idx, token=token, category="unresolved"))
        # Check 2: bare `reviewer` (drift re-detection). `reviewer 系` is allowed.
        if BARE_REVIEWER_RE.search(line):
            out.append(Violation(file=rel, line=idx, token="reviewer", category="bare-reviewer"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that every agent named in a skill/eval spawn context resolves "
            "to a real agents/<name>.md, and that no bare `reviewer` spawn slips in."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON.",
    )
    args = parser.parse_args()

    real_agents = collect_agent_names()
    findings: list[Violation] = []
    for path in target_files():
        findings.extend(scan_file(path, real_agents))

    if args.json:
        print(
            json.dumps(
                {
                    "real_agents": sorted(real_agents),
                    "violations": [asdict(v) for v in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not findings:
            print(
                "OK: all spawn references resolve to "
                f"{len(real_agents)} real agents ({', '.join(sorted(real_agents))})."
            )
        for v in findings:
            print(f"{v.file}:{v.line}:{v.token} [{v.category}]")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
