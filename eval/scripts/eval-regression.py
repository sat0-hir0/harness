#!/usr/bin/env python3
"""eval-regression.py — baseline と現在の case output を diff し、 ズレを検出する。

fixture-sync lint の本体。 eval-baseline.py が固定した baseline/*.baseline.yaml と、
現在の cases/*.yaml が生成する期待 output を比較する。 skill / case を編集した結果、
期待 output が baseline から変わっていれば「未同期」として報告する (= skill を実行
しないため挙動回帰そのものは検知しない。 fixture 同士の同期を lint するだけ)。 差分
ゼロなら exit 0、 差分ありなら exit 1 (= CI / pre-push gate で使える)。

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


# baseline / current の両方から取り出して diff する契約 field。
# input / skill / case_id / snapshot_id は identity / metadata なので除外する
# (= input は test-strategy §4 で baseline と現在で意図的に食い違うため diff すると
#  false drift になる)。 trigger 契約 (expected_trigger / expected_no_trigger) を
# expected_output と並べて比較対象に含める (= trigger を反転しても回帰検出されない穴を塞ぐ)。
CONTRACT_FIELDS = ("expected_trigger", "expected_no_trigger", "expected_output")


def contract_view(entry: dict) -> dict:
    """baseline_entry 形式の dict から契約 field だけを取り出す。"""
    return {k: entry.get(k) for k in CONTRACT_FIELDS}


def apply_override(skill: str, case: dict) -> str:
    """意図した diff を baseline に再固定し、 更新した snapshot_id を返す。"""
    entry = ec.baseline_entry(skill, case)
    ec.write_yaml(ec.BASELINE_DIR / f"{entry['snapshot_id']}.baseline.yaml", entry)
    return entry["snapshot_id"]


def main() -> int:
    p = argparse.ArgumentParser(description="diff baseline vs current case output")
    p.add_argument("--skill", required=True, help="skill 名 または 'all'")
    p.add_argument("--judge", action="store_true", help="Ollama judge で semantic 等価も確認")
    p.add_argument("--override", action="store_true", help="意図した diff を baseline に取り込む")
    p.add_argument("--case", type=int, default=None,
                   help="単一 case id に絞る (--skill は具体名必須)")
    args = p.parse_args()

    if args.case is not None and args.skill == "all":
        ec.eprint("ERROR: --case は --skill に具体名を指定した時のみ使える (all 不可)")
        return 2

    use_judge = args.judge
    if use_judge and not ec.judge_available():
        ec.eprint(f"WARNING: judge ({ec.JUDGE_MODEL} @ {ec.OLLAMA_URL}) unreachable; "
                  "structural diff only")
        use_judge = False

    targets = ec.skill_names() if args.skill == "all" else [args.skill]

    results = []
    details = []
    missing_baseline = []
    overridden = []
    for skill in targets:
        try:
            data = ec.load_cases(skill)
        except (FileNotFoundError, ValueError) as e:
            ec.eprint("ERROR:", e)
            return 2
        for c in data["cases"]:
            if args.case is not None and c["id"] != args.case:
                continue
            sid = ec.snapshot_id(skill, c["id"])
            bpath = ec.BASELINE_DIR / f"{sid}.baseline.yaml"
            if not bpath.exists():
                missing_baseline.append(sid)
                continue
            baseline = contract_view(ec.read_yaml(bpath))
            current = contract_view(ec.baseline_entry(skill, c))
            struct_diff = diff_dicts(baseline, current)

            if not struct_diff:
                status = "pass"
            elif args.override:
                status = "acknowledged"
                apply_override(skill, c)
                overridden.append(sid)
            else:
                status = "fail"

            entry = {
                "snapshot_id": sid,
                "status": status,
                "structural_diff": struct_diff or "none",
            }
            if struct_diff and use_judge:
                verdict = ec.judge_compare(baseline, current)
                if verdict["match"] is True:
                    entry["judge"] = "semantic-equivalent (表記ゆれ許容)"
                elif verdict["match"] is False:
                    entry["judge"] = f"semantic-mismatch: {verdict['reason']}"
                else:
                    entry["judge"] = f"unavailable: {verdict['reason']}"
            results.append(entry)
            if status != "pass":
                details.append(entry)

    n_pass = sum(1 for r in results if r["status"] == "pass")
    n_fail = sum(1 for r in results if r["status"] == "fail")
    n_ack = sum(1 for r in results if r["status"] == "acknowledged")
    regressions = n_fail

    report = {
        "compared": len(results),
        "mode": "structural+judge" if use_judge else "structural",
        "pass": n_pass,
        "fail": n_fail,
        "acknowledged": n_ack,
        "regressions": regressions,
        "missing_baseline": missing_baseline or "none",
        "overridden": overridden or "none",
        "details": details if details else "no drift from baseline",
    }
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False))

    if args.case is not None and not results and not missing_baseline:
        ec.eprint(f"WARNING: case id {args.case} matched nothing in skill '{args.skill}'")

    if missing_baseline:
        ec.eprint(f"NOTE: {len(missing_baseline)} case(s) have no baseline; "
                  "run eval-baseline.py --skill all first")
    # 差分あり (fail) or baseline 欠落 → 非 0。 acknowledged は exit 1 にしない。
    return 1 if (regressions or missing_baseline) else 0


if __name__ == "__main__":
    sys.exit(main())
