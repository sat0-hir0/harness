#!/usr/bin/env python3
"""eval-regression.py — baseline と現在の case output を diff し、 ズレを検出する。

eval-baseline.py が固定した baseline/*.baseline.yaml と、 現在の cases/*.yaml が
生成する期待 output を比較する。 skill / case を編集した結果、 期待 output が
baseline から変わっていれば regression として報告する。 差分ゼロなら exit 0、
差分ありなら exit 1 (= CI / pre-commit gate で使える)。

judge (= --judge) を付けると、 単純な構造 diff に加えてローカル Ollama judge に
「baseline と現在が semantic に等価か」を判定させる (= 表記ゆれを許容した比較)。
judge 到達不可なら構造 diff のみで判定する。

使い方:
  eval-regression.py --skill all
  eval-regression.py --skill task-routing --judge
"""

from __future__ import annotations

import argparse
import sys

import yaml

import eval_common as ec


def current_expected(skill: str, case_id: int) -> dict:
    case = ec.find_case(skill, case_id)
    return case.get("expected_output", {})


def diff_dicts(baseline: dict, current: dict, path: str = "") -> list[str]:
    """2 つの dict を再帰比較し、 差分を人間可読な文字列リストで返す。"""
    diffs = []
    keys = set(baseline) | set(current)
    for k in sorted(keys, key=str):
        p = f"{path}.{k}" if path else str(k)
        if k not in baseline:
            diffs.append(f"+ {p}: {current[k]!r} (baseline に無し)")
        elif k not in current:
            diffs.append(f"- {p}: {baseline[k]!r} (現在に無し)")
        elif isinstance(baseline[k], dict) and isinstance(current[k], dict):
            diffs.extend(diff_dicts(baseline[k], current[k], p))
        elif baseline[k] != current[k]:
            diffs.append(f"~ {p}: {baseline[k]!r} -> {current[k]!r}")
    return diffs


def main() -> int:
    p = argparse.ArgumentParser(description="diff baseline vs current case output")
    p.add_argument("--skill", required=True, help="skill 名 または 'all'")
    p.add_argument("--judge", action="store_true", help="Ollama judge で semantic 等価も確認")
    args = p.parse_args()

    use_judge = args.judge
    if use_judge and not ec.judge_available():
        ec.eprint(f"WARNING: judge ({ec.JUDGE_MODEL} @ {ec.OLLAMA_URL}) unreachable; "
                  "structural diff only")
        use_judge = False

    targets = ec.skill_names() if args.skill == "all" else [args.skill]

    results = []
    missing_baseline = []
    for skill in targets:
        try:
            data = ec.load_cases(skill)
        except (FileNotFoundError, ValueError) as e:
            ec.eprint("ERROR:", e)
            return 2
        for c in data["cases"]:
            sid = ec.snapshot_id(skill, c["id"])
            bpath = ec.BASELINE_DIR / f"{sid}.baseline.yaml"
            if not bpath.exists():
                missing_baseline.append(sid)
                continue
            baseline = ec.read_yaml(bpath).get("expected_output", {})
            current = c.get("expected_output", {})
            struct_diff = diff_dicts(baseline, current)

            entry = {"snapshot_id": sid, "structural_diff": struct_diff or "none"}
            if struct_diff and use_judge:
                verdict = ec.judge_compare(baseline, current)
                if verdict["match"] is True:
                    entry["judge"] = "semantic-equivalent (表記ゆれ許容)"
                elif verdict["match"] is False:
                    entry["judge"] = f"semantic-mismatch: {verdict['reason']}"
                else:
                    entry["judge"] = f"unavailable: {verdict['reason']}"
            results.append(entry)

    regressions = [r for r in results if r["structural_diff"] != "none"]

    report = {
        "compared": len(results),
        "regressions": len(regressions),
        "missing_baseline": missing_baseline or "none",
        "mode": "structural+judge" if use_judge else "structural",
        "details": regressions if regressions else "no drift from baseline",
    }
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False))

    if missing_baseline:
        ec.eprint(f"NOTE: {len(missing_baseline)} case(s) have no baseline; "
                  "run eval-baseline.py --skill all first")
    # 差分あり or baseline 欠落 → 非 0
    return 1 if (regressions or missing_baseline) else 0


if __name__ == "__main__":
    sys.exit(main())
