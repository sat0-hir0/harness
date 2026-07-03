#!/usr/bin/env python3
"""Assemble a Claude Code plugin directory from this repo's skills/ + agents/.

The harness repo is distributed to individual machines via skillshare
(= cross-vendor sync layer). This script emits the *Claude-facing* artifact:
an official Claude Code plugin directory that an org can host in a
git-hosted marketplace and install / pin / update through the official
plugin machinery. The manifest layout follows the published schema at
https://code.claude.com/docs/en/plugins-reference (`.claude-plugin/plugin.json`,
skills auto-discovered under `skills/<name>/SKILL.md`, agents under `agents/*.md`).

Version source: the `VERSION` file at the repo root is the single source.
`git describe` is not used because (a) the repo carries no tags, so it fails
outright, (b) builds must reproduce identically outside a git checkout
(= zip export, CI cache), and (c) a version bump as a one-line file diff goes
through the same review discipline as any doc change. Standard library only.

Usage
-----
    python scripts/build-plugin.py           # build dist/claude-plugin/
    python scripts/build-plugin.py --zip     # also write dist/harness-plugin-<version>.zip
    python scripts/build-plugin.py --out DIR # build into DIR instead of dist/claude-plugin/

Exit codes
----------
    0   build succeeded and validated
    1   validation failure (missing SKILL.md, empty inputs, bad manifest)
    2   invocation error (missing VERSION, bad version string)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

# Force UTF-8 on stdout so tree output survives Windows cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "harness"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Never copy these into the artifact (caches, editor droppings, VCS internals).
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".*", "*.swp")


def read_version() -> str:
    version_file = REPO_ROOT / "VERSION"
    if not version_file.is_file():
        print(f"error: {version_file} not found", file=sys.stderr)
        sys.exit(2)
    version = version_file.read_text(encoding="utf-8").strip()
    if not VERSION_RE.match(version):
        print(f"error: VERSION must be MAJOR.MINOR.PATCH, got {version!r}", file=sys.stderr)
        sys.exit(2)
    return version


def build_manifest(version: str) -> dict:
    """Only fields recognized by the official schema, so that
    `claude plugin validate --strict` passes without warnings."""
    return {
        "name": PLUGIN_NAME,
        "version": version,
        "description": (
            "Universal AI-development harness: entry-point skills "
            "(task-routing / intent-clarify), slicing / status / completion "
            "workflow skills, and role-based subagents."
        ),
        "author": {"name": "sat0-hir0"},
        "repository": "https://github.com/sat0-hir0/harness",
        "keywords": ["harness", "skills", "agents", "workflow"],
    }


def copy_skills(dest: Path) -> list[str]:
    src = REPO_ROOT / "skills"
    names: list[str] = []
    for skill_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        if not (skill_dir / "SKILL.md").is_file():
            print(f"error: {skill_dir} has no SKILL.md", file=sys.stderr)
            sys.exit(1)
        shutil.copytree(skill_dir, dest / "skills" / skill_dir.name, ignore=IGNORE)
        names.append(skill_dir.name)
    return names


def copy_agents(dest: Path) -> list[str]:
    src = REPO_ROOT / "agents"
    (dest / "agents").mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for agent_md in sorted(src.glob("*.md")):
        shutil.copy2(agent_md, dest / "agents" / agent_md.name)
        names.append(agent_md.stem)
    return names


def validate(plugin_root: Path, skills: list[str], agents: list[str]) -> None:
    """Fail the build rather than ship a structurally broken plugin."""
    if not skills:
        print("error: no skills copied", file=sys.stderr)
        sys.exit(1)
    if not agents:
        print("error: no agents copied", file=sys.stderr)
        sys.exit(1)
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))  # raises on bad JSON
    if manifest.get("name") != PLUGIN_NAME:
        print(f"error: manifest name mismatch: {manifest.get('name')!r}", file=sys.stderr)
        sys.exit(1)
    for name in skills:
        skill_md = plugin_root / "skills" / name / "SKILL.md"
        head = skill_md.read_text(encoding="utf-8", errors="replace").lstrip()
        if not head.startswith("---"):
            print(f"error: {skill_md} lacks YAML frontmatter", file=sys.stderr)
            sys.exit(1)


def write_zip(plugin_root: Path, version: str) -> Path:
    """Zip the plugin so that extraction yields a single `harness/` plugin dir."""
    zip_path = plugin_root.parent / f"{PLUGIN_NAME}-plugin-{version}.zip"
    files = sorted(p for p in plugin_root.rglob("*") if p.is_file())
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            arcname = Path(PLUGIN_NAME) / f.relative_to(plugin_root)
            zf.write(f, arcname.as_posix())
    return zip_path


def print_tree(root: Path) -> None:
    print(f"{root}")
    entries = sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix())
    for p in entries:
        rel = p.relative_to(root)
        indent = "  " * len(rel.parts)
        suffix = "/" if p.is_dir() else ""
        print(f"{indent}{rel.name}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Claude Code plugin artifact.")
    parser.add_argument("--out", metavar="DIR", help="Output dir (default: dist/claude-plugin).")
    parser.add_argument("--zip", action="store_true", help="Also write a versioned zip next to the output dir.")
    args = parser.parse_args()

    version = read_version()
    plugin_root = Path(args.out).resolve() if args.out else REPO_ROOT / "dist" / "claude-plugin"

    if plugin_root.exists():
        shutil.rmtree(plugin_root)
    (plugin_root / ".claude-plugin").mkdir(parents=True)

    manifest = build_manifest(version)
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    skills = copy_skills(plugin_root)
    agents = copy_agents(plugin_root)
    validate(plugin_root, skills, agents)

    print(f"plugin  : {PLUGIN_NAME} v{version}")
    print(f"skills  : {len(skills)} ({', '.join(skills)})")
    print(f"agents  : {len(agents)} ({', '.join(agents)})")
    print_tree(plugin_root)

    if args.zip:
        zip_path = write_zip(plugin_root, version)
        print(f"zip     : {zip_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
