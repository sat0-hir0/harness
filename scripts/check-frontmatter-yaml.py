#!/usr/bin/env python3
"""Detect YAML frontmatter corruption in skill / agent `description:` fields.

Skill `SKILL.md` and agent `*.md` files carry a YAML frontmatter block whose
`description:` drives skill/agent triggering. When that value is written as an
unquoted plain scalar, certain characters silently break the YAML scan:

    * ` #` (space + hash) starts a YAML comment, truncating the description.
    * `: ` (colon + space) or a trailing `:` is read as a nested mapping,
      raising a ScannerError so the whole frontmatter fails to load.

Either way the description the author wrote is not the description that gets
loaded. This lint catches those cases and enforces a safe scalar style
(`>-` folded block, `|-` literal block, or quoted) so the field survives a
round-trip.

On top of parse safety, the lint enforces a length budget: descriptions render
into the vendor's skill / agent picker, which truncates at ~1,535 chars
(observed live 2026-07-03: task-routing at 1,684 chars was cut mid-sentence;
docs/wip/harness-evaluation-2026-07-02.md section 11.2). Lengths over 1,400
chars warn (exit 0, headroom shrinking); lengths at or past 1,535 fail,
because everything beyond the cap is silently dropped at render time.

Standard library is enough: the pre-push hook runs bare `python`, and a
lightweight per-line simulation is enough to flag the two failure modes without
reimplementing a full YAML parser. When PyYAML happens to be installed, the
length check loads the frontmatter with `yaml.safe_load` and measures the
description the loader actually yields (authoritative); otherwise it falls
back to the stdlib estimate, which mirrors YAML folding semantics.

Usage
-----
    python check-frontmatter-yaml.py                 # scan all skill + agent files
    python check-frontmatter-yaml.py --files a.md b.md   # only the listed files
    python check-frontmatter-yaml.py --json          # JSON output

Exit codes
----------
    0   no violations (warnings may still be printed)
    1   at least one violation found
    2   invocation error (bad args)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# PyYAML is optional: when present the length check measures the loaded
# description authoritatively; when absent the stdlib estimate below is used,
# so the bare-`python` pre-push hook keeps working without the dependency.
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# Force UTF-8 on stdout so Japanese / em-dash excerpts survive Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# Glob patterns for the default full scan. Relative to the repo root (the
# directory this script lives under, one level up from `scripts/`).
DEFAULT_GLOBS = ("skills/*/SKILL.md", "agents/*.md")

# Length budget for the loaded description, in chars. The live render cap was
# observed at ~1,535 chars (2026-07-03: task-routing's 1,684-char description
# was truncated mid-sentence in the deployed picker; see
# docs/wip/harness-evaluation-2026-07-02.md section 11.2). Warn above the soft
# budget so authors trim while there is still headroom; fail at the cap
# because chars past it are silently dropped at render time.
DESC_LENGTH_WARN_OVER = 1400  # warn when loaded length > this (exit 0)
DESC_LENGTH_FAIL_AT = 1535  # fail when loaded length >= this (exit 1)


@dataclass
class Violation:
    file: str
    line: int
    category: str  # see the five categories documented in main()'s help.
    excerpt: str
    detail: str
    severity: str = "error"  # "error" drives exit 1; "warning" prints, exit 0.


def repo_root() -> Path:
    """Return the repo root (parent of the `scripts/` dir holding this file)."""
    return Path(__file__).resolve().parent.parent


def collect_default_targets() -> list[str]:
    """Return the sorted list of skill + agent files for a full scan."""
    root = repo_root()
    out: list[str] = []
    for pattern in DEFAULT_GLOBS:
        out.extend(str(p) for p in sorted(root.glob(pattern)))
    return out


def read_text(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def extract_frontmatter(text: str) -> tuple[list[str], int] | None:
    """Return (frontmatter_lines, start_line_index) or None if no block.

    The frontmatter is the region between the first `---` (which must be the
    very first line) and the next `---`. `start_line_index` is the 0-based
    index of the opening `---` so callers can map back to file line numbers.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return lines[1:i], 0
    return None


def find_description(fm_lines: list[str]) -> tuple[int, str] | None:
    """Locate the `description:` key. Return (0-based index in fm_lines, value).

    The value is the text after `description:` on the same line, left-stripped.
    For block scalars (`>-` / `|-`) this is the indicator; for quoted / plain it
    is the raw scalar text.
    """
    for idx, line in enumerate(fm_lines):
        stripped = line.lstrip()
        if stripped.startswith("description:"):
            value = stripped[len("description:") :].lstrip()
            return idx, value
    return None


def _check_leading_indicator(value: str) -> tuple[str, str] | None:
    """Break checks that fire only at the very start of a plain scalar."""
    # Leading `#`: the whole scalar is read as a comment, so the value loads as
    # empty. A mid-scalar ` #` scan (which requires a preceding space) misses it.
    if value[0] == "#":
        snippet = value[:25]
        return (
            "description-truncated",
            f"plain scalar starts with '#' (...{snippet}...); "
            f"YAML reads the whole value as a comment, so 0 of {len(value)} "
            "chars survive",
        )
    # Leading `-` / `?` followed by whitespace or end-of-value is a
    # block-sequence / complex-mapping-key indicator, which raises a ScannerError
    # in this position.
    if value[0] in ("-", "?"):
        second = value[1] if len(value) > 1 else ""
        if second in (" ", "\t", ""):
            snippet = value[:25]
            return (
                "description-scanner-error",
                f"plain scalar starts with '{value[0]}{second}' "
                f"(...{snippet}...) which YAML reads as a sequence / mapping "
                "indicator (ScannerError)",
            )
    return None


def simulate_plain_scalar_breakage(
    value: str, is_first_line: bool = True
) -> tuple[str, str] | None:
    """Check whether a plain-scalar line would break the YAML scan.

    Returns (category, detail) if it would break, else None.

    `is_first_line` gates the leading-indicator checks (a leading `#` / `-` /
    `?` is only a node indicator at the very start of the scalar). On a folded
    continuation line those characters are ordinary content, so only the
    mid-scalar ` #` / `: ` scans apply.

    Failure modes, matching how a real YAML scanner reads a plain scalar:
      * A leading indicator char — when the value's FIRST char is one that YAML
        reserves at the start of a node. `#` starts a comment (the value loads
        as null/empty); `-` or `?` followed by whitespace/EOL is read as a
        block-sequence / mapping-key indicator (ScannerError). This is the
        first-char case that a mid-scalar scan misses.
      * ` #` — a hash preceded by whitespace begins a comment; everything from
        there on is dropped, silently truncating the value.
      * `: ` (colon + space) or a trailing `:` — read as a nested mapping,
        which is illegal in this position and raises a ScannerError.

    Backticks are NOT special in YAML, so they are not treated as quoting: a
    `: ` or ` #` inside backticks breaks exactly the same as outside.

    Both mid-scalar failure modes are located and the one that occurs FIRST
    (leftmost) is reported, because that is the point at which a real scanner
    stops reading the plain scalar: a ` #` before a `: ` truncates (the `: ` is
    never reached), while a `: ` before a ` #` raises the ScannerError first.
    A leading-indicator break is checked before both, since it fires at index 0.
    """
    if not value:
        return None

    # Leading-indicator checks apply only at the true start of the scalar.
    if is_first_line:
        leading = _check_leading_indicator(value)
        if leading is not None:
            return leading

    # Leftmost ` #` (whitespace + hash) — comment start, truncates the scalar.
    hash_pos: int | None = None
    for i in range(1, len(value)):
        if value[i] == "#" and value[i - 1] in (" ", "\t"):
            hash_pos = i
            break
    # Leftmost `: ` / trailing `:` — read as a nested mapping, ScannerError.
    colon_pos: int | None = None
    for i, ch in enumerate(value):
        if ch == ":":
            nxt = value[i + 1] if i + 1 < len(value) else ""
            if nxt in (" ", "\t", ""):
                colon_pos = i
                break

    if hash_pos is None and colon_pos is None:
        return None
    # Pick whichever break-point the scanner would hit first.
    truncates_first = colon_pos is None or (
        hash_pos is not None and hash_pos < colon_pos
    )
    if truncates_first:
        i = hash_pos  # type: ignore[assignment]
        kept = len(value[:i].rstrip())
        snippet = value[max(0, i - 12) : i + 13]
        return (
            "description-truncated",
            f"plain scalar truncated at ' #' near ...{snippet}...; "
            f"{kept} of {len(value)} chars survive",
        )
    i = colon_pos  # type: ignore[assignment]
    nxt = value[i + 1] if i + 1 < len(value) else ""
    snippet = value[max(0, i - 12) : i + 13]
    return (
        "description-scanner-error",
        f"plain scalar contains ':{nxt}' near ...{snippet}... "
        "which YAML reads as a nested mapping (ScannerError)",
    )


def check_block_scalar_indent(
    fm_lines: list[str], desc_idx: int
) -> str | None:
    """For a `>-` / `|-` block scalar, verify at least one indented body line.

    Returns a detail string if the block scalar has no indented continuation
    (an empty description), else None. Indentation integrity beyond presence is
    left to the YAML loader; this is a light sanity check.
    """
    for line in fm_lines[desc_idx + 1 :]:
        if line.strip() == "":
            continue
        # A body line must be more indented than the `description:` key. The key
        # sits at the frontmatter's base indent (0 for these files); any leading
        # space qualifies as a continuation line.
        if line[:1] in (" ", "\t"):
            return None
        # Hit a sibling key or end of block before any body line.
        break
    return "block scalar has no indented body (empty description)"


def collect_plain_scalar_continuations(
    fm_lines: list[str], desc_idx: int
) -> list[str]:
    """Gather the continuation lines of a multi-line plain scalar.

    A plain scalar may fold across several lines: the `description:` line holds
    the first chunk and each following indented, non-empty line adds more. YAML
    scans ` #` / `: ` on those continuation lines exactly as on the first line,
    so they must be inspected too — checking only the first line is a false
    negative for any dangerous character that lands on a wrapped line.

    Collection stops at the first sibling key (a line at the frontmatter's base
    indent, i.e. no leading whitespace) or end of the block. Blank lines end a
    plain scalar in YAML, so they stop collection as well.
    """
    out: list[str] = []
    for line in fm_lines[desc_idx + 1 :]:
        if line.strip() == "":
            break
        if line[:1] not in (" ", "\t"):
            break
        out.append(line.strip())
    return out


def collect_block_scalar_body(fm_lines: list[str], desc_idx: int) -> list[str]:
    """Gather the (stripped) body lines of a `>-` / `|-` block scalar.

    Blank lines are kept as empty strings — they are legal inside a block
    scalar and matter for folding — but trailing blanks are dropped, matching
    the `-` chomping indicator used in these files.
    """
    out: list[str] = []
    for line in fm_lines[desc_idx + 1 :]:
        if line.strip() == "":
            out.append("")
            continue
        if line[:1] not in (" ", "\t"):
            break
        out.append(line.strip())
    while out and out[-1] == "":
        out.pop()
    return out


def _yaml_loaded_description(fm_lines: list[str]) -> str | None:
    """Load the frontmatter with PyYAML and return the description it yields.

    Returns None when PyYAML is not installed, the block fails to parse, or
    the loaded description is not a string — callers then fall back to the
    stdlib estimate.
    """
    if yaml is None:
        return None
    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    desc = data.get("description")
    return desc if isinstance(desc, str) else None


def loaded_description_length(
    value: str, fm_lines: list[str], desc_idx: int
) -> int:
    """Char count of the description as YAML loads it.

    This is the length that counts against the render cap: what the loader
    yields, not what sits in the file. When PyYAML is installed the length is
    measured on the actually-loaded value; otherwise it is estimated per
    scalar style:

      * folded block (`>` / `>-`): adjacent body lines join with a single
        space; a run of k blank lines folds to exactly k newline chars,
        replacing the join space (YAML folds the break before a blank away).
      * literal block (`|` / `|-`): body lines join with newlines.
      * quoted: the surrounding quotes are dropped (single-line heuristic,
        matching check_quoted_symmetry).
      * plain: the first line joins its continuation lines with single spaces.
    """
    loaded = _yaml_loaded_description(fm_lines)
    if loaded is not None:
        return len(loaded)
    if value.startswith((">", "|")):
        body = collect_block_scalar_body(fm_lines, desc_idx)
        if value.startswith("|"):
            return len("\n".join(body))
        total = 0
        pending_blanks = 0
        first = True
        for line in body:
            if not line:
                pending_blanks += 1
                continue
            if not first:
                total += pending_blanks if pending_blanks else 1
            total += len(line)
            pending_blanks = 0
            first = False
        return total
    if value[:1] in ("'", '"'):
        body = value.rstrip()
        if len(body) >= 2 and body[-1] == body[0]:
            return len(body) - 2
        return max(len(body) - 1, 0)
    parts = [value, *collect_plain_scalar_continuations(fm_lines, desc_idx)]
    return len(" ".join(p for p in parts if p))


def check_description_length(
    path: str, file_line: int, excerpt: str, length: int
) -> list[Violation]:
    """Apply the length budget. Returns a fail / warn Violation or nothing."""
    if length >= DESC_LENGTH_FAIL_AT:
        return [
            Violation(
                file=path,
                line=file_line,
                category="description-over-length",
                excerpt=excerpt,
                detail=(
                    f"description loads as {length} chars, at or past the "
                    f"observed live render cap of {DESC_LENGTH_FAIL_AT} chars "
                    "(2026-07-03: a 1,684-char description was truncated "
                    "mid-sentence in the deployed picker); everything past "
                    "the cap is silently dropped — trim the description"
                ),
            )
        ]
    if length > DESC_LENGTH_WARN_OVER:
        return [
            Violation(
                file=path,
                line=file_line,
                category="description-over-length",
                excerpt=excerpt,
                detail=(
                    f"description loads as {length} chars, over the "
                    f"{DESC_LENGTH_WARN_OVER}-char budget and within "
                    f"{DESC_LENGTH_FAIL_AT - length} chars of the observed "
                    f"live render cap ({DESC_LENGTH_FAIL_AT}); trim before "
                    "it truncates"
                ),
                severity="warning",
            )
        ]
    return []


def check_quoted_symmetry(value: str) -> str | None:
    """For a quoted scalar, verify the closing quote is present on the line.

    Returns a detail string if the quote looks unbalanced, else None. This is a
    single-line heuristic; multi-line quoted scalars are uncommon here.
    """
    quote = value[0]
    body = value[1:]
    # Strip a trailing comment for the check — quoted scalars may be followed by
    # ` # comment`, though that is unusual in this frontmatter.
    if not body.rstrip().endswith(quote):
        return f"quoted scalar opened with {quote} but no matching close on the line"
    return None


def scan_file(path: str) -> list[Violation]:
    """Scan one file's frontmatter description. Return any violations."""
    text = read_text(path)
    if text is None:
        return []
    fm = extract_frontmatter(text)
    if fm is None:
        return [
            Violation(
                file=path,
                line=1,
                category="frontmatter-missing",
                excerpt=(text.splitlines()[0] if text.splitlines() else ""),
                detail="no '---' ... '---' frontmatter block at the top of the file",
            )
        ]
    fm_lines, _ = fm
    found = find_description(fm_lines)
    if found is None:
        return [
            Violation(
                file=path,
                line=1,
                category="description-missing",
                excerpt="",
                detail="frontmatter has no 'description:' key",
            )
        ]
    desc_idx, value = found
    file_line = desc_idx + 2  # +1 for the opening '---', +1 for 1-based.
    excerpt = f"description: {value}"[:200]

    if value == "":
        # Bare `description:` with nothing after it — either an empty value or a
        # block scalar with no indicator. Empty => missing.
        detail = check_block_scalar_indent(fm_lines, desc_idx)
        if detail is not None:
            return [
                Violation(path, file_line, "description-missing", excerpt, detail)
            ]
    elif value.startswith((">", "|")):
        detail = check_block_scalar_indent(fm_lines, desc_idx)
        if detail is not None:
            return [
                Violation(path, file_line, "description-missing", excerpt, detail)
            ]
    elif value[0] in ("'", '"'):
        detail = check_quoted_symmetry(value)
        if detail is not None:
            return [
                Violation(
                    path, file_line, "description-scanner-error", excerpt, detail
                )
            ]
    else:
        # Plain scalar (possibly multi-line): fold the first line together with
        # any continuation lines and simulate breakage over each. A ` #` or
        # `: ` on a wrapped line breaks the scan just as it would on the first
        # line, so checking only `value` would be a false negative.
        continuations = collect_plain_scalar_continuations(fm_lines, desc_idx)
        for offset, chunk in enumerate([value, *continuations]):
            result = simulate_plain_scalar_breakage(
                chunk, is_first_line=(offset == 0)
            )
            if result is not None:
                category, detail = result
                chunk_line = file_line + offset
                chunk_excerpt = excerpt if offset == 0 else chunk[:200]
                return [
                    Violation(path, chunk_line, category, chunk_excerpt, detail)
                ]

    # Parse checks passed — the description loads as written. Now enforce the
    # length budget against what the loader yields (the rendered length).
    length = loaded_description_length(value, fm_lines, desc_idx)
    return check_description_length(path, file_line, excerpt, length)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect YAML frontmatter description corruption and over-length "
            "descriptions in skill / agent files. "
            "Categories: description-truncated (plain scalar cut at ' #'), "
            "description-scanner-error (plain scalar with ': ' read as a mapping), "
            "description-missing (no / empty description), "
            "frontmatter-missing (no '---' block), "
            f"description-over-length (warn > {DESC_LENGTH_WARN_OVER} chars, "
            f"fail >= {DESC_LENGTH_FAIL_AT} chars = observed live render cap). "
            "Fix parse breaks by switching description to a '>-' folded block "
            "scalar; fix length by trimming the description."
        ),
    )
    parser.add_argument(
        "--files",
        nargs="+",
        metavar="PATH",
        help="Scan only these files (ignores the default skill + agent glob).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON.",
    )
    args = parser.parse_args()

    targets = args.files if args.files else collect_default_targets()

    findings: list[Violation] = []
    for f in targets:
        findings.extend(scan_file(f))

    errors = [v for v in findings if v.severity == "error"]

    if args.json:
        print(json.dumps([asdict(v) for v in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: all frontmatter descriptions load cleanly and fit the length budget.")
        elif not errors:
            print("OK: descriptions load cleanly; length warnings below (not blocking).")
        for v in findings:
            prefix = "warning: " if v.severity == "warning" else ""
            print(f"{prefix}{v.file}:{v.line}:{v.category}: {v.excerpt}")
            print(f"    -> {v.detail}")

    # Warnings print but do not block; only errors flip the exit code.
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
