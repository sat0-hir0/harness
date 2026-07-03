#!/usr/bin/env python3
"""eval-behavioral.py の synthetic test (= claude 実行なし、 無課金)。

手書きの小さな run set YAML を作って --compare の各経路 (互換性 check /
partial-run 拒否 / majority diff) を subprocess で検証し、 既定出力パスの
same-day suffix (= 上書き防止) は unique_out_path() を直接検証する。

実行: python test_eval_behavioral.py
      (または python -m unittest test_eval_behavioral -v)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
RUNNER = SCRIPTS_DIR / "eval-behavioral.py"


def _load_runner_module():
    """eval-behavioral.py (= ファイル名にハイフン) を module として読み込む。"""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("eval_behavioral", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _case(src: str, cid: int, majority: str, expected: str = "Lead-direct") -> dict:
    return {
        "source_file": src,
        "id": cid,
        "input": f"synthetic input {src}#{cid}",
        "expected_verdict": expected,
        "trials": [majority] * 3,
        "tally": {majority: 3},
        "majority": majority,
        "result": "pass" if majority == expected else "fail",
    }


def _write_artifact(path: Path, cases: list[dict], *,
                    model: str = "claude-haiku-4-5",
                    cli: str = "2.1.195",
                    trials: int = 3) -> Path:
    artifact = {
        "run_set": {
            "skill": "task-routing",
            "date": "2026-07-03",
            "model": model,
            "cli_version": cli,
            "trials_per_case": trials,
            "smoke": "pass",
            "total_cost_usd": 0.0,
            "note": "synthetic artifact for test_eval_behavioral.py",
        },
        "cases": cases,
        "summary": {
            "pass": sum(c["result"] == "pass" for c in cases),
            "fail": sum(c["result"] == "fail" for c in cases),
            "total": len(cases),
        },
    }
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(artifact, fh, allow_unicode=True, sort_keys=False)
    return path


def _run_compare(old: Path, new: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--compare", str(old), str(new)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=SCRIPTS_DIR, timeout=60,
    )


class CompareTests(unittest.TestCase):
    """--compare の exit code 契約: 0 = 差分なし / 1 = 差分 / 2 = 前提条件エラー。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.full_cases = [
            _case("cases", 1, "Lead-direct"),
            _case("cases", 2, "delegate-single", expected="delegate-single"),
            _case("holdout", 1, "delegate-slice", expected="delegate-slice"),
        ]
        self.old = _write_artifact(self.tmp / "old.yaml", self.full_cases)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_identical_run_sets_exit_0(self):
        new = _write_artifact(self.tmp / "new.yaml", self.full_cases)
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no majority-level verdict diff", proc.stdout)

    def test_majority_change_exit_1(self):
        changed = [_case("cases", 1, "delegate-single")] + self.full_cases[1:]
        new = _write_artifact(self.tmp / "new.yaml", changed)
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("Lead-direct -> delegate-single", proc.stdout)

    def test_new_case_in_new_exit_1(self):
        extra = self.full_cases + [_case("holdout", 2, "Lead-direct")]
        new = _write_artifact(self.tmp / "new.yaml", extra)
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("new case", proc.stdout)

    def test_partial_new_missing_old_case_exit_2(self):
        # --case / --no-holdout 由来の partial run が「差分なし」で通らないこと。
        partial = [self.full_cases[0]]
        new = _write_artifact(self.tmp / "new.yaml", partial)
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("missing cases present in OLD", proc.stderr)
        # 欠けた key が列挙されること (= どの case が未評価かを示す)。
        self.assertIn("holdout", proc.stderr)

    def test_trials_mismatch_exit_2(self):
        new = _write_artifact(self.tmp / "new.yaml", self.full_cases, trials=1)
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("trials_per_case mismatch", proc.stderr)

    def test_model_mismatch_exit_2(self):
        new = _write_artifact(self.tmp / "new.yaml", self.full_cases,
                              model="claude-sonnet-5")
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("model mismatch", proc.stderr)

    def test_cli_version_mismatch_exit_2(self):
        new = _write_artifact(self.tmp / "new.yaml", self.full_cases, cli="9.9.9")
        proc = _run_compare(self.old, new)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("cli_version mismatch", proc.stderr)


class VerdictRegexTests(unittest.TestCase):
    """VERDICT_RE の抽出契約 (= backlog #108 の no-verdict-line 根本原因の再発防止)。

    positive case は 2026-07-03 の probe run で観測された haiku の実出力形式
    (= raw stream-json から採取) を含む。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rx = _load_runner_module().VERDICT_RE

    def _match(self, text: str) -> str | None:
        m = self.rx.search(text)
        return m.group(1) if m else None

    def test_plain(self):
        self.assertEqual(self._match("判定: Lead-direct"), "Lead-direct")

    def test_bold_label(self):
        self.assertEqual(self._match("**判定**: delegate-single (S)"),
                         "delegate-single")

    def test_fullwidth_colon(self):
        self.assertEqual(self._match("判定： delegate-slice"), "delegate-slice")

    def test_backtick_code_span_around_verdict(self):
        # 観測形式: **判定: `delegate-slice` (L)** (= 旧 regex の取りこぼし #1)
        self.assertEqual(self._match("**判定: `delegate-slice` (L)**"),
                         "delegate-slice")

    def test_english_verdict_label(self):
        # 観測形式: ## Verdict: **delegate-slice (L)** (= 旧 regex の取りこぼし #2)
        self.assertEqual(self._match("## Verdict: **delegate-slice (L)**"),
                         "delegate-slice")

    def test_ytrace_code_span_line(self):
        # Y-trace 全体が code span でも内側は plain 形式なので拾える
        line = "**Y-trace**: `判定: delegate-single (XS) | ∵ file 確認: 1 file`"
        self.assertEqual(self._match(line), "delegate-single")

    def test_no_verdict_line_returns_none(self):
        self.assertIsNone(self._match("skill は発火したが判定行を書かなかった出力"))

    def test_label_without_colon_returns_none(self):
        # 見出しだけの行 (= `## 判定`) は verdict token が続かない限り拾わない
        self.assertIsNone(self._match("## 判定\nこのタスクは委譲が妥当です"))


class UniqueOutPathTests(unittest.TestCase):
    """既定出力パスの same-day suffix (= 既存 run set を silent overwrite しない)。"""

    def setUp(self) -> None:
        self.mod = _load_runner_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_same_path_when_free(self):
        target = self.tmp / "task-routing-2026-07-03.yaml"
        self.assertEqual(self.mod.unique_out_path(target), target)

    def test_appends_suffix_when_target_exists(self):
        target = self.tmp / "task-routing-2026-07-03.yaml"
        target.touch()
        got = self.mod.unique_out_path(target)
        self.assertEqual(got, self.tmp / "task-routing-2026-07-03-2.yaml")
        self.assertTrue(target.exists(), "既存 artifact が消えていない")

    def test_increments_past_existing_suffixes(self):
        (self.tmp / "task-routing-2026-07-03.yaml").touch()
        (self.tmp / "task-routing-2026-07-03-2.yaml").touch()
        got = self.mod.unique_out_path(self.tmp / "task-routing-2026-07-03.yaml")
        self.assertEqual(got, self.tmp / "task-routing-2026-07-03-3.yaml")


if __name__ == "__main__":
    unittest.main(verbosity=2)
