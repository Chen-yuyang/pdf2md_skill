#!/usr/bin/env python3
"""
cross_validate.py — Cross-validation script for pdf2md conversion.

Compares source page images directory against the generated markdown to verify:
1. Every page in the source has corresponding content in the markdown
2. All tracked equations, figures, and tables appear in the markdown
3. No orphaned or duplicate equation tags
4. Content density per page is reasonable (no suspiciously empty pages)
5. Formula LaTeX syntax is valid

Usage:
    python cross_validate.py <source-dir> <markdown_file>
    python cross_validate.py <source-dir> <markdown_file> --tracking <tracking.json>
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_tracking(output_dir: Path) -> dict:
    """Load tracking.json from the output directory."""
    tracking_path = output_dir / "tracking.json"
    if not tracking_path.exists():
        return {}
    with open(tracking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_page_images(source_dir: Path) -> List[int]:
    """Extract page numbers from source image filenames."""
    pages = []
    for f in source_dir.glob("page-*.png"):
        m = re.search(r'page-(\d+)', f.name)
        if m:
            pages.append(int(m.group(1)))
    return sorted(pages)


def extract_formulas_from_markdown(content: str) -> List[Dict]:
    """Extract all formulas from markdown content with their line numbers."""
    formulas = []

    # Display math ($$...$$)
    for match in re.finditer(r'\$\$(.*?)\$\$', content, re.DOTALL):
        formulas.append({
            'type': 'display',
            'content': match.group(1),
            'line_num': content[:match.start()].count('\n') + 1
        })

    # Inline math ($...$)
    for match in re.finditer(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', content):
        formulas.append({
            'type': 'inline',
            'content': match.group(1),
            'line_num': content[:match.start()].count('\n') + 1
        })

    return formulas


def extract_equation_tags(content: str) -> List[str]:
    """Extract all equation tags from markdown."""
    return re.findall(r'\\tag\{([^}]+)\}', content)


def extract_figure_refs(content: str) -> List[str]:
    """Extract all figure references from markdown."""
    return re.findall(r'图(\d+)-(\d+)', content)


def extract_table_refs(content: str) -> List[str]:
    """Extract all table references from markdown."""
    return re.findall(r'表(\d+)-(\d+)', content)


def check_formula_syntax(formulas: List[Dict]) -> List[Dict]:
    """Check LaTeX syntax for all formulas."""
    issues = []

    for formula in formulas:
        content = formula['content']
        line = formula['line_num']
        formula_issues = []

        # Bracket matching
        for open_b, close_b, name in [('(', ')', '圆括号'), ('{', '}', '花括号'), ('[', ']', '方括号')]:
            if content.count(open_b) != content.count(close_b):
                formula_issues.append(f"{name}不匹配: {content.count(open_b)}个'{open_b}' vs {content.count(close_b)}个'{close_b}'")

        # LaTeX environment matching
        envs = ['bmatrix', 'pmatrix', 'matrix', 'cases', 'aligned', 'equation', 'align', 'gather']
        for env in envs:
            begin_count = len(re.findall(rf'\\begin\{{{env}\}}', content))
            end_count = len(re.findall(rf'\\end\{{{env}\}}', content))
            if begin_count != end_count:
                formula_issues.append(f"LaTeX环境 {env} 不匹配: {begin_count}个begin vs {end_count}个end")

        # Broken row separators in environments
        for env in ['bmatrix', 'pmatrix', 'cases', 'aligned']:
            env_match = re.search(rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}', content, re.DOTALL)
            if env_match:
                inner = env_match.group(1)
                if re.search(r'(?<!\\)\\(?!\\|[a-zA-Z{}])', inner):
                    formula_issues.append(f"\\begin{{{env}}}中存在单反斜杠行分隔符（应为双反斜杠）")

        # Incomplete fraction
        if re.search(r'\\frac\{\s*\}', content) or re.search(r'\\frac\{[^}]*\}\{\s*\}', content):
            formula_issues.append("分数格式不完整")

        # Incomplete sqrt
        if re.search(r'\\sqrt\{\s*\}', content):
            formula_issues.append("根号格式不完整")

        if formula_issues:
            issues.append({
                'line': line,
                'type': formula['type'],
                'content': content[:80] + ('...' if len(content) > 80 else ''),
                'issues': formula_issues
            })

    return issues


def check_page_content_density(content: str, tracking: dict) -> List[Dict]:
    """Check that each processed page has reasonable content in the markdown."""
    issues = []
    processed = tracking.get("processed_pages", [])

    # Split markdown into rough page sections using tracking info
    # We check that tracked equations/figures/tables actually appear in the content
    tracked_equations = tracking.get("equations_found", [])
    tracked_figures = tracking.get("figures_found", [])
    tracked_tables = tracking.get("tables_found", [])

    # Check equations
    md_tags = extract_equation_tags(content)
    for eq in tracked_equations:
        tag = eq.get("tag", "") if isinstance(eq, dict) else str(eq)
        if tag and tag not in md_tags:
            issues.append({
                'type': 'missing_equation',
                'message': f"跟踪的公式 {tag} 在markdown中未找到"
            })

    # Check for duplicate equation tags
    if len(md_tags) != len(set(md_tags)):
        from collections import Counter
        dupes = [t for t, c in Counter(md_tags).items() if c > 1]
        issues.append({
            'type': 'duplicate_equations',
            'message': f"重复的公式标签: {dupes}"
        })

    # Check figures
    md_figures = extract_figure_refs(content)
    md_fig_strs = [f"{c}-{n}" for c, n in md_figures]
    for fig in tracked_figures:
        name = fig.get("name", "") if isinstance(fig, dict) else str(fig)
        m = re.search(r'图(\d+)-(\d+)', name)
        if m:
            fig_id = f"{m.group(1)}-{m.group(2)}"
            if fig_id not in md_fig_strs:
                issues.append({
                    'type': 'missing_figure',
                    'message': f"跟踪的图表 {name} 在markdown中未找到"
                })

    # Check tables
    md_tables = extract_table_refs(content)
    md_tbl_strs = [f"{c}-{n}" for c, n in md_tables]
    for tbl in tracked_tables:
        name = tbl.get("name", "") if isinstance(tbl, dict) else str(tbl)
        m = re.search(r'表(\d+)-(\d+)', name)
        if m:
            tbl_id = f"{m.group(1)}-{m.group(2)}"
            if tbl_id not in md_tbl_strs:
                issues.append({
                    'type': 'missing_table',
                    'message': f"跟踪的表格 {name} 在markdown中未找到"
                })

    # Check for summarization shortcuts
    shortcuts = ["等等", "etc.", "...", "之类", "以此类推", "省略", "略"]
    for shortcut in shortcuts:
        count = content.count(shortcut)
        if count > 2:
            issues.append({
                'type': 'summarization',
                'message': f"发现疑似省略标记 '{shortcut}' {count}次——可能存在内容遗漏"
            })

    return issues


def check_source_vs_markdown(source_dir: Path, content: str, tracking: dict) -> List[Dict]:
    """Compare source page images against markdown content."""
    issues = []

    source_pages = extract_page_images(source_dir)
    processed = tracking.get("processed_pages", [])
    processed_page_nums = {p["page"] for p in processed if isinstance(p, dict)}

    # Check for missing pages
    missing = set(source_pages) - processed_page_nums
    if missing:
        issues.append({
            'type': 'missing_pages',
            'message': f"以下页面未在tracking.json中标记为已处理: {sorted(missing)}"
        })

    # Check for extra pages in tracking
    extra = processed_page_nums - set(source_pages)
    if extra:
        issues.append({
            'type': 'extra_pages',
            'message': f"tracking.json中包含源目录中不存在的页面: {sorted(extra)}"
        })

    # Check markdown length vs page count
    if source_pages:
        chars_per_page = len(content) / len(source_pages)
        if chars_per_page < 200:
            issues.append({
                'type': 'low_content',
                'message': f"平均每页仅 {chars_per_page:.0f} 字符，内容可能不完整"
            })

    return issues


def generate_report(all_issues: List[Dict], stats: Dict) -> str:
    """Generate a cross-validation report."""
    lines = []
    lines.append("=" * 60)
    lines.append("交叉验证报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"源目录: {stats.get('source_dir', 'N/A')}")
    lines.append(f"Markdown文件: {stats.get('markdown_file', 'N/A')}")
    lines.append(f"源页面数: {stats.get('source_pages', 0)}")
    lines.append(f"已处理页面数: {stats.get('processed_pages', 0)}")
    lines.append(f"Markdown字符数: {stats.get('markdown_chars', 0)}")
    lines.append(f"公式总数: {stats.get('total_formulas', 0)}")
    lines.append(f"公式标签数: {stats.get('total_tags', 0)}")
    lines.append("")

    if not all_issues:
        lines.append("RESULT: ALL CHECKS PASSED")
    else:
        # Group by type
        by_type = {}
        for issue in all_issues:
            t = issue.get('type', 'unknown')
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(issue)

        type_names = {
            'missing_equation': '缺失的公式',
            'duplicate_equations': '重复的公式标签',
            'missing_figure': '缺失的图表',
            'missing_table': '缺失的表格',
            'summarization': '疑似省略',
            'missing_pages': '缺失的页面',
            'extra_pages': '多余的页面',
            'low_content': '内容过少',
            'formula_syntax': '公式语法问题'
        }

        for issue_type, issues in by_type.items():
            name = type_names.get(issue_type, issue_type)
            lines.append(f"\n{name} ({len(issues)}个):")
            for issue in issues:
                lines.append(f"  - {issue['message']}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python cross_validate.py <source-dir> <markdown_file> [--tracking <tracking.json>]")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    markdown_file = Path(sys.argv[2])

    if not source_dir.exists():
        print(f"ERROR: Source directory does not exist: {source_dir}")
        sys.exit(1)

    if not markdown_file.exists():
        print(f"ERROR: Markdown file does not exist: {markdown_file}")
        sys.exit(1)

    # Load tracking.json
    tracking = {}
    if "--tracking" in sys.argv:
        idx = sys.argv.index("--tracking")
        if idx + 1 < len(sys.argv):
            tracking_path = Path(sys.argv[idx + 1])
            if tracking_path.exists():
                with open(tracking_path, "r", encoding="utf-8") as f:
                    tracking = json.load(f)

    # Also try to find tracking.json in the markdown file's parent directory
    if not tracking:
        tracking_path = markdown_file.parent / "tracking.json"
        if tracking_path.exists():
            with open(tracking_path, "r", encoding="utf-8") as f:
                tracking = json.load(f)

    # Read markdown
    with open(markdown_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Run all checks
    all_issues = []

    # 1. Source vs markdown comparison
    all_issues.extend(check_source_vs_markdown(source_dir, content, tracking))

    # 2. Page content density and tracked element verification
    all_issues.extend(check_page_content_density(content, tracking))

    # 3. Formula syntax check
    formulas = extract_formulas_from_markdown(content)
    syntax_issues = check_formula_syntax(formulas)
    if syntax_issues:
        for issue in syntax_issues:
            all_issues.append({
                'type': 'formula_syntax',
                'message': f"行 {issue['line']}: {', '.join(issue['issues'])}"
            })

    # Generate stats
    source_pages = extract_page_images(source_dir)
    stats = {
        'source_dir': str(source_dir),
        'markdown_file': str(markdown_file),
        'source_pages': len(source_pages),
        'processed_pages': len(tracking.get("processed_pages", [])),
        'markdown_chars': len(content),
        'total_formulas': len(formulas),
        'total_tags': len(extract_equation_tags(content))
    }

    # Generate report
    report = generate_report(all_issues, stats)
    print(report)

    # Save report
    report_path = markdown_file.parent / "cross_validation_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存到: {report_path}")

    # Exit with error if there are issues
    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
