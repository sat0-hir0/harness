"""共通ヘルパー: case ローダ / judge クライアント / snapshot I/O。

eval-run.py / eval-baseline.py / eval-regression.py が共有する。
標準ライブラリ + PyYAML のみに依存する。 judge (= ローカル Ollama) は
optional で、 到達不可なら呼び出し側が static mode に fallback する。
"""

from __future__ import annotations

import copy
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# Windows の既定 console encoding (= cp932) だと日本語 case の表示が化ける。
# ファイル I/O は常に encoding="utf-8" を明示しているため実害はないが、
# stdout/stderr も UTF-8 に揃えて表示崩れを防ぐ (= Python 3.7+ の reconfigure)。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# --- パス規約 -------------------------------------------------------------
# eval/scripts/eval_common.py から見て eval/ が 1 つ上。
EVAL_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = EVAL_ROOT / "cases"
BASELINE_DIR = EVAL_ROOT / "baseline"
SNAPSHOT_DIR = EVAL_ROOT / "snapshots"

# judge (= Ollama) の既定接続先。 環境変数で上書き可能。
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "qwen3:14b")


# --- case ローダ ----------------------------------------------------------
def skill_names() -> list[str]:
    """cases/ にある skill 名を返す (= ファイル名から .yaml を除いたもの)。"""
    return sorted(p.stem for p in CASES_DIR.glob("*.yaml"))


def load_cases(skill: str) -> dict:
    """1 skill の case ファイルを読む。 skill 名と case リストを持つ dict を返す。"""
    path = CASES_DIR / f"{skill}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"case file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not data or "cases" not in data:
        raise ValueError(f"{path}: missing 'cases' key")
    data.setdefault("skill", skill)
    return data


def find_case(skill: str, case_id: int) -> dict:
    data = load_cases(skill)
    for c in data["cases"]:
        if c.get("id") == case_id:
            return c
    raise KeyError(f"{skill}: case id {case_id} not found")


# --- schema validation ----------------------------------------------------
REQUIRED_CASE_FIELDS = ("id", "input", "expected_trigger", "expected_output")


def validate_case(skill: str, case: dict) -> list[str]:
    """1 case の schema 違反を文字列リストで返す (= 空なら OK)。"""
    errs = []
    for f in REQUIRED_CASE_FIELDS:
        if f not in case:
            errs.append(f"{skill} case {case.get('id', '?')}: missing '{f}'")
    if "expected_no_trigger" in case and not isinstance(
        case["expected_no_trigger"], list
    ):
        errs.append(f"{skill} case {case.get('id')}: expected_no_trigger must be a list")
    return errs


def validate_all() -> tuple[int, list[str]]:
    """全 skill の全 case を検証。 (検証件数, エラーリスト) を返す。"""
    total, errors = 0, []
    for skill in skill_names():
        data = load_cases(skill)
        ids = [c.get("id") for c in data["cases"]]
        if ids != sorted(ids):
            errors.append(f"{skill}: case ids not in ascending order: {ids}")
        for c in data["cases"]:
            total += 1
            errors.extend(validate_case(skill, c))
    return total, errors


# --- judge (optional) -----------------------------------------------------
def judge_available() -> bool:
    """Ollama daemon が到達可能で JUDGE_MODEL が load 可能かを確認する。"""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        names = {m.get("name", "") for m in tags.get("models", [])}
        # 完全一致、 または Ollama が tag を正規化した "<model>:latest" 形のみ許可する。
        # 素の startswith は "qwen3:14b" が "qwen3:14b-instruct" 等の別量子化に
        # 過剰マッチし、 judge_compare が 404 を返す false positive を招くため使わない。
        return any(n == JUDGE_MODEL or n == f"{JUDGE_MODEL}:latest" for n in names)
    except (urllib.error.URLError, OSError, ValueError):
        return False


def judge_compare(expected: dict, actual: dict, timeout: int = 120) -> dict:
    """expected と actual を judge (= Ollama) に semantic 比較させる。

    {"match": bool, "reason": str} を返す。 judge 呼び出しに失敗したら
    match=None (= 判定不能) を返し、 呼び出し側が static 判定に委ねる。
    """
    prompt = (
        "You are a strict evaluation judge for a skill-routing test harness.\n"
        "Compare the EXPECTED skill output against the ACTUAL skill output.\n"
        "They match if the key decision fields (verdict, action, type, status, "
        "scope, trigger) are semantically equivalent. Minor wording differences "
        "are fine; a different verdict/action/type is a mismatch.\n"
        "Reply with ONLY compact JSON: {\"match\": true|false, \"reason\": \"<short>\"}.\n\n"
        f"EXPECTED:\n{json.dumps(expected, ensure_ascii=False)}\n\n"
        f"ACTUAL:\n{json.dumps(actual, ensure_ascii=False)}\n"
    )
    payload = {
        "model": JUDGE_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 200},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = (body.get("response") or "").strip()
        parsed = _extract_json(text)
        if parsed is None:
            return {"match": None, "reason": f"judge returned unparseable text: {text[:120]}"}
        return {"match": bool(parsed.get("match")), "reason": str(parsed.get("reason", ""))}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"match": None, "reason": f"judge call failed: {e}"}


def _extract_json(text: str):
    """テキストから最初の JSON オブジェクトを抜き出して parse する。"""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except ValueError:
        return None


# --- snapshot / baseline I/O ---------------------------------------------
def snapshot_id(skill: str, case_id: int) -> str:
    return f"{skill}-{case_id}"


def baseline_entry(skill: str, case: dict) -> dict:
    """baseline に固定する 1 case 分の期待 output スナップショット。"""
    return {
        "snapshot_id": snapshot_id(skill, case["id"]),
        "skill": skill,
        "case_id": case["id"],
        "input": case["input"],
        "expected_trigger": case.get("expected_trigger"),
        "expected_no_trigger": case.get("expected_no_trigger", []),
        "expected_output": copy.deepcopy(case.get("expected_output", {})),
    }


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=True, default_flow_style=False)


def read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def eprint(*args) -> None:
    print(*args, file=sys.stderr)
