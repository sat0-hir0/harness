#!/usr/bin/env python3
"""Verify eval case `source:` citations resolve to a real SKILL.md anchor.

Sister guard to lint-agent-refs.py (Issue #81 drift). Each eval case in
`eval/cases/*.yaml` carries a `source:` field citing the SKILL.md section it
was extracted from (e.g. `skills/task-routing/SKILL.md Example 3`). Nothing
previously checked that citation against the actual file, so a SKILL.md
header rename or removal silently strands the case source with no signal.
This script re-derives the header set from each cited SKILL.md and confirms
every anchor segment in the citation still resolves to one of them.

Source citation format: `<path> <anchor>`, where `<path>` is the first
whitespace token (e.g. `skills/task-routing/SKILL.md`) and `<anchor>` is the
remainder. An anchor may cite multiple sections separated by ` / ` (e.g.
`Use when / Phase 3`); every segment must resolve for the source to pass.
Standard library only (no PyYAML, no eval_common — pre-push runs bare
python), so case files are line-scanned with a regex rather than parsed as
YAML.

Usage
-----
    python scripts/check-case-source.py                 # scan eval/cases/*.yaml
    python scripts/check-case-source.py --files PATH...  # scan a subset
    python scripts/check-case-source.py --json           # JSON output

Exit codes
----------
    0   no violations
    1   at least one violation found
    2   invocation error (no eval/cases dir, bad --files path)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

# Force UTF-8 on stdout so that Japanese / em-dash / etc. survive Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# `source: "..."` line in a case yaml (double-quoted scalar, one line).
SOURCE_RE = re.compile(r'^\s*source:\s*"(.+)"\s*$')

# ATX header (`## Title`, `### Sub`), levels 2-6. Group 1 is the header text.
HEADER_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$")

# Trailing bracketed aside on a segment, e.g. "Phase 3 (yes 確認)" -> "Phase 3".
# Matches both ASCII "(" and full-width "（" through end of string.
TRAILING_ASIDE_RE = re.compile(r"\s*[（(].*$")

# Range anchor: "Phase <start>-<end>" (e.g. "Phase 1-3") -> endpoints. Phase
# only — a "Step <n>-<m>" token is a Step's own ID (a "<phase>-<step>" pair),
# not a range, so it must NOT be expanded here (see LABEL_TOKEN_RE below).
RANGE_RE = re.compile(r"^Phase\s+(\d+)-(\d+)$")

# A single label token: "Phase <n>" or "Step <n>-<m>" (Step IDs are
# "<phase>-<step>" pairs, e.g. "Step 4-5", not a range to expand).
LABEL_TOKEN_RE = re.compile(r"(?:Phase|Step)\s+\d+(?:-\d+)?")


@dataclass
class Violation:
    file: str
    line: int
    source: str
    segment: str
    category: str  # "file-missing" | "anchor-unresolved"


def normalize(s: str) -> str:
    """NFKC-normalize, trim, and collapse internal whitespace runs."""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s.strip())
    return s


def target_files(explicit: list[str] | None) -> list[Path]:
    """Collect the case yaml files to scan."""
    if explicit:
        return [Path(p) for p in explicit]
    return sorted((REPO_ROOT / "eval" / "cases").glob("*.yaml"))


def extract_headers(skill_md: Path) -> set[str]:
    """Return the normalized set of ATX header texts in a SKILL.md."""
    headers: set[str] = set()
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        m = HEADER_RE.match(line)
        if m:
            headers.add(normalize(m.group(1)))
    return headers


def expand_segment(raw: str) -> list[list[str]]:
    """Strip a trailing bracketed aside and expand a range/compound anchor.

    Returns a list of resolution groups that must ALL resolve (AND); each
    group is itself a list of candidate strings where ANY one resolving is
    enough (OR).

    "Phase 3 (yes 確認)"  -> [["Phase 3"]]
    "Phase 1-3"           -> [["Phase 1"], ["Phase 3"]]     (Phase range, AND)
    "Phase 4 Step 4-5"    -> [["Phase 4"], ["Step 4-5"]]    (compound, AND)

    A "Phase <n>-<m>" range must resolve both endpoints. A compound segment
    that names 2+ "Phase <n>" / "Step <n>-<m>" label tokens (a Step's own ID
    is a "<phase>-<step>" pair, not a range) must resolve EVERY token it
    names — otherwise a rename that drops only the Step half of a compound
    citation (e.g. "Step 4-5" -> "Step 4-6") would silently pass because the
    Phase half still resolves. A segment with at most one label token
    resolves as a single group (the whole string, e.g. free text like
    "Use when", or a lone "Phase 3" / "Step 3-2").
    """
    seg = TRAILING_ASIDE_RE.sub("", raw).strip()
    m = RANGE_RE.match(seg)
    if m:
        start, end = m.groups()
        return [[normalize(f"Phase {start}")], [normalize(f"Phase {end}")]]
    tokens = LABEL_TOKEN_RE.findall(seg)
    if len(tokens) >= 2:
        return [[normalize(tok)] for tok in tokens]
    return [[normalize(seg)]]


def segment_resolves(seg: str, headers: set[str]) -> bool:
    """Return True when a normalized anchor segment resolves to a header.

    A header resolves a segment when it is exactly equal, or extends the
    segment with a `:` or space separator (headers commonly carry a title
    suffix or a bracketed aside, e.g. "Phase 3: Restate" resolves "Phase
    3"). No other prefix match is allowed: a bare `header.startswith(seg)`
    would let a rename like "Example 3" -> "Example 3X" slip through
    undetected, since "X" is not a real section boundary.
    """
    for header in headers:
        if header == seg:
            return True
        if header.startswith(seg + ":") or header.startswith(seg + " "):
            return True
    return False


def check_source(raw_source: str, file: str, line: int) -> list[Violation]:
    """Validate one `source:` citation and return any violations found."""
    parts = raw_source.split(None, 1)
    if not parts:
        return [Violation(file, line, raw_source, "", "file-missing")]
    path_token = parts[0]
    anchor = parts[1] if len(parts) > 1 else ""

    skill_md = REPO_ROOT / path_token
    if not skill_md.is_file():
        return [Violation(file, line, raw_source, path_token, "file-missing")]

    headers = extract_headers(skill_md)
    violations: list[Violation] = []
    for raw_segment in anchor.split(" / "):
        raw_segment = raw_segment.strip()
        if not raw_segment:
            continue
        for group in expand_segment(raw_segment):
            if not any(segment_resolves(candidate, headers) for candidate in group):
                violations.append(
                    Violation(file, line, raw_source, group[0], "anchor-unresolved")
                )
    return violations


def scan_file(path: Path) -> list[Violation]:
    """Scan one eval case yaml for source citations and validate each."""
    try:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    out: list[Violation] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = SOURCE_RE.match(line)
        if not m:
            continue
        out.extend(check_source(m.group(1), rel, idx))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that every eval case `source:` citation resolves to a real "
            "skills/<name>/SKILL.md file and an existing section anchor."
        ),
    )
    parser.add_argument(
        "--files",
        nargs="+",
        metavar="PATH",
        help="Scan only these case yaml files (default: eval/cases/*.yaml).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON.",
    )
    args = parser.parse_args()

    paths = target_files(args.files)
    if not paths:
        print("error: no case files to scan", file=sys.stderr)
        return 2
    for p in paths:
        if not p.is_file():
            print(f"error: {p} is not a file", file=sys.stderr)
            return 2

    findings: list[Violation] = []
    for path in paths:
        findings.extend(scan_file(path))

    if args.json:
        print(json.dumps([asdict(v) for v in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print(f"OK: all source citations resolve across {len(paths)} case files.")
        for v in findings:
            print(f"{v.file}:{v.line}:{v.category}: {v.source}")
            print(f"    -> {v.segment}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
