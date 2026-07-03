#!/usr/bin/env python3
"""eval-baseline.py — 現状の case output を baseline として記録する。

eval-run.py が生成する snapshot と同じ内容を eval/baseline/ に固定する。
以降 skill / case を変更したら eval-regression.py が baseline と最新 snapshot を
diff し、 意図しないズレを検出する。 baseline は「合意された正しい状態」であり、
git に commit して変更履歴を残す (= snapshots/ は派生物なので commit しない)。

使い方:
  eval-baseline.py --skill all         # 全 skill の baseline を更新
  eval-baseline.py --skill task-routing
"""

from __future__ import annotations

import argparse
import sys

import yaml

import eval_common as ec


def main() -> int:
    p = argparse.ArgumentParser(description="record current case output as baseline")
    p.add_argument("--skill", required=True, help="skill 名 または 'all'")
    args = p.parse_args()

    targets = ec.skill_names() if args.skill == "all" else [args.skill]

    written = 0
    for skill in targets:
        try:
            data = ec.load_cases(skill)
        except FileNotFoundError as e:
            ec.eprint("ERROR:", e)
            return 2
        for c in data["cases"]:
            entry = ec.baseline_entry(skill, c)
            ec.write_yaml(ec.BASELINE_DIR / f"{entry['snapshot_id']}.baseline.yaml", entry)
            written += 1

    print(yaml.safe_dump(
        {"baseline_written": written, "baseline_dir": str(ec.BASELINE_DIR), "skills": targets},
        allow_unicode=True, sort_keys=False, default_flow_style=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
