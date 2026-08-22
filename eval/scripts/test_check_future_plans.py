#!/usr/bin/env python3
"""scripts/check-future-plans.py の detection-power test (= stdlib only, 無課金)。

このファイルの fixture 文字列は forbidden literal (Wave / Phase / Sprint / M<N> /
future-tense 表現) を意図的に含む。それが exemption list (`_SELF_REFERENCE_RE`) に
このファイル自身を載せている理由 — さもなくば `finish-task` の future-plans lint が
このファイルを違反として報告し続ける。

`.py` 拡張子に markdown 文法 (heading / 引用符付き例 / フェンス) の除外を適用すると、
その文法が実際に守っているコメント・docstring・panic message が黙って検出対象から
落ちる。TestDetectionPowerPython の各 fixture は、その落ち方を 1 つずつ再現する。

実行: python eval/scripts/test_check_future_plans.py
      (または python -m unittest test_check_future_plans -v)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "scripts" / "check-future-plans.py"
_HARNESS_LAYOUT_PRESENT = (REPO_ROOT / "AGENTS.md").is_file() and (REPO_ROOT / "docs").is_dir()


def _load_module():
    """check-future-plans.py (= ファイル名にハイフン) を module として読み込む。

    `@dataclass` の型解決が `cls.__module__` を `sys.modules` から引くため、
    `exec_module` の前に module 登録が要る (importlib の標準作法)。
    """
    spec = importlib.util.spec_from_file_location("check_future_plans", TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TARGET), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        timeout=60,
    )


# --- TestDetectionPowerPython fixtures ---------------------------------------------
# 1 fixture = 1 違反行。個別 test method の docstring に「どの blind spot を pin する
# か」を書く。fixture 自体を壊さずに検出だけ壊れれば、対応する 1 test だけが red になる。

A1_BACKTICK_COMMENT = (
    "def foo():\n"
    "    # `Wave 5 の実例` — ガードは共通層に置く。\n"
    "    pass\n"
)
A2_ONE_LINE_DOCSTRING = (
    "def foo():\n"
    '    x = """メモ (Wave 6)。あとで詳細を書く。"""\n'
    "    return x\n"
)
A3_STRING_LITERAL = 'THRESHOLD_NOTE = "Wave 8 の実験値、暫定"\n'
A4_FSTRING_PANIC = (
    "def _guard(p):\n"
    '    sys.exit(f"Wave 6 disclosure_wiring: file missing: {p}")\n'
)
A5_COLUMN0_BANNER = (
    "# ----------------------------------------------------------------- "
    "Wave 6: dialogue wiring check\n"
    "def foo():\n"
    "    pass\n"
)
A6_INDENTED_PLAIN_COMMENT = (
    "def foo():\n"
    "    # Wave 9 の実装ノート\n"
    "    pass\n"
)
A7_MULTILINE_DOCSTRING_BACKTICK_PAIR = (
    "def check_disclosure_wiring():\n"
    '    """`state.py` と対話 skill の整合を検査する。\n'
    "\n"
    "    (`check_disclosure_wiring`) — Wave 6。`check_type_b_wiring` と同型の検査。\n"
    '    """\n'
)
A8_UPPERCASE_M = "# 現在 M3 の状態を記録する\n"
A9_SPRINT_STRING = 'LABEL = "Sprint 3 の記録"\n'
A10_PHASE_DOCSTRING = (
    "def foo():\n"
    '    """このロジックは Phase 2 で実装した。"""\n'
)
A11_WILL_BE_COMMENT = "# this behavior will be implemented after the review\n"
A12_FOR_FUTURE_DOCSTRING = (
    "def foo():\n"
    '    """kept generic for future extension of the schema."""\n'
)
A13_STRAY_FENCE_IN_DOCSTRING = (
    "def foo():\n"
    '    """Example output.\n'
    "\n"
    "    ```\n"
    "    Wave 7 の実装ノート\n"
    '    """\n'
)

# 上記 13 fixture は測定済みの blind spot ごとに 1 つ選んだもので、`PATTERNS` 全 16
# entry のうち 7 label しか実地には出てこない (milestone-name 系 4 つ + will-be /
# for-future / Phase-de実装)。残り 9 label は blind-spot の実例と無関係なので、
# test_every_pattern_has_a_positive_case 専用に最小限の正例を別途持つ (= どの A
# fixture にも属さない。削除 / 追加された PATTERNS entry を拾うための補助)。
_EXTRA_PATTERN_COVERAGE = "\n".join(
    [
        "# later wave discussion for this guard",
        "# deferred to sync-branch review",
        "# is cut when the feature flag disables it",
        "# 互換性は M3 で再評価する",
        "# Wave 6 で対応する運用ログ",
        "# kept extensible to new metrics",
        "# may add more cases later if needed",
        "# 将来 API に拡張する設計",
        "# (and any future variants)",
    ]
)

_ALL_A_FIXTURES = [
    A1_BACKTICK_COMMENT,
    A2_ONE_LINE_DOCSTRING,
    A3_STRING_LITERAL,
    A4_FSTRING_PANIC,
    A5_COLUMN0_BANNER,
    A6_INDENTED_PLAIN_COMMENT,
    A7_MULTILINE_DOCSTRING_BACKTICK_PAIR,
    A8_UPPERCASE_M,
    A9_SPRINT_STRING,
    A10_PHASE_DOCSTRING,
    A11_WILL_BE_COMMENT,
    A12_FOR_FUTURE_DOCSTRING,
    A13_STRAY_FENCE_IN_DOCSTRING,
]


class TestDetectionPowerPython(unittest.TestCase):
    """`.py` に対する検出力の pin (= 過去の見落としの再発防止)。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _scan(self, text: str, filename: str = "sample_module.py"):
        return self.mod.scan_text(filename, text)

    def test_a1_indented_backtick_wrapped_comment(self):
        """バッククォート囲みの `Wave 5` はもう引用例として除外されない。"""
        findings, _ = self._scan(A1_BACKTICK_COMMENT)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (2, "Wave <N>(-<X>)"))

    def test_a2_one_line_docstring_closing_quote(self):
        """開閉の `\"\"\"` が同じ行にある docstring は closing quote として誤認されない。"""
        findings, _ = self._scan(A2_ONE_LINE_DOCSTRING)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (2, "Wave <N>(-<X>)"))

    def test_a3_plain_string_literal(self):
        """通常の文字列 literal は quoted-example 除外の対象外になる。"""
        findings, _ = self._scan(A3_STRING_LITERAL)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (1, "Wave <N>(-<X>)"))

    def test_a4_fstring_panic_message(self):
        """`sys.exit(f"...")` — panic message はルールが名指しする最重要サイト。"""
        findings, _ = self._scan(A4_FSTRING_PANIC)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (2, "Wave <N>(-<X>)"))

    def test_a5_column0_banner_comment(self):
        """列 0 の `# -----` banner comment は ATX heading として誤認されない。"""
        findings, _ = self._scan(A5_COLUMN0_BANNER)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (1, "Wave <N>(-<X>)"))

    def test_a6_indented_plain_comment_still_works(self):
        """インデント済み `# Wave 9` — 修正前から検出できていた形の回帰確認。"""
        findings, _ = self._scan(A6_INDENTED_PLAIN_COMMENT)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (2, "Wave <N>(-<X>)"))

    def test_a7_multiline_docstring_backtick_pair(self):
        """直前後の code-span backtick が挟む `Wave 6` は quote-pair として誤認されない。"""
        findings, _ = self._scan(A7_MULTILINE_DOCSTRING_BACKTICK_PAIR)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (4, "Wave <N>(-<X>)"))

    def test_a8_uppercase_m_pattern_still_fires(self):
        """`M<N>` 規則を case-sensitive にしても大文字 `M3` は検出され続ける。"""
        findings, _ = self._scan(A8_UPPERCASE_M)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (1, "M<N>(-M<N>)"))

    def test_a9_sprint_in_string_literal(self):
        findings, _ = self._scan(A9_SPRINT_STRING)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (1, "Sprint <N>"))

    def test_a10_phase_de_jissou_in_docstring(self):
        findings, _ = self._scan(A10_PHASE_DOCSTRING)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual(findings[0].line, 2)

    def test_a11_will_be_implemented_in_comment(self):
        findings, _ = self._scan(A11_WILL_BE_COMMENT)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (1, "will be <verb>"))

    def test_a12_for_future_extension_in_docstring(self):
        findings, _ = self._scan(A12_FOR_FUTURE_DOCSTRING)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (2, "for future <X>"))

    def test_a13_stray_fence_inside_docstring_does_not_silence_to_eof(self):
        """docstring 内の孤立した ``` は、以降の行を EOF まで黙らせない。"""
        findings, _ = self._scan(A13_STRAY_FENCE_IN_DOCSTRING)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual((findings[0].line, findings[0].pattern), (5, "Wave <N>(-<X>)"))

    def test_every_pattern_has_a_positive_case(self):
        """`PATTERNS` に追加された entry が正例なしで放置されないことの網羅性チェック。

        ここで見ているのは「今 `PATTERNS` にある label は全部 corpus 中に実例を持つ
        か」だけ。entry の削除はこの test では検出できない (corpus 側は無傷のまま
        残るため) — 削除は個々の A test (期待した違反が消えて red になる) が拾う。
        """
        corpus = "\n".join(_ALL_A_FIXTURES + [_EXTRA_PATTERN_COVERAGE])
        for _category, pattern, label in self.mod.PATTERNS:
            with self.subTest(label=label):
                self.assertIsNotNone(
                    pattern.search(corpus), f"pattern {label!r} has no positive example"
                )

    def test_markdown_syntax_kwarg_has_no_default(self):
        """`markdown_syntax` に default 値が付いていないことの固定。

        default が付くと、それを省略した将来の呼び出し元が黙って markdown 挙動
        (heading / quoted-example 除外あり) に倒れ、`.py` の検出力が元の欠陥に戻る。
        """
        with self.assertRaises(TypeError):
            self.mod.is_excluded_line("x")


# --- TestNoFalsePositivesPython fixtures --------------------------------------------

B1_MATCH_SLUG_FORMS = (
    'entry = log_entry("m1", cue_present=4, executed=2)\n'
    "series = tt.execution_rate_series(log)\n"
    'row_slugs = [row["slug"] for row in series["learning"]]\n'
    'assert row_slugs == ["m1", "m2", "m3"]\n'
    'print("m1: 味方が既に前に出ていたので合わせた")\n'
    'print("m2: (未記入)")\n'
)
B2_WAVE_RESPAWN_FORMS = (
    '"""Wave Respawn (Season 12 以降) を再現する。一律 N 秒で戻る仕組みではない。"""\n'
    "DEFAULT_RESPAWN = 12\n"
    "WAVE_WINDOW = 6\n"
    "wave_start = None\n"
    'print(f"Wave Respawn: 基本 {DEFAULT_RESPAWN} 秒 / wave 猶予 {WAVE_WINDOW} 秒")\n'
)
B3_SECTION_REF_IN_COMMENT = "# 詳細は Phase 3-1 / Step 4-5 を参照\n"


class TestNoFalsePositivesPython(unittest.TestCase):
    """`.py` の正当な用法 (= match slug / 識別子) を誤検出しないことの回帰確認。

    B1 (`ow-coach/tests/test_theme_tracker.py` の match slug) と B2
    (`ow-coach/src/fetch/roster.py` の Wave Respawn 語彙) は CLI 経由 (exit 0) で
    検証する — `--files` の実運用経路を通す。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _run_cli_on(self, text: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample_module.py"
            target.write_text(text, encoding="utf-8")
            return _run_cli(["--files", str(target)])

    def test_b1_lowercase_match_slugs(self):
        proc = self._run_cli_on(B1_MATCH_SLUG_FORMS)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_b2_wave_respawn_vocabulary(self):
        proc = self._run_cli_on(B2_WAVE_RESPAWN_FORMS)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_b3_section_ref_in_python_comment(self):
        findings, _ = self.mod.scan_text("sample_module.py", B3_SECTION_REF_IN_COMMENT)
        self.assertEqual(findings, [])


# --- TestMarkdownUnchanged fixtures --------------------------------------------------

C1_ATX_HEADING = "## Phase 2: 実装\n"
C2_RULE_DECLARATION = (
    "禁止パターン: `M[0-9]`, `Phase [0-9]`, `Wave [0-9]` を含む行は違反。\n"
)
C3_YTRACE_ACCEPTING = "accepting: wave 6 分割で実装期間 1 -> 3 セッション\n"
C4_QUOTED_EXAMPLE = "「Wave 6 で対応」という書き方は禁止表現の例。\n"
C5_FENCED_LITERAL = "```\nWave 6 で対応する例。\n```\n"
C6_PLAIN_PROSE = "Wave 6 で対応する\n"
C7_HEADING_WITHOUT_FORBIDDEN_CONTENT = "## この節はただの見出しです\n"


class TestMarkdownUnchanged(unittest.TestCase):
    """markdown 側の既存除外 (heading / rule 宣言 / Y-trace / 引用例 / fence) は無傷。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _scan_md(self, text: str):
        return self.mod.scan_text("sample_doc.md", text)

    def test_c1_atx_heading(self):
        findings, suppressed = self._scan_md(C1_ATX_HEADING)
        self.assertEqual(findings, [])
        # "Phase 2" in the heading text did match a PATTERNS regex before exclusion —
        # this is a real suppression, not a line that never had a match.
        self.assertEqual(suppressed, 1)

    def test_c2_rule_declaration_two_backticked_literals(self):
        findings, _ = self._scan_md(C2_RULE_DECLARATION)
        self.assertEqual(findings, [])

    def test_c3_ytrace_accepting_line(self):
        findings, _ = self._scan_md(C3_YTRACE_ACCEPTING)
        self.assertEqual(findings, [])

    def test_c4_quoted_example(self):
        findings, _ = self._scan_md(C4_QUOTED_EXAMPLE)
        self.assertEqual(findings, [])

    def test_c5_fenced_literal(self):
        findings, _ = self._scan_md(C5_FENCED_LITERAL)
        self.assertEqual(findings, [])

    def test_c6_plain_prose_is_still_a_violation(self):
        """markdown 側の除外を全部止めていないことの陽性確認。"""
        findings, _ = self._scan_md(C6_PLAIN_PROSE)
        self.assertEqual(len(findings), 1, findings)

    def test_c7_suppressed_counts_only_would_be_violations(self):
        """除外された行のうち forbidden pattern に一切マッチしない行は suppressed に
        数えない — 数えると「見出しが多いだけの doc」が suppressed 過多になり、
        カウントの意味 (= 除外が食った本物の違反) が薄れる。
        """
        findings, suppressed = self._scan_md(C7_HEADING_WITHOUT_FORBIDDEN_CONTENT)
        self.assertEqual(findings, [])
        self.assertEqual(suppressed, 0)


# --- TestSelfReferenceScope ------------------------------------------------------------


class TestSelfReferenceScope(unittest.TestCase):
    """`is_self_reference()` の対象範囲が後から静かに広がらないことの固定。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_true_cases(self):
        for path in (
            "scripts/check-future-plans.py",
            "skills/task-routing/SKILL.md",
            "eval/scripts/test_check_future_plans.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.mod.is_self_reference(path))

    def test_false_cases(self):
        for path in (
            "agents/architect.md",
            "AGENTS.md",
            "docs/adr/0001.md",
            ".skillshare/skills/foo/SKILL.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(self.mod.is_self_reference(path))

    @unittest.skipUnless(_HARNESS_LAYOUT_PRESENT, "harness repo layout not found")
    def test_absolute_path_forms_still_exempt(self):
        """`--files <absolute path>` でも自己参照除外が効くことの固定。

        regression: 絶対パスを repo-root 相対に正規化する前は、この形が exempt から
        漏れ、`docs/harness-design.md` のような自己参照 doc が絶対パスで渡されると
        誤って違反として報告されていた。
        """
        target = REPO_ROOT / "skills" / "task-routing" / "SKILL.md"
        forms = [str(target), str(target).replace("\\", "/")]
        for form in forms:
            with self.subTest(path=form):
                self.assertTrue(self.mod.is_self_reference(form))

    def test_unresolved_absolute_path_is_not_silently_exempt(self):
        """repo 外の絶対パスは正規化に失敗しても exempt にならない (安全側 fallback)。"""
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "skills" / "task-routing" / "SKILL.md"
            self.assertFalse(self.mod.is_self_reference(str(outside)))


# --- TestHarnessRepoClean ---------------------------------------------------------------


def _harness_markdown_targets() -> list[str]:
    """AGENTS.md / CLAUDE.md / agents/*.md / docs/**/*.md (self-reference 除く)。"""
    targets = ["AGENTS.md", "CLAUDE.md"]
    targets += [str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "agents").glob("*.md")]
    targets += [
        str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "docs").glob("**/*.md")
    ]
    return sorted(t.replace("\\", "/") for t in targets)


class TestHarnessRepoClean(unittest.TestCase):
    """harness 自身の markdown が現状 clean であることの固定 (= vendor 配布先では skip)。"""

    @unittest.skipUnless(_HARNESS_LAYOUT_PRESENT, "harness repo layout not found")
    def test_harness_markdown_is_clean(self):
        proc = _run_cli(["--files", *_harness_markdown_targets()])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


# --- TestCLIInvocationErrors ------------------------------------------------------------


class TestCLIInvocationErrors(unittest.TestCase):
    """`main()` の invocation-error 分岐を CLI 経由で直接叩く。

    detection-power fixture (A1-A13) は全部 `scan_text()` を直接呼ぶため、`main()` /
    argparse / file-I/O 自体は他の少数の CLI 経由 test でしか通らない。この class は
    その分岐 (missing path / undecodable file) を明示的に踏む。
    """

    def test_missing_files_path_exits_2(self):
        proc = _run_cli(["--files", "does/not/exist.md"])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("does/not/exist.md", proc.stderr)

    def test_undecodable_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "binary.py"
            target.write_bytes(b"\xff\xfe\x00\x01not-utf8")
            proc = _run_cli(["--files", str(target)])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_explicit_files_violation_exits_1(self):
        """`--files` 経由の正常系 (検出 -> exit 1) も CLI レベルで固定する。"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample_module.py"
            target.write_text(A3_STRING_LITERAL, encoding="utf-8")
            proc = _run_cli(["--files", str(target)])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Wave <N>(-<X>)", proc.stdout)


# --- TestNonAsciiFilenames ---------------------------------------------------------------


def _init_temp_git_repo(root: Path) -> None:
    """空 commit 済みの git repo を root に作る (diff_files() が HEAD を要求するため)。"""
    for args in (
        ["init", "-q"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "test"],
        ["commit", "--allow-empty", "-q", "-m", "init"],
    ):
        subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )


class TestNonAsciiFilenames(unittest.TestCase):
    """git の `core.quotepath` (既定 true) が非 ASCII ファイル名を escape する経路の固定。

    escape されたパス文字列 (`"\\346\\227\\245..."`) はディスク上のどのファイルとも
    一致しないため、正規化しないと違反ファイルが黙ってスキップされ「違反なし」に化ける。
    """

    def test_non_ascii_violating_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_temp_git_repo(repo)
            target = repo / "日本語.py"
            target.write_text('THRESHOLD = "Wave 6 の実験値"\n', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(TARGET)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=repo,
                timeout=60,
            )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("milestone-name", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
