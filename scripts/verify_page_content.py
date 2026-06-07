#!/usr/bin/env python3
"""
verify_page_content.py — Page-by-page content verification for pdf2md conversion.

Reads tracking.json and the generated markdown, then verifies that each page's
tracked content (equations, figures, tables, sections) actually appears in the
markdown. Reports missing or incomplete content per page.

Usage:
    python verify_page_content.py <output-dir>
    python verify_page_content.py <output-dir> --source-dir <source-dir>
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_tracking(output_dir: Path) -> dict:
    """Load tracking.json from the output directory."""
    tracking_path = output_dir / "tracking.json"
    if not tracking_path.exists():
        print(f"ERROR: tracking.json not found at {tracking_path}")
        return {}
    with open(tracking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_markdown(output_dir: Path) -> str:
    """Load the main markdown file from the output directory."""
    md_files = list(output_dir.glob("*.md"))
    if not md_files:
        print("ERROR: No markdown file found in output directory")
        return ""
    with open(md_files[0], "r", encoding="utf-8") as f:
        return f.read()


def check_page_equations(page_data: dict, md_content: str) -> List[str]:
    """Check that all equations tracked for this page appear in the markdown."""
    issues = []
    equations = page_data.get("equations", [])

    for eq_tag in equations:
        # eq_tag might be "(1-1)" or "1-1" or just "1"
        tag_clean = eq_tag.strip("()")
        # Search for the tag in markdown
        if f"\\tag{{{tag_clean}}}" not in md_content:
            # Also try with parentheses
            if f"\\tag{{({tag_clean})}}" not in md_content:
                issues.append(f"公式 {eq_tag} 在markdown中未找到")

    return issues


def check_page_figures(page_data: dict, md_content: str) -> List[str]:
    """Check that all figures tracked for this page appear in the markdown."""
    issues = []
    figures = page_data.get("figures", [])

    for fig_name in figures:
        # fig_name might be "图1-4 飞机典型操纵机构示意图" or "图1-4"
        if fig_name not in md_content:
            # Try matching just the figure number
            m = re.search(r'图(\d+)-(\d+)', fig_name)
            if m:
                fig_id = f"图{m.group(1)}-{m.group(2)}"
                if fig_id not in md_content:
                    issues.append(f"图表 {fig_name} 在markdown中未找到")
            else:
                issues.append(f"图表 {fig_name} 在markdown中未找到")

    return issues


def check_page_tables(page_data: dict, md_content: str) -> List[str]:
    """Check that all tables tracked for this page appear in the markdown."""
    issues = []
    tables = page_data.get("tables", [])

    for tbl_name in tables:
        if tbl_name not in md_content:
            m = re.search(r'表(\d+)-(\d+)', tbl_name)
            if m:
                tbl_id = f"表{m.group(1)}-{m.group(2)}"
                if tbl_id not in md_content:
                    issues.append(f"表格 {tbl_name} 在markdown中未找到")
            else:
                issues.append(f"表格 {tbl_name} 在markdown中未找到")

    return issues


def check_page_sections(page_data: dict, md_content: str) -> List[str]:
    """Check that section headings tracked for this page appear in the markdown."""
    issues = []
    section = page_data.get("section", "")

    if section:
        # Check if the section title appears in markdown
        # Try exact match first
        if section not in md_content:
            # Try partial match (section number)
            m = re.search(r'(\d+(?:\.\d+)*)', section)
            if m:
                section_num = m.group(1)
                # Look for heading with this number
                heading_pattern = rf'^#+\s*.*{re.escape(section_num)}'
                if not re.search(heading_pattern, md_content, re.MULTILINE):
                    issues.append(f"章节标题 '{section}' 在markdown中未找到")

    return issues


def check_page_word_count(page_data: dict, md_content: str, page_num: int) -> List[str]:
    """Rough check that the page has a reasonable amount of content."""
    issues = []
    expected_count = page_data.get("word_count_approx", 0)

    if expected_count > 0:
        # This is a rough heuristic — we can't precisely measure per-page content
        # without page markers in the markdown, but we can flag obviously empty pages
        pass  # Word count is tracked but hard to verify without page markers

    return issues


def check_summarization_shortcuts(md_content: str) -> Dict:
    """Check for summarization shortcuts in the entire markdown."""
    issues = []
    shortcuts = {
        "等等": 2,
        "etc.": 2,
        "省略": 1,
        "略": 1,
        "以此类推": 1,
        "之类": 1,
        "...": 3,  # ... is common in markdown, so higher threshold
    }

    for shortcut, max_count in shortcuts.items():
        count = md_content.count(shortcut)
        if count > max_count:
            issues.append(f"发现 '{shortcut}' {count}次（阈值: {max_count}）——可能存在内容省略")

    return issues


def check_heading_hierarchy(md_content: str) -> List[str]:
    """Check that heading hierarchy is reasonable (no huge jumps)."""
    issues = []
    headings = re.findall(r'^(#{1,6})\s+(.+)$', md_content, re.MULTILINE)

    prev_level = 0
    for hashes, title in headings:
        level = len(hashes)
        if prev_level > 0 and level > prev_level + 1:
            issues.append(f"标题层级跳跃: H{prev_level} -> H{level} ('{title}')")
        prev_level = level

    return issues


def check_latex_rendering_issues(md_content: str) -> List[str]:
    """Check for common LaTeX rendering issues in the markdown."""
    issues = []

    # Check for $$...$$ blocks that might be empty
    empty_display = re.findall(r'\$\$\s*\$\$', md_content)
    if empty_display:
        issues.append(f"发现 {len(empty_display)} 个空的 display math 块")

    # Check for $...$ that might be empty
    empty_inline = re.findall(r'(?<!\$)\$(?!\$)\s*(?<!\$)\$(?!\$)', md_content)
    if empty_inline:
        issues.append(f"发现 {len(empty_inline)} 个空的 inline math 块")

    # Check for unclosed $$ blocks
    double_dollar_count = md_content.count('$$')
    if double_dollar_count % 2 != 0:
        issues.append(f"$$ 标记数量为奇数 ({double_dollar_count})，可能存在未闭合的 display math")

    # Check for LaTeX commands outside of math mode
    # This is tricky — we'd need to parse math regions properly
    # For now, just check for obvious cases

    return issues


def verify_all_pages(tracking: dict, md_content: str) -> Tuple[Dict[int, List[str]], List[str]]:
    """Verify content for all pages. Returns per-page issues and global issues."""
    per_page_issues = {}
    global_issues = []

    processed = tracking.get("processed_pages", [])

    for page_data in processed:
        if not isinstance(page_data, dict):
            continue

        page_num = page_data.get("page", 0)
        status = page_data.get("status", "")

        if status != "complete":
            per_page_issues.setdefault(page_num, []).append(f"页面状态为 '{status}'，不是 'complete'")

        page_issues = []
        page_issues.extend(check_page_equations(page_data, md_content))
        page_issues.extend(check_page_figures(page_data, md_content))
        page_issues.extend(check_page_tables(page_data, md_content))
        page_issues.extend(check_page_sections(page_data, md_content))

        if page_issues:
            per_page_issues[page_num] = page_issues

    # Global checks
    global_issues.extend(check_summarization_shortcuts(md_content))
    global_issues.extend(check_heading_hierarchy(md_content))
    global_issues.extend(check_latex_rendering_issues(md_content))

    return per_page_issues, global_issues


def generate_report(per_page_issues: Dict[int, List[str]], global_issues: List[str],
                    tracking: dict, md_content: str) -> str:
    """Generate a detailed verification report."""
    lines = []
    lines.append("=" * 60)
    lines.append("逐页内容验证报告")
    lines.append("=" * 60)
    lines.append("")

    total_pages = tracking.get("total_pages", 0)
    processed = tracking.get("processed_pages", [])
    equations = tracking.get("equations_found", [])
    figures = tracking.get("figures_found", [])
    tables = tracking.get("tables_found", [])

    lines.append(f"总页数: {total_pages}")
    lines.append(f"已处理页数: {len(processed)}")
    lines.append(f"跟踪的公式数: {len(equations)}")
    lines.append(f"跟踪的图表数: {len(figures)}")
    lines.append(f"跟踪的表格数: {len(tables)}")
    lines.append(f"Markdown字符数: {len(md_content)}")
    lines.append("")

    # Summary
    pages_with_issues = len(per_page_issues)
    total_page_issues = sum(len(v) for v in per_page_issues.values())

    if not per_page_issues and not global_issues:
        lines.append("RESULT: ALL PAGES VERIFIED — NO ISSUES FOUND")
    else:
        if pages_with_issues > 0:
            lines.append(f"有问题的页面: {pages_with_issues}/{len(processed)}")
            lines.append(f"页面问题总数: {total_page_issues}")
            lines.append("")

            # Sort by page number
            for page_num in sorted(per_page_issues.keys()):
                issues = per_page_issues[page_num]
                lines.append(f"--- 第{page_num}页 ({len(issues)}个问题) ---")
                for issue in issues:
                    lines.append(f"  [FAIL] {issue}")
                lines.append("")

        if global_issues:
            lines.append(f"--- 全局问题 ({len(global_issues)}个) ---")
            for issue in global_issues:
                lines.append(f"  [FAIL] {issue}")
            lines.append("")

    # Pages with no issues
    all_page_nums = {p["page"] for p in processed if isinstance(p, dict)}
    clean_pages = all_page_nums - set(per_page_issues.keys())
    if clean_pages and len(clean_pages) <= 20:
        lines.append(f"验证通过的页面: {sorted(clean_pages)}")
    elif clean_pages:
        lines.append(f"验证通过的页面: {len(clean_pages)}页")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_page_content.py <output-dir> [--source-dir <source-dir>]")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"ERROR: Directory does not exist: {output_dir}")
        sys.exit(1)

    # Load data
    tracking = load_tracking(output_dir)
    if not tracking:
        sys.exit(1)

    md_content = load_markdown(output_dir)
    if not md_content:
        sys.exit(1)

    # Run verification
    per_page_issues, global_issues = verify_all_pages(tracking, md_content)

    # Generate report
    report = generate_report(per_page_issues, global_issues, tracking, md_content)
    print(report)

    # Save report
    report_path = output_dir / "page_content_verification_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存到: {report_path}")

    # Exit with error if there are issues
    has_errors = bool(per_page_issues) or any("省略" in i or "缺失" in i for i in global_issues)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
