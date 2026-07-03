#!/usr/bin/env python3
"""harness の context 消費量を実測する。

skill / agent / doc / script の token / char / description 長さを走査し、
「どのファイルがどれだけ context を食っているか」「業界基準からどれだけ乖離しているか」
を token 順の table で出力する。

依存: Python 標準ライブラリのみ (= script-placement.md の cross-OS 方針)。
token は cl100k_base 概算 (= 誤差 ±10%)、 tiktoken には依存しない。

使い方:
    python ~/code/harness/scripts/metrics/count-tokens.py
    python ~/code/harness/scripts/metrics/count-tokens.py --root ~/code/harness
    python ~/code/harness/scripts/metrics/count-tokens.py --json
"""

import argparse
import glob
import io
import json
import os
import sys

# Windows のコンソールで日本語出力を UTF-8 に固定 (= cp932 事故回避)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# === 業界指標 (= 比較の基準線) ===
# skill 1 個あたりの token 上限。 Anthropic の skill 設計ガイド由来の目安。
SKILL_TOKEN_BUDGET = 2000
# description 1 個あたりの char 上限。 skill listing に載る全 description の合計を budget 内に収めるための目安。
DESCRIPTION_CHAR_BUDGET = 130
# skill listing 全体の description char budget。 全 skill の description 合計がこれを超えると listing が肥大化する。
LISTING_CHAR_BUDGET = 16000


def estimate_tokens(content):
    """cl100k_base 概算で token 数を見積もる。

    英語 (= ASCII): 1 token ≈ 4 chars
    日本語 / 中国語 (= 非 ASCII): 1 char ≈ 1.5 tokens
    """
    n_chars = len(content)
    n_ascii = sum(1 for c in content if ord(c) < 128)
    n_nonascii = n_chars - n_ascii
    est = n_ascii // 4 + int(n_nonascii * 1.5)
    return n_chars, n_ascii, n_nonascii, est


def extract_description(content):
    """YAML frontmatter から description の値を取り出す。 無ければ空文字。

    単一行 (= `description: ...`) と 複数行 folded/literal scalar
    (= `description: >` / `description: |` + インデント継続行) の両方に対応。
    標準ライブラリのみで動かすため簡易 parser を自前実装する。
    PyYAML が import できる環境では yaml.safe_load を優先する (= skill listing が実際に
    load する値と一致させる。 unquoted scalar の ` #` comment 切断等を正確に反映)。
    """
    try:
        import yaml  # 任意依存 (= eval/ が既に要求)。 無ければ簡易 parser へ fallback
        parts = content.split("---")
        if len(parts) >= 3:
            data = yaml.safe_load(parts[1])
            if isinstance(data, dict) and isinstance(data.get("description"), str):
                return " ".join(data["description"].split())
    except Exception:
        pass
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    # frontmatter block の範囲を特定
    fm_end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    if fm_end is None:
        return ""

    fm = lines[1:fm_end]
    for i, line in enumerate(fm):
        stripped = line.lstrip()
        if not stripped.startswith("description:"):
            continue
        rest = stripped[len("description:"):].strip()
        # folded (>) / literal (|) scalar: 後続のインデント行を連結
        if rest in (">", "|", ">-", "|-", ">+", "|+"):
            collected = []
            for cont in fm[i + 1:]:
                if cont.strip() == "":
                    collected.append("")
                    continue
                # インデントが消えたら scalar 終了 (= 次の key)
                if not cont.startswith((" ", "\t")):
                    break
                collected.append(cont.strip())
            return " ".join(x for x in collected if x).strip()
        # 単一行: 前後の quote を剥がす
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in ("'", '"'):
            return rest[1:-1].strip()
        # unquoted plain scalar: YAML は ` #` 以降を comment として捨てるため、
        # 実際に load される長さに合わせて同位置で切断する
        cut = rest.find(" #")
        if cut != -1:
            rest = rest[:cut]
        return rest.strip()
    return ""


def categorize(relpath):
    """相対 path から分類 (= skills / agents / docs / scripts / other) を返す。"""
    parts = relpath.replace("\\", "/").split("/")
    top = parts[0]
    if top in ("skills", "agents", "docs", "scripts"):
        return top
    return "other"


def collect_files(root):
    """走査対象ファイルを集める。

    - skills/*/SKILL.md
    - agents/*.md
    - docs/**/*.md (再帰、 wip / diagrams 含む)
    - scripts/**/*.py (再帰、 __pycache__ 除外)
    """
    patterns = [
        os.path.join(root, "skills", "*", "SKILL.md"),
        os.path.join(root, "agents", "*.md"),
        os.path.join(root, "docs", "**", "*.md"),
        os.path.join(root, "scripts", "**", "*.py"),
    ]
    found = set()
    for pat in patterns:
        for path in glob.glob(pat, recursive=True):
            norm = os.path.normpath(path)
            if "__pycache__" in norm.replace("\\", "/").split("/"):
                continue
            found.add(norm)
    return sorted(found)


def analyze(root):
    """各ファイルを計測して dict の list で返す。"""
    results = []
    for path in collect_files(root):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                content = fp.read()
        except (OSError, UnicodeDecodeError) as e:
            print("WARN: skip {} ({})".format(path, e), file=sys.stderr)
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        n_chars, n_ascii, n_nonascii, est = estimate_tokens(content)
        n_lines = content.count("\n") + 1
        category = categorize(rel)
        # description は skill / agent のみ意味を持つ
        desc = extract_description(content) if category in ("skills", "agents") else ""
        results.append({
            "file": rel,
            "category": category,
            "lines": n_lines,
            "chars": n_chars,
            "ascii": n_ascii,
            "nonascii": n_nonascii,
            "tokens": est,
            "desc_chars": len(desc),
        })
    return results


def fmt_pct(value, budget):
    """budget 比を +XXX% / OK 文字列にする。"""
    if value > budget:
        return "+{:.0f}%".format((value - budget) / budget * 100)
    return "OK"


def print_table(results):
    results_sorted = sorted(results, key=lambda r: r["tokens"], reverse=True)

    print("=== 全ファイル (= token 降順) ===")
    hdr = "{:<44}{:>6}{:>8}{:>8}{:>8}{:>8}{:>9}"
    print(hdr.format("file", "lines", "chars", "ascii", "ja", "~tokens", "desc_ch"))
    print("-" * 91)
    row = "{:<44}{:>6}{:>8}{:>8}{:>8}{:>8}{:>9}"
    for r in results_sorted:
        desc_col = r["desc_chars"] if r["category"] in ("skills", "agents") else "-"
        print(row.format(
            r["file"][:44], r["lines"], r["chars"],
            r["ascii"], r["nonascii"], r["tokens"], desc_col,
        ))
    print("-" * 91)
    print(row.format(
        "TOTAL",
        sum(r["lines"] for r in results),
        sum(r["chars"] for r in results),
        sum(r["ascii"] for r in results),
        sum(r["nonascii"] for r in results),
        sum(r["tokens"] for r in results),
        sum(r["desc_chars"] for r in results),
    ))

    print()
    print("=== 分類別集計 ===")
    cat_hdr = "{:<10}{:>7}{:>9}{:>11}"
    print(cat_hdr.format("category", "files", "lines", "~tokens"))
    print("-" * 37)
    for cat in ("skills", "agents", "docs", "scripts", "other"):
        group = [r for r in results if r["category"] == cat]
        if not group:
            continue
        print(cat_hdr.format(
            cat, len(group),
            sum(r["lines"] for r in group),
            sum(r["tokens"] for r in group),
        ))

    # === skill token: 業界上限 (2000) 比 ===
    skills = sorted(
        [r for r in results if r["category"] == "skills"],
        key=lambda r: r["tokens"], reverse=True,
    )
    if skills:
        print()
        print("=== skill token vs 業界上限 (= {} token) ===".format(SKILL_TOKEN_BUDGET))
        s_row = "{:<44}{:>8}{:>10}"
        print(s_row.format("skill", "~tokens", "vs budget"))
        print("-" * 62)
        for r in skills:
            print(s_row.format(r["file"][:44], r["tokens"], fmt_pct(r["tokens"], SKILL_TOKEN_BUDGET)))

    # === description char: 業界推奨 (130) 比 ===
    desc_items = sorted(
        [r for r in results if r["category"] in ("skills", "agents") and r["desc_chars"] > 0],
        key=lambda r: r["desc_chars"], reverse=True,
    )
    if desc_items:
        print()
        print("=== description char vs 業界推奨 (= {} char) ===".format(DESCRIPTION_CHAR_BUDGET))
        d_row = "{:<44}{:>9}{:>10}"
        print(d_row.format("file", "desc_ch", "vs budget"))
        print("-" * 63)
        for r in desc_items:
            print(d_row.format(r["file"][:44], r["desc_chars"], fmt_pct(r["desc_chars"], DESCRIPTION_CHAR_BUDGET)))

        # skill listing 全体の description budget 比
        skill_desc_total = sum(
            r["desc_chars"] for r in results if r["category"] == "skills"
        )
        print("-" * 63)
        print(d_row.format(
            "SKILL desc TOTAL (vs listing {})".format(LISTING_CHAR_BUDGET),
            skill_desc_total,
            fmt_pct(skill_desc_total, LISTING_CHAR_BUDGET),
        ))

    print()
    print("(注) token は cl100k_base 概算、 誤差 ±10%。 tiktoken 非依存。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.path.expanduser("~/code/harness"),
        help="走査対象の harness repo root (= default: ~/code/harness)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="table でなく JSON で結果を出力する",
    )
    args = parser.parse_args()

    root = os.path.abspath(os.path.expanduser(args.root))
    if not os.path.isdir(root):
        print("ERROR: root が存在しません: {}".format(root), file=sys.stderr)
        return 1

    results = analyze(root)
    if not results:
        print("WARN: 走査対象ファイルが 0 件でした (root={})".format(root), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_table(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
