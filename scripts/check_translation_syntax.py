#!/usr/bin/env python3
"""
Translation syntax checker for Gemini-translated .qmd files.

Detects common syntax breakages introduced by Gemini translation:
- Cross-reference glued to CJK characters (@fig-xxx中文)
- Fence div unclosed (::: mismatched stack)
- Shortcode incorrectly wrapped in ::: fence div
- ::: closing marker glued to content lines
- TikZ code block closing marker glued to description text

Usage:
    python3 check_translation_syntax.py -f chapter.qmd
    python3 check_translation_syntax.py -d output/book/contents/
    python3 check_translation_syntax.py -d output/book/contents/ --strict --quiet

Exit codes:
    0: No issues found
    1: Issues found (only with --strict)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


# ANSI colors
class C:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def find_qmd_files(path: Path) -> List[Path]:
    if path.is_file() and path.suffix == ".qmd":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.qmd"))
    return []


# ---------------------------------------------------------------------------
# Check 1: Cross-reference glued to CJK characters
# ---------------------------------------------------------------------------
_XREF_CJK_PATTERN = re.compile(
    r"(@(?:sec|fig|tbl|eq|lst)-[a-zA-Z0-9_-]+)[\u4e00-\u9fff]"
)
_CITATION_CJK_PATTERN = re.compile(
    r"(\[[\]@][^\]]*\])([\u4e00-\u9fff])"
)


def check_xref_glued(lines: List[str]) -> List[Tuple[int, str, str]]:
    """Detect @fig-xxx中文, [@cite]中文 patterns."""
    issues = []
    in_code = False
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        for pat, desc in [
            (_XREF_CJK_PATTERN, "cross-reference"),
            (_CITATION_CJK_PATTERN, "citation"),
        ]:
            m = pat.search(stripped)
            if m:
                issues.append((i, desc, stripped.strip()))
    return issues


# ---------------------------------------------------------------------------
# Check 2: Fence div pairing (:::)
# ---------------------------------------------------------------------------
def check_fence_div(lines: List[str]) -> List[Tuple[int, str, str]]:
    """Stack-based fence div pairing. Skips code blocks."""
    issues = []
    in_code = False
    stack = []  # (line_num, content)

    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        if stripped.startswith(":::"):
            rest = stripped[3:].strip()
            if rest == "":
                # Closing fence
                if stack:
                    stack.pop()
                else:
                    issues.append((i, "unmatched-closing", stripped.strip()))
            elif rest.startswith("{") or rest.startswith("{{"):
                stack.append((i, stripped.strip()))

    for ln, content in stack:
        issues.append((ln, "unclosed-opening", content))

    return issues


# ---------------------------------------------------------------------------
# Check 3: Shortcode incorrectly wrapped in :::
# ---------------------------------------------------------------------------
_SHORTCODE_IN_FENCE = re.compile(r"^:::\s*\{\{<")


def check_shortcode_wrapped(lines: List[str]) -> List[Tuple[int, str, str]]:
    """Detect ::: lines followed by {{< shortcode >}} on same or next line."""
    issues = []
    in_code = False
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        if _SHORTCODE_IN_FENCE.match(stripped):
            issues.append((i, "shortcode-in-fence", stripped.strip()))
    return issues


# ---------------------------------------------------------------------------
# Check 4: ::: glued to content lines
# ---------------------------------------------------------------------------
_GLUED_CLOSING = re.compile(r"[^\s]:::(?:\s*$)")
_GLUED_CLOSING_WITH_CONTENT = re.compile(r"^:::\s+\S")


def check_closing_glued(lines: List[str]) -> List[Tuple[int, str, str]]:
    """Detect ::: closing markers glued to adjacent content."""
    issues = []
    in_code = False
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        # Case: content line ending with ::: (e.g. "![](img.png) :::")
        if _GLUED_CLOSING.search(stripped) and not stripped.startswith(":::"):
            issues.append((i, "closing-glued-to-content", stripped.strip()))

        # Case: ::: followed by non-empty content on same line (but not ::: {#...})
        if _GLUED_CLOSING_WITH_CONTENT.match(stripped) and not stripped.startswith(":::{{"):
            # Allow valid opening fences like ::: {#fig-xxx .class}
            rest = stripped[3:].strip()
            if not rest.startswith("{"):
                issues.append((i, "closing-with-content", stripped.strip()))
    return issues


# ---------------------------------------------------------------------------
# Check 5: TikZ code block closing marker glued to description
# ---------------------------------------------------------------------------
def check_tikz_closing_glued(lines: List[str]) -> List[Tuple[int, str, str]]:
    """Detect ``` closing markers glued to non-blank content in TikZ blocks."""
    issues = []
    in_code = False
    code_lang = ""
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            if in_code:
                # Closing code block — check for glued content
                rest = stripped[3:].strip()
                if rest:
                    # ``` followed by non-whitespace = glued
                    issues.append((i, "tikz-closing-glued", stripped.strip()))
                in_code = False
                code_lang = ""
            else:
                # Opening code block
                lang = stripped[3:].strip().lower()
                in_code = True
                code_lang = lang
            continue

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def check_file(filepath: Path, quiet: bool = False) -> int:
    """Run all checks on a single file. Returns issue count."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 0

    lines = content.splitlines()

    all_issues = []

    # Run checks
    xref_issues = check_xref_glued(lines)
    for ln, desc, ctx in xref_issues:
        all_issues.append((ln, f"[xref-glued] {desc}", ctx))

    fence_issues = check_fence_div(lines)
    for ln, desc, ctx in fence_issues:
        all_issues.append((ln, f"[fence-div] {desc}", ctx))

    shortcode_issues = check_shortcode_wrapped(lines)
    for ln, desc, ctx in shortcode_issues:
        all_issues.append((ln, f"[shortcode] {desc}", ctx))

    closing_issues = check_closing_glued(lines)
    for ln, desc, ctx in closing_issues:
        all_issues.append((ln, f"[closing-glued] {desc}", ctx))

    tikz_issues = check_tikz_closing_glued(lines)
    for ln, desc, ctx in tikz_issues:
        all_issues.append((ln, f"[tikz-closing] {desc}", ctx))

    if all_issues:
        try:
            rel = filepath.relative_to(Path.cwd())
        except ValueError:
            rel = filepath

        if quiet:
            print(f"{rel}: {len(all_issues)} issue(s)")
        else:
            print(f"\n{C.RED}{C.BOLD}{rel} ({len(all_issues)} issue(s)):{C.RESET}")
            for ln, desc, ctx in sorted(all_issues):
                ctx_trunc = ctx[:120] + ("..." if len(ctx) > 120 else "")
                print(f"  L{ln}: {C.YELLOW}{desc}{C.RESET}  | {ctx_trunc}")

    return len(all_issues)


def main():
    parser = argparse.ArgumentParser(
        description="Check translation syntax issues in .qmd files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Checks:
  [xref-glued]     Cross-reference @fig-xxx glued to CJK characters
  [fence-div]      Fence div ::: unclosed or unmatched
  [shortcode]      Shortcode {{< >}} incorrectly wrapped in :::
  [closing-glued]  ::: closing marker glued to content lines
  [tikz-closing]   TikZ code block ``` closing marker glued to description

Examples:
  %(prog)s -f chapter.qmd
  %(prog)s -d output/book/contents/ --strict
  %(prog)s -d output/book/contents/ --strict --quiet
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Check a single .qmd file")
    group.add_argument("-d", "--dir", help="Recursively check all .qmd files in directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any issues found (for CI/CD)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Minimal output"
    )

    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        files = find_qmd_files(Path(args.dir))

    if not files:
        print("No .qmd files found.", file=sys.stderr)
        sys.exit(1)

    total_issues = 0
    files_with_issues = 0

    for f in files:
        count = check_file(f, quiet=args.quiet)
        if count > 0:
            total_issues += count
            files_with_issues += 1

    # Summary
    if total_issues == 0:
        if not args.quiet:
            print(
                f"{C.GREEN}All checks passed.{C.RESET} "
                f"Scanned {len(files)} file(s)."
            )
        sys.exit(0)
    else:
        print(
            f"\n{C.RED}{total_issues} issue(s) in {files_with_issues} file(s).{C.RESET}"
        )
        if args.strict:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
