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
import functools
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
# Patterns are intentionally narrow to keep false positives low; broaden in tandem with the
# rule. Most regexes use IGNORECASE so that lowercase forms like `wave 6` / `phase 2` /
# `sprint 3` are caught alongside the capitalized canonical form. The `M<N>` milestone
# pattern is the exception: it is case-sensitive because the canonical spelling is
# uppercase (`M0`-`M5`), and lowercase `m1` / `m2` are ordinary match-slug fragments in
# project test data (see TestNoFalsePositivesPython in eval/scripts/test_check_future_plans.py).
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # --- milestone / Wave / Phase / Sprint names ---
    ("milestone-name", re.compile(r"\bM[0-9]+(?:-M?[0-9]+)?\b"), r"M<N>(-M<N>)"),
    ("milestone-name", re.compile(r"\bWave\s+[0-9]+(?:-[A-Z]+)?\b", re.IGNORECASE), r"Wave <N>(-<X>)"),
    ("milestone-name", re.compile(r"\bSprint\s+[0-9]+\b", re.IGNORECASE), r"Sprint <N>"),
    # `Phase <N>` is intentionally listed but excluded when it sits inside a markdown heading
    # or a code/quote block (see is_excluded_line).
    ("milestone-name", re.compile(r"\bPhase\s+[0-9]+\b", re.IGNORECASE), r"Phase <N>"),
    # --- future-tense commitments ---
    ("future-tense", re.compile(r"\bwill be (implemented|added|cut|moved|removed|done)\b", re.IGNORECASE), r"will be <verb>"),
    ("future-tense", re.compile(r"\blater wave\b", re.IGNORECASE), r"later wave"),
    ("future-tense", re.compile(r"\bdeferred to\s+(?!the\b)\w", re.IGNORECASE), r"deferred to <target>"),
    ("future-tense", re.compile(r"\bis cut when\b", re.IGNORECASE), r"is cut when"),
    ("future-tense", re.compile(r"M[0-9]+\s*で再評価", re.IGNORECASE), r"M<N> で再評価"),
    ("future-tense", re.compile(r"Phase\s*[0-9]+\s*で実装", re.IGNORECASE), r"Phase <N> で実装"),
    ("future-tense", re.compile(r"Wave\s*[0-9]+\s*で対応", re.IGNORECASE), r"Wave <N> で対応"),
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

# Source-code file suffixes for which markdown-grammar exclusions (headings, quoted
# examples, backticked rule literals, fence tracking) do not apply. A quoted `Wave 6` in
# a `.md` rule doc is an example; a quoted `Wave 6` in a `.py` string literal is a
# user-visible string — exactly the site the rule targets. Scope is limited to the
# extension actually measured (`.py`). Broadening to "every non-markdown file" produces
# false positives against `eval/cases/*.yaml`, `eval/baseline/finish-task-5.baseline.yaml`,
# and `docs/wip/eval-workflow-scripts/run5-harness-fifth-evaluation.js`, which are
# structural pointers to skill sections, not commitments. Rust call sites the rule also
# names (`#[ignore]` reasons, panic messages) are not covered by this suffix set.
SOURCE_CODE_SUFFIXES = {".py"}


def uses_markdown_syntax(path: str) -> bool:
    """Return True when markdown-grammar exclusions apply to this file."""
    return Path(path).suffix.lower() not in SOURCE_CODE_SUFFIXES


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
# Files / patterns that describe the rule itself, not its application surface. Listed
# explicitly so that project-side `docs/` directories (e.g., `docs/adr/0001.md`) are
# still scanned — only the harness's own meta-docs are exempt.
_SELF_REFERENCE_RE = re.compile(
    r"""
    # Anchored to the true start of the (repo-relative) path, not "start or after any
    # slash" — the latter would also match a nested `.skillshare/skills/foo/SKILL.md`,
    # exempting a project-side skill that the rule must still cover.
    ^
    (?:
        # The script itself is full of forbidden literals as test patterns.
        scripts/check-future-plans\.py
      | # Its detection-power test carries the same fixtures by construction.
        eval/scripts/test_check_future_plans\.py
      | # Harness-only meta-docs that explain the rule and the harness architecture.
        # Listed as exact files so that adding new docs requires a conscious decision
        # rather than silently exempting whatever lands under `docs/`.
        docs/script-placement\.md
      | docs/harness-design\.md
      | docs/diagrams/README\.md
      | # Every skill defines its own internal Phase / Step / Wave vocabulary inside
        # SKILL.md / ATTRIBUTION.md — those are structure, not commitments. Limited to
        # the harness's own `skills/` layout (top-level), not project `.skillshare/skills/`
        # because project-side skills are still subject to the rule.
        skills/[^/]+/(?:SKILL|ATTRIBUTION)\.md
    )$
    """,
    re.VERBOSE,
)


@functools.lru_cache(maxsize=1)
def _repo_root() -> str | None:
    """Resolve the repository root once per process. None if git is unavailable or the
    cwd is not inside a git repo. Callers must fall back gracefully on None — this
    function must never raise or exit(), unlike `run_git`.
    """
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _to_repo_relative(path: str) -> str:
    """Normalize `path` to a repo-root-relative, forward-slash form.

    `_SELF_REFERENCE_RE` is anchored to the true start of the string, so an absolute
    path (as passed by `--files <absolute path>`, or a Windows drive-letter path with
    mixed separators) needs to be reduced to its repo-relative form before matching —
    otherwise every absolute-path invocation fails to match and the exemption silently
    stops applying. Falls back to the slash-normalized raw path when git is unavailable
    or the path resolves outside the repo root: that failure mode must not crash and
    must not become exempt, and since the regex requires an exact repo-root-relative
    prefix, an unresolved path simply fails to match and stays scanned (the safe
    default). Drive-letter case is compared case-insensitively; the rest of the path
    keeps its original case.
    """
    normalised = path.replace("\\", "/")
    root = _repo_root()
    if root is None:
        return normalised
    try:
        abs_path = str(Path(path).resolve()).replace("\\", "/")
        abs_root = str(Path(root).resolve()).replace("\\", "/")
    except OSError:
        return normalised
    if abs_path.lower() == abs_root.lower():
        return ""
    prefix = abs_root.lower() + "/"
    if abs_path.lower().startswith(prefix):
        return abs_path[len(prefix) :]
    return normalised


def is_self_reference(path: str) -> bool:
    """Return True if the file's job is to describe the rule (not be subject to it).

    Only the harness's own meta-docs (script-placement.md / harness-design.md /
    diagrams README), top-level `skills/*/SKILL.md` and `skills/*/ATTRIBUTION.md`,
    the script itself, and its detection-power test are exempt. Project-side `docs/`
    and project-side skills are still scanned, because that is where the rule
    actually needs to bite.
    """
    return _SELF_REFERENCE_RE.search(_to_repo_relative(path)) is not None


# Inline skill section refs like `Phase 3-1` / `Step 4-5` look like milestones but
# point at structural subsections of the skill itself. Always benign.
SECTION_REF_RE = re.compile(r"\b(?:Phase|Step|Section)\s+[0-9]+-[0-9A-Z]+\b")

# A forbidden literal wrapped in Japanese / English quotes is almost always a quoted
# example, not an actual commitment. Matching is broad: any quote pair around the line's
# match excerpt suffices.
QUOTED_EXAMPLE_RE = re.compile(
    r"""[「『"'`][^「『"'`]{0,80}(?:Wave\s+[0-9]+|Phase\s+[0-9]+|M[0-9]+|Sprint\s+[0-9]+)[^」』"'`]{0,80}[」』"'`]"""
)


def is_excluded_line(line: str, *, markdown_syntax: bool) -> bool:
    """Return True when the line is not a real violation site.

    `markdown_syntax=False` (source code, currently `.py`) skips `HEADING_RE`,
    `RULE_LITERAL_RE`, `Y_TRACE_ACCEPTING_RE`, `QUOTED_EXAMPLE_RE`, and the
    「除外」/「OK な」 heuristic — those five model markdown grammar (ATX headings,
    backtick-quoted rule literals, quote-pair examples). Applied to source, a leading
    `#` comment reads as a heading, a string literal reads as a quoted example, and a
    closing triple-quote reads as a closing quote: exactly the sites the rule names
    (comments, docstrings, panic messages) get deleted. `SECTION_REF_RE` (`Phase 3-1` / `Step 4-5`)
    stays active for every file — it is a doc-internal section pointer, language-neutral.
    No default value on `markdown_syntax`: a default would silently give future callers
    markdown behaviour on source files.
    """
    if markdown_syntax:
        if HEADING_RE.match(line):
            return True
        # Lines that *declare* the rule by listing forbidden patterns together (one
        # declarative line typically holds 2+ literal regex strings inside backticks).
        backtick_hits = RULE_LITERAL_RE.findall(line)
        if len(backtick_hits) >= 2:
            return True
        # Y-trace accepting: ... wave ... lines.
        if Y_TRACE_ACCEPTING_RE.search(line):
            return True
    # Section refs like `Phase 3-1` / `Step 4-5` — structural pointers, not commitments.
    # Active for every file: language-neutral, not markdown grammar.
    if SECTION_REF_RE.search(line):
        return True
    if markdown_syntax:
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


def scan_text(file: str, text: str) -> tuple[list[Violation], int]:
    """Scan the full text of a single file.

    Returns (violations, suppressed_count). `suppressed_count` counts only lines that
    actually matched a `PATTERNS` regex and got dropped by an exclusion — i.e. lines
    that WOULD have been reported as a violation — not every excluded line (most
    excluded lines, e.g. an ordinary heading, never matched anything to begin with and
    contribute 0). This is what lets the "OK" message distinguish "nothing was there"
    from "the exclusions ate it": a heading-only file still reports 0 suppressed.

    Getting that count means every line, excluded or not, still needs its PATTERNS
    search run (first-match-wins, same as the non-excluded path) instead of the old
    early `continue` on exclusion. The added cost is bounded — still one first-match
    scan per line — not a scan of all 16 patterns unconditionally.
    """
    out: list[Violation] = []
    suppressed = 0
    lines = text.splitlines()
    markdown = uses_markdown_syntax(file)
    # Fence tracking models a markdown convention (``` toggles a code block). Applied to
    # source, a stray ``` inside a docstring or comment would silence every line to EOF.
    fences = fence_state(lines) if markdown else [False] * len(lines)
    for idx, line in enumerate(lines):
        excluded = is_excluded_line(line, markdown_syntax=markdown) or fences[idx]
        for category, pattern, label in PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            if excluded:
                suppressed += 1
                break
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
    return out, suppressed


def run_git(args: list[str]) -> str:
    """Run a git command and return its stdout. Exit 2 on failure.

    `-c core.quotepath=false` disables git's default octal-escaping of non-ASCII path
    bytes in porcelain output (`"\\346\\227\\245..."` instead of `日本語.py`). Without it,
    `diff --name-only` / `ls-files --others` return an escaped string that never matches
    a real file on disk, so `file_content_working_tree()` reports it as missing and the
    file is skipped without a word — a non-ASCII violating file scans as clean.

    `encoding="utf-8"` is explicit because git writes path output as UTF-8 regardless of
    the OS locale; `subprocess.run(text=True)` without it decodes using the platform
    default (cp932 on this team's Windows machines), which raises `UnicodeDecodeError`
    on the very non-ASCII bytes `core.quotepath=false` was just told to stop escaping.
    """
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
    introduced relative to REF, not the merge-base view (three dots). The default
    (no --base) also includes untracked files via `git ls-files --others
    --exclude-standard`, because finish-task typically runs pre-commit when a
    brand-new doc is still untracked and would otherwise slip past the check.
    """
    if base:
        spec = [f"{base}..HEAD"]
        out = run_git(["diff", "--name-only", *spec])
        return [f for f in out.splitlines() if f.strip()]

    diff_out = run_git(["diff", "--name-only", "HEAD"])
    untracked_out = run_git(["ls-files", "--others", "--exclude-standard"])
    seen: set[str] = set()
    result: list[str] = []
    for line in (*diff_out.splitlines(), *untracked_out.splitlines()):
        f = line.strip()
        if f and f not in seen:
            seen.add(f)
            result.append(f)
    return result


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

    explicit_files = bool(args.files)
    targets = args.files if explicit_files else diff_files(args.base)

    findings: list[Violation] = []
    suppressed_total = 0
    for f in targets:
        if is_self_reference(f):
            continue
        content = file_content_working_tree(f)
        if content is None:
            # An explicit `--files` path that is missing or undecodable is an invocation
            # error, not a clean scan: an agent that mistypes a path currently gets exit
            # 0, which reads as "clean". `git diff`-derived targets legitimately include
            # deleted files, so that path stays silent.
            if explicit_files:
                print(f"error: cannot read file: {f}", file=sys.stderr)
                return 2
            continue
        file_findings, file_suppressed = scan_text(f, content)
        findings.extend(file_findings)
        suppressed_total += file_suppressed

    if args.json:
        print(json.dumps([asdict(v) for v in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            # "exclusions", not "markdown exclusions": for `.py` files the only active
            # exclusion is `SECTION_REF_RE` (language-neutral), so naming markdown
            # specifically would overstate the mechanism for non-markdown files.
            suffix = (
                f" ({suppressed_total} line(s) suppressed by exclusions)"
                if suppressed_total
                else ""
            )
            print(f"OK: no future-plans / milestone / Wave / Phase violations detected.{suffix}")
        for v in findings:
            print(f"{v.file}:{v.line}:{v.category}: {v.excerpt}  [pattern: {v.pattern}]")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
