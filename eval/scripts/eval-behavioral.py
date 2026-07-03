#!/usr/bin/env python3
"""eval-behavioral.py — L2 verdict-contract runner (= `claude -p` の薄い wrapper)。

docs/wip/test-strategy-2026-07-02.md §4/§5 の実体。 task-routing の判定行から
verdict ∈ {Lead-direct, delegate-single, delegate-slice} のみを抽出して assert する。
fixture-sync lint (= eval-run / eval-regression) とは別物: こちらは skill を
**実際に headless 実行** する。 標準ライブラリ + PyYAML のみ (= eval_common を再利用)。

trial の状態は 3 値で区別する:
  - verdict         判定行から verdict を抽出できた
  - no-verdict-line skill は発火したが判定行が見つからない (= extraction-fail)
  - trigger-fail    Skill tool_use event が観測されなかった (= 発火せず)

pass 基準: N trial (既定 3) の多数決 verdict == expected。 最多 tie (= 3 値割れ含む)
は fail。 run set 冒頭に smoke assertion (= 先頭 case で Skill tool_use を 1 回観測)
を置き、 通過しない場合は trial を数えず exit 2 で止まる。

前提条件 (= skill 読込): `--setting-sources project` で個人 ~/.claude を排除するが、
task-routing は user scope にしか配布されないため、 repo 直下に project scope の
junction を用意する (= .claude/skills -> skills)。 本 runner が実行前に自動作成する。
詳細は eval/README.md の「L2 behavioral eval」節。

使い方:
  python eval-behavioral.py --skill task-routing                 # cases + holdout, N=3
  python eval-behavioral.py --skill task-routing --no-holdout
  python eval-behavioral.py --skill task-routing --case 3 --trials 5
  python eval-behavioral.py --skill task-routing --sonnet        # 深掘り用 opt-in
  python eval-behavioral.py --compare old.yaml new.yaml          # run set 同士の verdict diff

exit code: 0 = 全 case pass (compare: majority 差分なし) / 1 = fail あり (compare: 差分あり)
           / 2 = 前提条件エラー (smoke fail / junction 不可 / compare: model・CLI・trials
                 不一致、 NEW 側の case 欠落 = partial run)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

import eval_common as ec

REPO_ROOT = ec.EVAL_ROOT.parent
HOLDOUT_DIR = ec.EVAL_ROOT / "holdout"
DEFAULT_OUT_DIR = ec.EVAL_ROOT / "behavioral-baseline"

# --- 再現性の固定 (= 戦略 §4) ----------------------------------------------
# model は必ず明示する (= 本環境の headless 既定 model は haiku ではない)。
MODEL_DEFAULT = "claude-haiku-4-5"   # 既定。 run set 記録に echo される
MODEL_SONNET = "claude-sonnet-5"     # 深掘り用 opt-in (--sonnet)
PINNED_CLI_VERSION = "2.1.195"       # 検証済み CLI version。 不一致は warning + 記録

VERDICTS = ("Lead-direct", "delegate-single", "delegate-slice")
# 抽出規約: `判定:\s*(Lead-direct|delegate-single|delegate-slice)`。
# markdown 太字 (= `**判定**:`) と全角コロンを許容する superset。 直後の size 表記や
# `|` 以降のテキストは regex が自然に無視する。
VERDICT_RE = re.compile(
    r"判定\**\s*[:：]\s*\**\s*(Lead-direct|delegate-single|delegate-slice)"
)

# tool scope: skill 発火に必要な Skill のみ許可し、 副作用系は明示 block する。
ALLOWED_TOOLS = "Skill"
DISALLOWED_TOOLS = "Bash,Edit,Write,NotebookEdit,Task,WebFetch,WebSearch"


# --- 前提条件 ---------------------------------------------------------------
def find_claude() -> str:
    exe = shutil.which("claude")
    if exe:
        return exe
    fallback = Path.home() / ".local" / "bin" / ("claude.exe" if os.name == "nt" else "claude")
    if fallback.exists():
        return str(fallback)
    ec.eprint("ERROR: claude CLI not found on PATH")
    sys.exit(2)


def cli_version(claude_exe: str) -> str:
    out = subprocess.run(
        [claude_exe, "--version"], capture_output=True, text=True, timeout=60
    ).stdout.strip()
    # 例: "2.1.195 (Claude Code)" -> "2.1.195"
    return out.split()[0] if out else "unknown"


def ensure_project_skills(repo_root: Path) -> None:
    """project scope の skill source を junction で用意する (= 戦略 §4 の前提条件)。

    `--setting-sources project` は <cwd>/.claude/skills しか読まない。 harness repo に
    .claude/ は無い (= task-routing は user scope 配布のみ) ため、 repo の skills/ を
    .claude/skills に junction する。 repo の編集中 SKILL.md がそのまま読まれ、 個人
    skill 排除の目的も保たれる。 .claude/ は commit しない (= .gitignore 済)。
    """
    link = repo_root / ".claude" / "skills"
    target = repo_root / "skills"
    if link.exists():
        return
    if not target.is_dir():
        ec.eprint(f"ERROR: skills dir not found: {target}")
        sys.exit(2)
    link.parent.mkdir(exist_ok=True)
    try:
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True, capture_output=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)
    except (OSError, subprocess.CalledProcessError) as e:
        ec.eprint(f"ERROR: failed to create junction {link} -> {target}: {e}")
        sys.exit(2)
    print(f"created junction: {link} -> {target}")


# --- case 読込 ---------------------------------------------------------------
def load_case_file(path: Path, skill: str) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    cases = (data or {}).get("cases", [])
    errs: list[str] = []
    ids = [c.get("id") for c in cases]
    if ids != sorted(ids):
        errs.append(f"{path}: case ids not in ascending order: {ids}")
    for c in cases:
        errs.extend(ec.validate_case(skill, c))
        if c.get("expected_output", {}).get("verdict") not in VERDICTS:
            errs.append(f"{path} case {c.get('id')}: expected_output.verdict missing or invalid")
    if errs:
        for e in errs:
            ec.eprint("ERROR:", e)
        sys.exit(2)
    return cases


# --- trial 実行 ---------------------------------------------------------------
def run_trial(claude_exe: str, model: str, prompt: str, skill: str,
              budget_usd: float, timeout_s: int) -> dict:
    cmd = [
        claude_exe, "-p", prompt,
        "--model", model,
        "--setting-sources", "project",
        "--output-format", "stream-json",
        "--verbose",
        "--max-budget-usd", str(budget_usd),
        "--allowed-tools", ALLOWED_TOOLS,
        "--disallowed-tools", DISALLOWED_TOOLS,
        "--strict-mcp-config",
    ]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {"state": "error", "verdict": None, "cost_usd": None,
                "duration_s": round(time.monotonic() - t0, 1), "detail": "timeout"}

    triggered = False
    texts: list[str] = []
    cost = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                btype = block.get("type")
                if btype == "tool_use" and block.get("name") == "Skill":
                    if skill in json.dumps(block.get("input", {}), ensure_ascii=False):
                        triggered = True
                elif btype == "text":
                    texts.append(block.get("text", ""))
        elif ev.get("type") == "result":
            cost = ev.get("total_cost_usd")
            if ev.get("result"):
                texts.append(str(ev["result"]))

    duration = round(time.monotonic() - t0, 1)
    if proc.returncode != 0 and not texts:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        return {"state": "error", "verdict": None, "cost_usd": cost,
                "duration_s": duration, "detail": f"exit {proc.returncode}: {detail}"}

    m = VERDICT_RE.search("\n".join(texts))
    if not triggered:
        return {"state": "trigger-fail", "verdict": None, "cost_usd": cost,
                "duration_s": duration}
    if not m:
        return {"state": "no-verdict-line", "verdict": None, "cost_usd": cost,
                "duration_s": duration}
    return {"state": "verdict", "verdict": m.group(1), "cost_usd": cost,
            "duration_s": duration}


def trial_label(t: dict) -> str:
    return t["verdict"] if t["state"] == "verdict" else t["state"]


def judge_case(trials: list[dict], expected: str) -> tuple[str, dict, str]:
    """(result, tally, majority_label) を返す。 最多 tie は fail (= 3 値割れ含む)。"""
    tally = Counter(trial_label(t) for t in trials)
    ranked = tally.most_common()
    top_count = ranked[0][1]
    tied = [label for label, n in ranked if n == top_count]
    if len(tied) > 1:
        return "fail", dict(tally), "split"
    majority = tied[0]
    return ("pass" if majority == expected else "fail"), dict(tally), majority


# --- run set ------------------------------------------------------------------
def unique_out_path(path: Path) -> Path:
    """既存 run set を silent overwrite しない出力先を返す。

    同日に before/after workflow を回すと既定パス (= <skill>-YYYY-MM-DD.yaml) が
    衝突し、 変更後 run が変更前 baseline を置換して --compare 用の OLD が消える。
    存在時は -2, -3, ... の数値 suffix を付けて回避する。
    """
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"no unused suffix found for {path}")


def run_set(args: argparse.Namespace) -> int:
    claude_exe = find_claude()
    version = cli_version(claude_exe)
    if version != PINNED_CLI_VERSION:
        ec.eprint(f"WARNING: CLI version {version} != pinned {PINNED_CLI_VERSION} "
                  "(run set は記録されるが、 version 不一致の run set 同士の compare は拒否される)")
    ensure_project_skills(REPO_ROOT)

    model = MODEL_SONNET if args.sonnet else MODEL_DEFAULT
    skill = args.skill

    targets: list[tuple[str, dict]] = []
    if not args.holdout_only:
        for c in load_case_file(ec.CASES_DIR / f"{skill}.yaml", skill):
            targets.append(("cases", c))
    if not args.no_holdout:
        for c in load_case_file(HOLDOUT_DIR / f"{skill}.yaml", skill):
            targets.append(("holdout", c))
    if args.case is not None:
        targets = [(src, c) for src, c in targets if c["id"] == args.case]
    if not targets:
        ec.eprint("ERROR: no cases matched")
        return 2

    # smoke assertion: 先頭 case で Skill tool_use を 1 回観測するまで trial を数えない。
    # 発火自体に観測 noise がある (= haiku が稀に skill を呼ばず直答する) ため、
    # 上限 3 回まで再試行する。 3 連続 trigger-fail は環境問題 (junction / auth) とみなす。
    smoke_prompt = targets[0][1]["input"]
    print(f"smoke: model={model} cli={version} prompt={smoke_prompt[:60]!r}")
    total_cost = 0.0
    smoke = None
    for attempt in range(1, 4):
        smoke = run_trial(claude_exe, model, smoke_prompt, skill,
                          args.budget_usd, args.timeout)
        total_cost += smoke.get("cost_usd") or 0.0
        if smoke["state"] not in ("trigger-fail", "error"):
            break
        ec.eprint(f"smoke attempt {attempt}/3: {smoke['state']} "
                  f"({smoke.get('detail', 'Skill tool_use not observed')})")
    if smoke["state"] in ("trigger-fail", "error"):
        ec.eprint("ERROR: smoke assertion failed 3 times; "
                  "junction / skill 配置 / auth を確認してから再実行する。")
        return 2
    print(f"smoke: ok ({smoke['state']}, {smoke['duration_s']}s, ${smoke.get('cost_usd')})")

    results = []
    n_pass = n_fail = 0
    for src, case in targets:
        expected = case["expected_output"]["verdict"]
        trials = []
        for i in range(args.trials):
            t = run_trial(claude_exe, model, case["input"], skill,
                          args.budget_usd, args.timeout)
            total_cost += t.get("cost_usd") or 0.0
            trials.append(t)
            print(f"  {src}#{case['id']} trial {i + 1}/{args.trials}: "
                  f"{trial_label(t)} ({t['duration_s']}s)")
        result, tally, majority = judge_case(trials, expected)
        n_pass += result == "pass"
        n_fail += result == "fail"
        results.append({
            "source_file": src,
            "id": case["id"],
            "input": case["input"],
            "expected_verdict": expected,
            "trials": [trial_label(t) for t in trials],
            "tally": tally,
            "majority": majority,
            "result": result,
        })
        print(f"{src}#{case['id']}: {result} (expected={expected}, majority={majority})")

    artifact = {
        "run_set": {
            "skill": skill,
            "date": _dt.date.today().isoformat(),
            "model": model,
            "cli_version": version,
            "trials_per_case": args.trials,
            "smoke": "pass",
            "total_cost_usd": round(total_cost, 4),
            "note": "cost は claude CLI の total_cost_usd 集計 (= client 側推計、 課金実測ではない)",
        },
        "cases": results,
        "summary": {"pass": n_pass, "fail": n_fail, "total": len(results)},
    }
    if args.out:
        out = Path(args.out)
        if out.exists():
            ec.eprint(f"WARNING: overwriting existing {out} (= 明示的な --out 指定)")
    else:
        out = unique_out_path(
            DEFAULT_OUT_DIR / f"{skill}-{_dt.date.today().isoformat()}.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(artifact, fh, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    print(f"\nwrote {out}")
    print(f"summary: pass={n_pass} fail={n_fail} cost=${round(total_cost, 4)}")
    return 1 if n_fail else 0


# --- compare ------------------------------------------------------------------
def compare(path_a: Path, path_b: Path) -> int:
    a, b = ec.read_yaml(path_a), ec.read_yaml(path_b)
    ra, rb = a["run_set"], b["run_set"]
    # trials_per_case も互換性条件に含める: N=3 baseline と N=1 probe の比較は
    # 単発試行比較と同じで noise と regression を分離できないため拒否する。
    for key in ("model", "cli_version", "trials_per_case"):
        if ra.get(key) != rb.get(key):
            ec.eprint(f"ERROR: {key} mismatch ({ra.get(key)} vs {rb.get(key)}); "
                      "不一致の run set 同士の diff は評価に使えないため拒否する。")
            return 2
    index_a = {(c["source_file"], c["id"]): c for c in a["cases"]}
    keys_b = {(c["source_file"], c["id"]) for c in b["cases"]}
    # NEW 側に OLD の case が欠けている partial run (= --case / --no-holdout 等) を
    # 「差分なし」 で通すと、 欠けた case が未評価のまま pass 扱いになるため拒否する。
    missing = sorted(k for k in index_a if k not in keys_b)
    if missing:
        ec.eprint("ERROR: NEW run set is missing cases present in OLD; "
                  "partial run は full baseline と比較できないため拒否する。")
        for key in missing:
            ec.eprint(f"  - {key}: OLD majority={index_a[key]['majority']}")
        return 2
    diffs = []
    for c in b["cases"]:
        key = (c["source_file"], c["id"])
        old = index_a.get(key)
        if old is None:
            diffs.append(f"+ {key}: new case (majority={c['majority']})")
        elif old["majority"] != c["majority"]:
            diffs.append(f"~ {key}: majority {old['majority']} -> {c['majority']} "
                         f"(expected={c['expected_verdict']})")
    if diffs:
        print("verdict-level diff (majority 単位):")
        for d in diffs:
            print(" ", d)
        return 1
    print("no majority-level verdict diff")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="L2 behavioral verdict-contract runner")
    p.add_argument("--skill", help="対象 skill 名 (現状 task-routing のみ想定)")
    p.add_argument("--trials", type=int, default=3, help="case あたりの試行数 (既定 3、 境界 case は 5)")
    p.add_argument("--case", type=int, default=None, help="単一 case id に絞る")
    p.add_argument("--no-holdout", action="store_true", help="eval/holdout/ を除外")
    p.add_argument("--holdout-only", action="store_true", help="eval/holdout/ のみ")
    p.add_argument("--sonnet", action="store_true",
                   help=f"model を {MODEL_SONNET} にする (既定 {MODEL_DEFAULT})")
    p.add_argument("--budget-usd", type=float, default=1.0, help="trial あたりの --max-budget-usd")
    p.add_argument("--timeout", type=int, default=300, help="trial あたりの timeout 秒")
    p.add_argument("--out", help="run set 記録の出力先 YAML (= 既存でも上書きする明示指定。 "
                   "未指定の既定パスは衝突時に -2, -3, ... suffix で回避)")
    p.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"),
                   help="2 つの run set 記録を majority 単位で diff する")
    args = p.parse_args()

    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))
    if not args.skill:
        p.error("--skill is required (or use --compare)")
    return run_set(args)


if __name__ == "__main__":
    sys.exit(main())
