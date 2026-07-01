#!/usr/bin/env python3
"""Gate a git push on eval regression for the skills / agents it touches.

Invoked from `lefthook.yml` as the `pre-push` hook. Reads the push plan on
stdin (git's `<local_ref> <local_sha> <remote_ref> <remote_sha>` lines),
computes the set of files the push introduces, and maps them to eval targets:
`skills/<name>/SKILL.md` runs that skill's regression, and any `agents/*.md`
change fans out to `--skill all`. Each target runs `eval-regression.py`; a
non-zero exit (drift or missing baseline) blocks the push. Standard library
only.

Usage
-----
    python eval-gate.py                    # read git pre-push lines from stdin
    python eval-gate.py --range A..B       # manual verification of one range

Exit codes
----------
    0   no skill/agent changes, or all targets clean
    1   at least one target reports drift / missing baseline (push blocked)
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

# Force UTF-8 on stdout so that Japanese / em-dash / etc. survive Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# git reports paths with `/` separators regardless of OS.
SKILL_RE = re.compile(r"skills/([^/]+)/SKILL\.md$")
AGENT_RE = re.compile(r"agents/.+\.md$")


def is_all_zero(sha: str) -> bool:
    """Return True for git's all-zero SHA (branch create / delete sentinel).

    Uses `set(sha) == {"0"}` so it is object-format agnostic (SHA-1 vs SHA-256
    differ in length but both are all-zero when git means "no object").
    """
    return bool(sha) and set(sha) == {"0"}


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command, capturing stdout/stderr. Never raises on non-zero."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def all_tracked_files() -> list[str]:
    """Return every tracked file (fallback when no merge-base exists)."""
    proc = run_git(["ls-files"])
    return [f for f in proc.stdout.splitlines() if f.strip()]


def diff_files(base: str, tip: str) -> list[str]:
    """Return files changed between base and tip (`git diff --name-only`).

    Deletions are excluded (`--diff-filter=d`): a removed `skills/x/SKILL.md`
    has no cases to evaluate, so mapping it to a target would make a legitimate
    skill removal fail on the missing baseline it can no longer satisfy.
    """
    proc = run_git(["diff", "--name-only", "--diff-filter=d", f"{base}..{tip}"])
    if proc.returncode != 0:
        # A bad range yields an empty set so the gate stays permissive rather
        # than blocking on a diff failure the user cannot act on, but log it so
        # the skip is visible rather than silent.
        print(
            f"eval-gate: warning: git diff {base}..{tip} failed; "
            f"range not evaluated ({proc.stderr.strip()})",
            file=sys.stderr,
        )
        return []
    return [f for f in proc.stdout.splitlines() if f.strip()]


def merge_base(a: str, b: str) -> str | None:
    """Return the merge-base of two refs, or None if git cannot find one."""
    proc = run_git(["merge-base", a, b])
    if proc.returncode != 0:
        return None
    base = proc.stdout.strip()
    return base or None


def files_for_ranges(ranges: list[tuple[str, str]]) -> set[str]:
    """Collect the union of changed files across every (base, tip) range."""
    changed: set[str] = set()
    for base, tip in ranges:
        changed.update(diff_files(base, tip))
    return changed


def ranges_from_stdin(lines: list[str]) -> list[tuple[str, str]]:
    """Turn git pre-push stdin lines into (base, tip) ranges.

    Each line is `<local_ref> <local_sha> <remote_ref> <remote_sha>`.
    - local all-zero  -> branch deletion push, skipped.
    - remote all-zero -> new branch; base = merge-base(local, origin/main),
      falling back to every tracked file when no merge-base exists.
    - otherwise        -> base = remote_sha.
    """
    ranges: list[tuple[str, str]] = []
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if is_all_zero(local_sha):
            continue  # deleting a remote branch; nothing to evaluate
        if is_all_zero(remote_sha):
            base = merge_base(local_sha, "origin/main")
            if base is None:
                # No shared history (fresh repo): evaluate against every tracked
                # file by using the empty tree as base.
                empty_tree = run_git(["hash-object", "-t", "tree", "/dev/null"])
                base = empty_tree.stdout.strip() or None
            if base is None:
                # Even the empty-tree probe failed; treat all tracked files as
                # changed so the gate errs toward running.
                ranges.append(("__ALL__", local_sha))
                continue
            ranges.append((base, local_sha))
        else:
            ranges.append((remote_sha, local_sha))
    return ranges


def changed_files(ranges: list[tuple[str, str]]) -> set[str]:
    """Resolve ranges to a file set, honoring the __ALL__ fallback sentinel."""
    changed: set[str] = set()
    real_ranges: list[tuple[str, str]] = []
    for base, tip in ranges:
        if base == "__ALL__":
            changed.update(all_tracked_files())
        else:
            real_ranges.append((base, tip))
    changed.update(files_for_ranges(real_ranges))
    return changed


def targets_for(files: set[str]) -> list[str]:
    """Map a changed-file set to eval-regression targets.

    Any `agents/*.md` change fans out to `["all"]`. Otherwise, return the
    sorted set of skills whose `SKILL.md` changed.
    """
    skills: set[str] = set()
    agent_changed = False
    for f in files:
        m = SKILL_RE.match(f)
        # Only target skills whose directory still exists; a name coming from a
        # tracked-file fallback for a removed skill has no cases to check.
        if m and (REPO_ROOT / "skills" / m.group(1)).is_dir():
            skills.add(m.group(1))
        if AGENT_RE.match(f):
            agent_changed = True
    if agent_changed:
        return ["all"]
    return sorted(skills)


def run_regression(target: str) -> subprocess.CompletedProcess[str]:
    """Run eval-regression.py for one target (no judge)."""
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval" / "scripts" / "eval-regression.py"),
            "--skill",
            target,
        ],
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Block a git push when its skill/agent changes drift from the eval "
            "baseline. Reads git pre-push lines on stdin; --range is for manual "
            "verification."
        ),
    )
    parser.add_argument(
        "--range",
        metavar="A..B",
        help="Evaluate the files changed in A..B instead of reading stdin.",
    )
    args = parser.parse_args()

    stdin_lines = []
    if sys.stdin is not None and not sys.stdin.isatty():
        stdin_lines = [ln for ln in sys.stdin.read().splitlines() if ln.strip()]

    if stdin_lines:
        ranges = ranges_from_stdin(stdin_lines)
    elif args.range:
        if ".." not in args.range:
            print(f"error: --range expects A..B, got {args.range!r}", file=sys.stderr)
            return 1
        base, tip = args.range.split("..", 1)
        ranges = [(base.strip() or "origin/main", tip.strip() or "HEAD")]
    else:
        print("no push range (empty stdin and no --range); skip")
        return 0

    files = changed_files(ranges)
    targets = targets_for(files)
    if not targets:
        print("no skill/agent changes in push range; skip")
        return 0

    print(f"eval-gate: running regression for target(s): {', '.join(targets)}")
    failures: list[str] = []
    for t in targets:
        proc = run_regression(t)
        if proc.stdout.strip():
            print(proc.stdout.rstrip())
        # rc != 0 covers both drift/missing baseline (exit 1) and the
        # invocation error (exit 2) that eval-regression.py raises on a bad
        # case file; both must block the push.
        if proc.returncode != 0:
            detail = proc.stderr.strip() or f"eval-regression.py --skill {t} exited {proc.returncode}"
            failures.append(f"[{t}] {detail}")

    if failures:
        print("eval-gate: push blocked by baseline drift / missing baseline", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print(
            "Update the baseline (eval-baseline.py) after the change is correct, "
            "or resolve the drift, before pushing.",
            file=sys.stderr,
        )
        return 1

    print("eval-gate: no drift from baseline; push allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
