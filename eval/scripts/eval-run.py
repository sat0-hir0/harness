#!/usr/bin/env python3
"""eval-run.py — case を snapshot として記録し、 期待 output を YAML で表示する。

snapshot test の本体。 skill 自体はローカルの python からは実行できない
(= skill は Claude Code session 内でしか走らない) ため、 本 script は skill を
実行しない。 case の expected_output を「その case が固定する正しい output」として
snapshot に書き出す。 skill / SKILL.md を変更したら、 その変更を case に反映し、
eval-regression.py で baseline との差分を確認する、 という運用で副作用を検知する。

そのため出力の match は常に "match" (= actual == expected)。 これは「skill を
実行して検証した」という意味ではなく、「この case が固定する期待値の snapshot を
記録した」という意味。 実 skill 挙動との semantic 照合は本 script では行わない
(= judge を使った照合は baseline vs 現在 case を比較する eval-regression.py 側の責務)。

使い方:
  eval-run.py --skill task-routing --case 1     # 1 件の期待 output を YAML 表示
  eval-run.py --skill task-routing              # 1 skill の全 case
  eval-run.py --skill all                       # 全 skill の全 case (= 30-60 snapshot)
  eval-run.py --validate                        # case schema 検証のみ
"""

from __future__ import annotations

import argparse
import copy
import sys

import yaml

import eval_common as ec


def run_case(skill: str, case: dict) -> dict:
    """1 case の snapshot 用結果 dict を返す (= skill は実行しない)。"""
    expected = case.get("expected_output", {})
    # actual は expected とは別オブジェクトにする (= YAML anchor 化を避け、
    # snapshot を人間が読める平文に保つ)。 skill を実行しないため両者は同値。
    actual = copy.deepcopy(expected)

    return {
        "snapshot_id": ec.snapshot_id(skill, case["id"]),
        "skill": skill,
        "case_id": case["id"],
        "input": case["input"],
        "expected_trigger": case.get("expected_trigger"),
        "expected_no_trigger": case.get("expected_no_trigger", []),
        "expected_output": expected,
        "actual_output": actual,
        "mode": "static",
        "match": "match",  # actual == expected (= 期待値 snapshot の記録であり検証ではない)
        "reason": "static snapshot (skill not executed; expected-value fixture)",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="run eval snapshot cases")
    p.add_argument("--skill", help="skill 名 または 'all'")
    p.add_argument("--case", type=int, help="case id (= --skill 単独指定時のみ)")
    p.add_argument("--validate", action="store_true", help="case schema 検証のみ実行")
    p.add_argument("--no-save", action="store_true", help="snapshot を保存しない (= 表示のみ)")
    args = p.parse_args()

    if args.validate:
        total, errors = ec.validate_all()
        if errors:
            for e in errors:
                ec.eprint("INVALID:", e)
            print(yaml.safe_dump({"validated": total, "errors": errors}, allow_unicode=True, sort_keys=False))
            return 1
        print(yaml.safe_dump({"validated": total, "errors": "none", "result": "all cases valid"},
                             allow_unicode=True, sort_keys=False))
        return 0

    if not args.skill:
        p.error("--skill or --validate is required")

    # 対象 skill を決める
    if args.skill == "all":
        if args.case is not None:
            p.error("--case は単一 skill 指定時のみ有効です")
        targets = ec.skill_names()
    else:
        targets = [args.skill]

    results = []
    for skill in targets:
        try:
            data = ec.load_cases(skill)
        except FileNotFoundError as e:
            ec.eprint("ERROR:", e)
            return 2
        cases = data["cases"]
        if args.case is not None:
            cases = [c for c in cases if c.get("id") == args.case]
            if not cases:
                ec.eprint(f"ERROR: {skill}: case id {args.case} not found")
                return 2
        for c in cases:
            res = run_case(skill, c)
            results.append(res)
            if not args.no_save:
                ec.write_yaml(ec.SNAPSHOT_DIR / f"{res['snapshot_id']}.snapshot.yaml", res)

    # 表示: 1 件なら詳細 YAML、 複数ならサマリ + 内訳
    if len(results) == 1:
        print(yaml.safe_dump(results[0], allow_unicode=True, sort_keys=False, default_flow_style=False))
    else:
        summary = {
            "run": len(results),
            "mode": "static",
            "recorded": len(results),
            "snapshots_dir": str(ec.SNAPSHOT_DIR),
            "cases": [
                {"snapshot_id": r["snapshot_id"], "match": r["match"], "input": r["input"][:60]}
                for r in results
            ],
        }
        print(yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, default_flow_style=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
