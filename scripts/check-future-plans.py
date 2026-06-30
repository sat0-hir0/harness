#!/usr/bin/env python3
"""Detect forbidden future-plans / milestone / Wave / Phase strings in a diff.

Sister to the rule defined in `skills/task-routing/SKILL.md` and invoked from
`skills/finish-task/SKILL.md` Phase 4-5. The skill orchestration stays in
markdown; this script makes the grep step reproducible across OSes and AI
vendors. Standard library only.

Usage
-----
    python check-future-plans.py                 # diff: HEAD vs working tree (staged + unstaged)
    python check-future-plans.py --base main     # diff: main..HEAD
    python check-future-plans.py --files a.md b.md   # only the listed files (full content scan)
    python check-future-plans.py --json          # JSON output (for finish-task YAML)

Exit codes
----------
    0   no violations
    1   at least one violation found
    2   invocation error (bad args, git failure)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Force UTF-8 on stdout so that Japanese / em-dash / etc. in excerpts survive Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


@dataclass
class Violation:
    file: str
    line: int
    category: str  # "milestone-name" | "future-tense" | "future-proofing"
    excerpt: str
    pattern: str


# Detection patterns. Each entry: (category, compiled regex, human-readable pattern label).
# Patterns are intentionally narrow to keep false positives low; broaden in tandem with the rule.
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # --- milestone / Wave / Phase / Sprint names ---
    ("milestone-name", re.compile(r"\bM[0-9]+(?:-M?[0-9]+)?\b"), r"M<N>(-M<N>)"),
    ("milestone-name", re.compile(r"\bWave\s+[0-9]+(?:-[A-Z]+)?\b"), r"Wave <N>(-<X>)"),
    ("milestone-name", re.compile(r"\bSprint\s+[0-9]+\b"), r"Sprint <N>"),
    # `Phase <N>` is intentionally listed but excluded when it sits inside a markdown heading
    # or a code/quote block (see is_excluded_line).
    ("milestone-name", re.compile(r"\bPhase\s+[0-9]+\b"), r"Phase <N>"),
    # --- future-tense commitments ---
    ("future-tense", re.compile(r"\bwill be (implemented|added|cut|moved|removed|done)\b", re.IGNORECASE), r"will be <verb>"),
    ("future-tense", re.compile(r"\blater wave\b", re.IGNORECASE), r"later wave"),
    ("future-tense", re.compile(r"\bdeferred to\s+(?!the\b)\w", re.IGNORECASE), r"deferred to <target>"),
    ("future-tense", re.compile(r"\bis cut when\b", re.IGNORECASE), r"is cut when"),
    ("future-tense", re.compile(r"M[0-9]+\s*で再評価"), r"M<N> で再評価"),
    ("future-tense", re.compile(r"Phase\s*[0-9]+\s*で実装"), r"Phase <N> で実装"),
    ("future-tense", re.compile(r"Wave\s*[0-9]+\s*で対応"), r"Wave <N> で対応"),
    # --- future-proofing / extensibility ---
    ("future-proofing", re.compile(r"\bfor future\s+\w", re.IGNORECASE), r"for future <X>"),
    ("future-proofing", re.compile(r"\bextensible to\b", re.IGNORECASE), r"extensible to"),
    ("future-proofing", re.compile(r"\bmay add\b[^.]{0,40}\blater\b", re.IGNORECASE), r"may add ... later"),
    ("future-proofing", re.compile(r"将来\s*\S+\s*に拡張"), r"将来 <X> に拡張"),
    ("future-proofing", re.compile(r"\(and any future\b", re.IGNORECASE), r"(and any future ...)"),
]

# Heading exclusion: skill SKILL.md files use `## Phase N: ...` as structural headings,
# which are not milestone commitments.
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")

# Y-trace `accepting:` field in task-routing example outputs is intentionally allowed to
# describe trade-offs in present terms (e.g., "wave 分割で実装期間 1 → 3 セッション").
Y_TRACE_ACCEPTING_RE = re.compile(r"accepting:\s*[^,]*wave[^,]*", re.IGNORECASE)

# A line is considered a rule-declaration literal quote when it lists multiple forbidden
# patterns together inside backticks (e.g., "`M[0-9]`, `Phase [0-9]`, `Wave [0-9]`").
RULE_LITERAL_RE = re.compile(r"`[^`]*(M\[0-9\]|Phase \[0-9\]|Wave \[0-9\])[^`]*`")

# Self-reference: files whose job is to *describe* the rule are not violators. The skill
# documents below define the rule, quote the patterns, and explain why they are banned —
# scanning them produces nothing but false positives. Other files in the repo (agent
# prompts, design docs, READMEs) still get scanned as normal.
_SELF_REFERENCE_RE = re.compile(
    r"""
    (?:^|/)
    (?:
        # The script itself is full of forbidden literals as test patterns.
        scripts/check-future-plans\.py
      | # Anything under docs/ is meta-documentation about the harness; abstract stage
        # labels like "Phase 0: 着手" are pedagogical, not milestone commitments.
        docs/
      | # Every skill defines its own internal Phase / Step / Wave vocabulary inside
        # SKILL.md / ATTRIBUTION.md — those are structure, not commitments.
        skills/[^/]+/(?:SKILL|ATTRIBUTION)\.md
    )
    """,
    re.VERBOSE,
)


def is_self_reference(path: str) -> bool:
    """Return True if the file's job is to describe the rule (not be subject to it).

    The harness repo deliberately uses Phase / Step / Wave as the vocabulary for skill
    structure and documentation. Treat anything under skills/*/SKILL.md, skills/*/
    ATTRIBUTION.md, docs/, and the script itself as self-referential. Other files
    (agents/*.md, README.md, project-side files) are still subject to scanning.
    """
    normalised = path.replace("\\", "/")
    return _SELF_REFERENCE_RE.search(normalised) is not None


# Inline skill section refs like `Phase 3-1` / `Step 4-5` look like milestones but
# point at structural subsections of the skill itself. Always benign.
SECTION_REF_RE = re.compile(r"\b(?:Phase|Step|Section)\s+[0-9]+-[0-9A-Z]+\b")

# A forbidden literal wrapped in Japanese / English quotes is almost always a quoted
# example, not an actual commitment. Matching is broad: any quote pair around the line's
# match excerpt suffices.
QUOTED_EXAMPLE_RE = re.compile(
    r"""[「『"'`][^「『"'`]{0,80}(?:Wave\s+[0-9]+|Phase\s+[0-9]+|M[0-9]+|Sprint\s+[0-9]+)[^」』"'`]{0,80}[」』"'`]"""
)


def is_excluded_line(line: str) -> bool:
    """Return True when the line is not a real violation site."""
    if HEADING_RE.match(line):
        return True
    # Lines that *declare* the rule by listing forbidden patterns together (one declarative
    # line typically holds 2+ literal regex strings inside backticks).
    backtick_hits = RULE_LITERAL_RE.findall(line)
    if len(backtick_hits) >= 2:
        return True
    # Y-trace accepting: ... wave ... lines.
    if Y_TRACE_ACCEPTING_RE.search(line):
        return True
    # Section refs like `Phase 3-1` / `Step 4-5` — structural pointers, not commitments.
    if SECTION_REF_RE.search(line):
        return True
    # Forbidden literal inside quotes is a quoted example.
    if QUOTED_EXAMPLE_RE.search(line):
        return True
    # Bullet items that explain "OK な表現" / "ただし除外" — heuristic: line contains
    # 「除外」 or "OK な" together with a forbidden pattern.
    if ("除外" in line or "OK な" in line) and any(p.search(line) for _, p, _ in PATTERNS):
        return True
    return False


def fence_state(lines: list[str]) -> list[bool]:
    """Pre-compute whether each line sits inside a ``` fenced block.

    Code fences in skill SKILL.md often quote forbidden strings as examples (e.g., the
    YAML schema or a bash invocation literal). These are documentation, not commitments.
    Pre-computing avoids the O(N^2) cost of re-scanning the file for every line.
    """
    in_fence = False
    out: list[bool] = []
    for raw in lines:
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
        out.append(in_fence)
    return out


def scan_text(file: str, text: str) -> list[Violation]:
    """Scan the full text of a single file."""
    out: list[Violation] = []
    lines = text.splitlines()
    fences = fence_state(lines)
    for idx, line in enumerate(lines):
        if is_excluded_line(line):
            continue
        if fences[idx]:
            continue
        for category, pattern, label in PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            out.append(
                Violation(
                    file=file,
                    line=idx + 1,
                    category=category,
                    excerpt=line.rstrip()[:200],
                    pattern=label,
                )
            )
            break  # one pattern per line is enough; surface the first match
    return out


def run_git(args: list[str]) -> str:
    """Run a git command and return its stdout. Exit 2 on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except FileNotFoundError:
        print("error: git is not on PATH", file=sys.stderr)
        sys.exit(2)
    except subprocess.CalledProcessError as exc:
        print(f"error: git {' '.join(args)} failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


def diff_files(base: str | None) -> list[str]:
    """Return the list of files changed in the relevant diff.

    `--base REF` uses two dots (`REF..HEAD`) so we get the files this branch
    introduced relative to REF, not the merge-base view (three dots).
    """
    if base:
        spec = [f"{base}..HEAD"]
    else:
        spec = ["HEAD"]
    out = run_git(["diff", "--name-only", *spec])
    return [f for f in out.splitlines() if f.strip()]


def file_content_working_tree(path: str) -> str | None:
    """Return the working-tree content of a file (current state). None if missing.

    Reads the on-disk file, NOT `git show HEAD:<path>`. Callers that want HEAD
    content must read it explicitly via git.
    """
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None  # binary — not a markdown / code file we care about


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect forbidden future-plans / milestone / Wave / Phase strings. "
            "See $task-routing Boundary for the rule and $finish-task Phase 4-5 for invocation."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="Compare REF..HEAD instead of HEAD vs working tree.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        metavar="PATH",
        help="Scan only these files (full content, ignores git diff).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON for downstream YAML report.",
    )
    args = parser.parse_args()

    if args.files:
        targets = args.files
    else:
        targets = diff_files(args.base)

    findings: list[Violation] = []
    for f in targets:
        if is_self_reference(f):
            continue
        content = file_content_working_tree(f)
        if content is None:
            continue
        findings.extend(scan_text(f, content))

    if args.json:
        print(json.dumps([asdict(v) for v in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: no future-plans / milestone / Wave / Phase violations detected.")
        for v in findings:
            print(f"{v.file}:{v.line}:{v.category}: {v.excerpt}  [pattern: {v.pattern}]")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
