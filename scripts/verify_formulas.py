#!/usr/bin/env python3
"""
verify_formulas.py — 公式内容验证脚本

用于验证转换后的markdown中的公式准确性。

使用方法:
    python verify_formulas.py <markdown_file>
    python verify_formulas.py --check-brackets <markdown_file>
    python verify_formulas.py --check-symbols <markdown_file>
"""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def extract_formulas(content: str) -> List[Dict]:
    """
    从markdown内容中提取所有公式
    """
    formulas = []

    # 提取display math ($$...$$)
    display_matches = re.finditer(r'\$\$(.*?)\$\$', content, re.DOTALL)
    for match in display_matches:
        formulas.append({
            'type': 'display',
            'content': match.group(1),
            'start': match.start(),
            'end': match.end(),
            'line_num': content[:match.start()].count('\n') + 1
        })

    # 提取inline math ($...$) - 排除$$
    inline_matches = re.finditer(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', content)
    for match in inline_matches:
        formulas.append({
            'type': 'inline',
            'content': match.group(1),
            'start': match.start(),
            'end': match.end(),
            'line_num': content[:match.start()].count('\n') + 1
        })

    return formulas


def check_bracket_matching(formula: str) -> List[str]:
    """
    检查括号匹配
    """
    issues = []

    # 检查圆括号
    if formula.count('(') != formula.count(')'):
        issues.append(f"圆括号不匹配: ({formula.count('(')}个'(' vs {formula.count(')')}个')')")

    # 检查花括号
    if formula.count('{') != formula.count('}'):
        issues.append(f"花括号不匹配: ({formula.count('{')}个'{{' vs {formula.count('}')}个'}}')")

    # 检查方括号
    if formula.count('[') != formula.count(']'):
        issues.append(f"方括号不匹配: ({formula.count('[')}个'[' vs {formula.count(']')}个']')")

    # 检查LaTeX环境匹配
    envs = ['bmatrix', 'pmatrix', 'matrix', 'cases', 'aligned', 'equation', 'align', 'gather']
    for env in envs:
        begin_count = len(re.findall(rf'\\begin\{{{env}\}}', formula))
        end_count = len(re.findall(rf'\\end\{{{env}\}}', formula))
        if begin_count != end_count:
            issues.append(f"LaTeX环境 {env} 不匹配: {begin_count}个'begin' vs {end_count}个'end'")

    return issues


def check_symbol_completeness(formula: str) -> List[str]:
    """
    检查符号完整性
    """
    issues = []

    # 检查常见下标模式
    # 正确: x_i, x_{ij}, x_{i,j}
    # 错误: x_i (当应该是x_{i}时)

    # 检查希腊字母是否完整
    greek_letters = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu', 'pi', 'sigma', 'phi', 'psi', 'omega']
    for letter in greek_letters:
        # 检查是否有不完整的希腊字母
        pattern = rf'\\{letter}(?![a-zA-Z{{}}])'
        matches = list(re.finditer(pattern, formula))
        for match in matches:
            # 如果后面没有花括号，可能是不完整的
            pos = match.end()
            if pos < len(formula) and formula[pos] not in ['{', ' ', ',', '.', ')', ']', '}', '+', '-', '*', '/']:
                # 这可能是正常的，比如 \alpha x
                pass

    # 检查是否有孤立的反斜杠
    if re.search(r'(?<!\\)\\(?!\\|[a-zA-Z{}()\[\]])', formula):
        issues.append("可能存在孤立的反斜杠")

    return issues


def check_latex_syntax(formula: str) -> List[str]:
    """
    检查LaTeX语法
    """
    issues = []

    # 检查常见语法错误
    # 1. 单反斜杠作为行分隔符（应该是\\）
    if re.search(r'(?<!\\)\\(?!\\|[a-zA-Z{}()\[\]])', formula):
        issues.append("可能存在单反斜杠行分隔符（应该是双反斜杠）")

    # 2. 检查分数格式
    frac_matches = list(re.finditer(r'\\frac\{([^}]*)\}\{([^}]*)\}', formula))
    for match in frac_matches:
        if not match.group(1) or not match.group(2):
            issues.append(f"分数格式不完整: \\frac{{{match.group(1)}}}{{{match.group(2)}}}")

    # 3. 检查根号格式
    sqrt_matches = list(re.finditer(r'\\sqrt\{([^}]*)\}', formula))
    for match in sqrt_matches:
        if not match.group(1):
            issues.append("根号格式不完整")

    # 4. 检查求和/积分格式
    sum_matches = list(re.finditer(r'\\sum\{([^}]*)\}', formula))
    for match in sum_matches:
        if not match.group(1):
            issues.append("求和格式不完整")

    return issues


def verify_formula_accuracy(markdown_file: str) -> Dict:
    """
    验证markdown文件中所有公式的准确性
    """
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    formulas = extract_formulas(content)
    results = {
        'total_formulas': len(formulas),
        'issues': [],
        'formulas_with_issues': []
    }

    for i, formula in enumerate(formulas):
        formula_issues = []

        # 检查括号匹配
        bracket_issues = check_bracket_matching(formula['content'])
        formula_issues.extend(bracket_issues)

        # 检查符号完整性
        symbol_issues = check_symbol_completeness(formula['content'])
        formula_issues.extend(symbol_issues)

        # 检查LaTeX语法
        syntax_issues = check_latex_syntax(formula['content'])
        formula_issues.extend(syntax_issues)

        if formula_issues:
            results['issues'].extend(formula_issues)
            results['formulas_with_issues'].append({
                'index': i + 1,
                'type': formula['type'],
                'line': formula['line_num'],
                'content': formula['content'][:100] + '...' if len(formula['content']) > 100 else formula['content'],
                'issues': formula_issues
            })

    return results


def generate_report(results: Dict) -> str:
    """
    生成验证报告
    """
    lines = []
    lines.append("=" * 60)
    lines.append("公式验证报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"总公式数: {results['total_formulas']}")
    lines.append(f"有问题的公式数: {len(results['formulas_with_issues'])}")
    lines.append("")

    if results['formulas_with_issues']:
        lines.append("问题详情:")
        lines.append("-" * 60)

        for formula_info in results['formulas_with_issues']:
            lines.append(f"\n公式 #{formula_info['index']} (行 {formula_info['line']}):")
            lines.append(f"  类型: {formula_info['type']}")
            lines.append(f"  内容: {formula_info['content']}")
            lines.append(f"  问题:")
            for issue in formula_info['issues']:
                lines.append(f"    - {issue}")
    else:
        lines.append("所有公式检查通过")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_formulas.py <markdown_file>")
        print("       python verify_formulas.py --check-brackets <markdown_file>")
        print("       python verify_formulas.py --check-symbols <markdown_file>")
        sys.exit(1)

    if sys.argv[1] == "--check-brackets":
        markdown_file = sys.argv[2]
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        formulas = extract_formulas(content)
        all_issues = []
        for formula in formulas:
            issues = check_bracket_matching(formula['content'])
            if issues:
                all_issues.extend(issues)
        if all_issues:
            print("括号匹配问题:")
            for issue in all_issues:
                print(f"  - {issue}")
        else:
            print("✓ 所有括号匹配正确")
        return

    if sys.argv[1] == "--check-symbols":
        markdown_file = sys.argv[2]
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        formulas = extract_formulas(content)
        all_issues = []
        for formula in formulas:
            issues = check_symbol_completeness(formula['content'])
            if issues:
                all_issues.extend(issues)
        if all_issues:
            print("符号完整性问题:")
            for issue in all_issues:
                print(f"  - {issue}")
        else:
            print("✓ 所有符号完整")
        return

    markdown_file = sys.argv[1]
    results = verify_formula_accuracy(markdown_file)
    report = generate_report(results)
    print(report)

    # 保存报告到文件
    report_path = Path(markdown_file).parent / "formula_verification_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
