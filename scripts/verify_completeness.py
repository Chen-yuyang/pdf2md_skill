#!/usr/bin/env python3
"""
verify_completeness.py — Verify completeness of pdf2md conversion output.

Reads tracking.json and the generated markdown file, then checks:
1. All pages are marked complete
2. Section numbering is sequential
3. Equation numbering is sequential per chapter
4. Figure numbering is sequential
5. Table numbering is sequential
6. Markdown file contains expected content

Usage:
    python verify_completeness.py <output-dir>
"""

import json
import os
import re
import sys
from pathlib import Path


def load_tracking(output_dir: Path) -> dict:
    tracking_path = output_dir / "tracking.json"
    if not tracking_path.exists():
        print(f"ERROR: tracking.json not found at {tracking_path}")
        return {}
    with open(tracking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_page_completeness(tracking: dict) -> list:
    """Check all pages are marked complete."""
    issues = []
    processed = tracking.get("processed_pages", [])
    total = tracking.get("total_pages", 0)

    if total == 0:
        issues.append("WARNING: total_pages is 0")
        return issues

    processed_pages = {p["page"] for p in processed if isinstance(p, dict)}
    missing = set(range(1, total + 1)) - processed_pages

    if missing:
        issues.append(f"MISSING PAGES: {sorted(missing)}")

    incomplete = [p for p in processed if isinstance(p, dict) and p.get("status") != "complete"]
    if incomplete:
        issues.append(f"INCOMPLETE PAGES: {[p['page'] for p in incomplete]}")

    return issues


def check_section_numbering(tracking: dict) -> list:
    """Check section numbering is sequential."""
    issues = []
    sections = tracking.get("sections_found", [])

    if not sections:
        issues.append("WARNING: No sections found in tracking")
        return issues

    # Extract section numbers from headings
    section_numbers = []
    for s in sections:
        if isinstance(s, dict):
            title = s.get("title", "")
        else:
            title = str(s)

        # Match patterns like "1.1", "1.2.3", "第1章", etc.
        m = re.search(r"(\d+(?:\.\d+)*)", title)
        if m:
            section_numbers.append(m.group(1))

    # Check for gaps in numbering at each level
    if section_numbers:
        for level in range(1, 4):  # Check up to 3 levels deep
            nums_at_level = []
            for sn in section_numbers:
                parts = sn.split(".")
                if len(parts) >= level:
                    try:
                        nums_at_level.append(int(parts[level - 1]))
                    except ValueError:
                        pass

            if nums_at_level:
                expected = list(range(1, max(nums_at_level) + 1))
                actual = sorted(set(nums_at_level))
                gaps = set(expected) - set(actual)
                if gaps:
                    issues.append(f"SECTION NUMBER GAP at level {level}: missing {sorted(gaps)}")

    return issues


def check_equation_numbering(tracking: dict) -> list:
    """Check equation numbering is sequential per chapter."""
    issues = []
    equations = tracking.get("equations_found", [])

    if not equations:
        issues.append("WARNING: No equations found in tracking")
        return issues

    # Group equations by chapter
    chapters = {}
    for eq in equations:
        if isinstance(eq, dict):
            tag = eq.get("tag", "")
        else:
            tag = str(eq)

        # Match patterns like (1-1), (2-13), etc.
        m = re.match(r"\((\d+)-(\d+)\)", tag)
        if m:
            chapter = m.group(1)
            num = int(m.group(2))
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(num)

    for chapter, nums in sorted(chapters.items()):
        nums_sorted = sorted(set(nums))
        expected = list(range(1, max(nums_sorted) + 1))
        gaps = set(expected) - set(nums_sorted)
        if gaps:
            issues.append(f"EQUATION NUMBER GAP in chapter {chapter}: missing {sorted(gaps)}")

        # Check for duplicates
        if len(nums) != len(set(nums)):
            from collections import Counter
            dupes = [n for n, c in Counter(nums).items() if c > 1]
            issues.append(f"DUPLICATE EQUATION NUMBERS in chapter {chapter}: {dupes}")

    return issues


def check_figure_numbering(tracking: dict) -> list:
    """Check figure numbering is sequential."""
    issues = []
    figures = tracking.get("figures_found", [])

    if not figures:
        issues.append("WARNING: No figures found in tracking")
        return issues

    # Group by chapter
    chapters = {}
    for fig in figures:
        if isinstance(fig, dict):
            name = fig.get("name", "")
        else:
            name = str(fig)

        m = re.search(r"图(\d+)-(\d+)", name)
        if m:
            chapter = m.group(1)
            num = int(m.group(2))
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(num)

    for chapter, nums in sorted(chapters.items()):
        nums_sorted = sorted(set(nums))
        expected = list(range(1, max(nums_sorted) + 1))
        gaps = set(expected) - set(nums_sorted)
        if gaps:
            issues.append(f"FIGURE NUMBER GAP in chapter {chapter}: missing {sorted(gaps)}")

    return issues


def check_table_numbering(tracking: dict) -> list:
    """Check table numbering is sequential."""
    issues = []
    tables = tracking.get("tables_found", [])

    if not tables:
        # Tables are optional, don't warn
        return issues

    chapters = {}
    for tbl in tables:
        if isinstance(tbl, dict):
            name = tbl.get("name", "")
        else:
            name = str(tbl)

        m = re.search(r"表(\d+)-(\d+)", name)
        if m:
            chapter = m.group(1)
            num = int(m.group(2))
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(num)

    for chapter, nums in sorted(chapters.items()):
        nums_sorted = sorted(set(nums))
        expected = list(range(1, max(nums_sorted) + 1))
        gaps = set(expected) - set(nums_sorted)
        if gaps:
            issues.append(f"TABLE NUMBER GAP in chapter {chapter}: missing {sorted(gaps)}")

    return issues


def check_markdown_content(output_dir: Path, tracking: dict) -> list:
    """Check markdown file has content and matches tracking stats."""
    issues = []
    md_files = list(output_dir.glob("*.md"))

    if not md_files:
        issues.append("ERROR: No markdown file found in output directory")
        return issues

    md_path = md_files[0]
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check file is not empty
    if len(content.strip()) < 100:
        issues.append(f"ERROR: Markdown file is suspiciously short ({len(content)} chars)")
        return issues

    # Count equations in markdown
    md_equations = re.findall(r"\\tag\{(\d+-\d+)\}", content)
    tracked_equations = len(tracking.get("equations_found", []))
    if tracked_equations > 0 and len(md_equations) == 0:
        issues.append("WARNING: tracking shows equations but none found in markdown with \\tag")

    # Count figures in markdown
    md_figures = re.findall(r"图\d+-\d+", content)
    tracked_figures = len(tracking.get("figures_found", []))
    if tracked_figures > 0 and len(md_figures) == 0:
        issues.append("WARNING: tracking shows figures but none found in markdown")

    # Check for summarization shortcuts
    shortcuts = ["等等", "etc.", "...", "之类", "以此类推"]
    for shortcut in shortcuts:
        count = content.count(shortcut)
        if count > 3:
            issues.append(f"WARNING: Found '{shortcut}' {count} times — possible summarization")

    return issues


def check_matrix_formatting(output_dir: Path) -> list:
    """Check for broken matrix row separators in LaTeX."""
    issues = []
    md_files = list(output_dir.glob("*.md"))

    if not md_files:
        return issues

    md_path = md_files[0]
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for broken matrix separators
    env_names = ['bmatrix', 'pmatrix', 'matrix', 'cases', 'aligned']
    for env in env_names:
        pattern = rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}'
        matches = re.findall(pattern, content, flags=re.DOTALL)

        for match in matches:
            # Check for single \ used as row separator (not \\)
            if re.search(r'(?<!\\)\\(?!\\|[a-zA-Z{}])', match):
                issues.append(f"BROKEN MATRIX: Found single backslash as row separator in \\begin{{{env}}}")
                break  # One warning per environment type is enough

    # Check for LaTeX in table cells (potential rendering issues)
    lines = content.split('\n')
    in_table = False
    table_latex_count = 0

    for line in lines:
        if line.strip().startswith('|') and '|' in line[1:]:
            in_table = True
        elif in_table and not line.strip().startswith('|'):
            in_table = False

        if in_table and '\\begin{' in line:
            table_latex_count += 1

    if table_latex_count > 0:
        issues.append(f"WARNING: Found {table_latex_count} table cells with \\begin{{}} — may not render correctly")

    return issues


def generate_report(tracking: dict, all_issues: list) -> str:
    """Generate a human-readable verification report."""
    lines = []
    lines.append("=" * 60)
    lines.append("PDF2MD COMPLETENESS VERIFICATION REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Summary stats
    total = tracking.get("total_pages", 0)
    processed = len(tracking.get("processed_pages", []))
    equations = len(tracking.get("equations_found", []))
    figures = len(tracking.get("figures_found", []))
    tables = len(tracking.get("tables_found", []))
    sections = len(tracking.get("sections_found", []))
    batches = len(tracking.get("batches", []))

    lines.append(f"Total pages:       {total}")
    lines.append(f"Processed pages:   {processed}")
    lines.append(f"Sections found:    {sections}")
    lines.append(f"Equations found:   {equations}")
    lines.append(f"Figures found:     {figures}")
    lines.append(f"Tables found:      {tables}")
    lines.append(f"Batches:           {batches}")
    lines.append("")

    # Issues
    errors = [i for i in all_issues if i.startswith("ERROR")]
    warnings = [i for i in all_issues if i.startswith("WARNING")]
    passed = [i for i in all_issues if i.startswith("MISSING") or i.startswith("GAP") or i.startswith("INCOMPLETE") or i.startswith("DUPLICATE")]

    if not all_issues:
        lines.append("RESULT: ALL CHECKS PASSED")
    else:
        if errors:
            lines.append(f"ERRORS ({len(errors)}):")
            for e in errors:
                lines.append(f"  - {e}")
            lines.append("")
        if warnings:
            lines.append(f"WARNINGS ({len(warnings)}):")
            for w in warnings:
                lines.append(f"  - {w}")
            lines.append("")
        if passed:
            lines.append(f"FAILURES ({len(passed)}):")
            for p in passed:
                lines.append(f"  - {p}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_completeness.py <output-dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"ERROR: Directory does not exist: {output_dir}")
        sys.exit(1)

    tracking = load_tracking(output_dir)
    if not tracking:
        sys.exit(1)

    all_issues = []
    all_issues.extend(check_page_completeness(tracking))
    all_issues.extend(check_section_numbering(tracking))
    all_issues.extend(check_equation_numbering(tracking))
    all_issues.extend(check_figure_numbering(tracking))
    all_issues.extend(check_table_numbering(tracking))
    all_issues.extend(check_markdown_content(output_dir, tracking))
    all_issues.extend(check_matrix_formatting(output_dir))

    report = generate_report(tracking, all_issues)
    print(report)

    # Write report to file
    report_path = output_dir / "verification_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")

    # Exit with error code if there are failures
    has_errors = any(i.startswith("ERROR") or i.startswith("MISSING") or i.startswith("INCOMPLETE") for i in all_issues)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
