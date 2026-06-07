#!/usr/bin/env python3
"""
verify_formula_structure.py — 通用公式结构验证脚本

用于检查markdown中公式的语义正确性，检测常见的转录错误模式。

使用方法:
    python verify_formula_structure.py <markdown_file>
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict


def extract_formulas(content: str) -> List[Dict]:
    """从markdown内容中提取所有公式"""
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

    # 提取inline math ($...$)
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


def check_bracket_matching(formulas: List[Dict]) -> List[Dict]:
    """检查括号匹配"""
    issues = []

    for formula in formulas:
        content = formula['content']
        line = formula['line_num']

        # 检查圆括号
        if content.count('(') != content.count(')'):
            issues.append({
                'type': 'bracket_mismatch',
                'message': f"圆括号不匹配: {content.count('(')} 个 '(' vs {content.count(')')} 个 ')'",
                'lines': [line],
                'severity': 'error'
            })

        # 检查花括号
        if content.count('{') != content.count('}'):
            issues.append({
                'type': 'bracket_mismatch',
                'message': f"花括号不匹配: {content.count('{')} 个 '{{' vs {content.count('}')} 个 '}}'",
                'lines': [line],
                'severity': 'error'
            })

        # 检查方括号
        if content.count('[') != content.count(']'):
            issues.append({
                'type': 'bracket_mismatch',
                'message': f"方括号不匹配: {content.count('[')} 个 '[' vs {content.count(']')} 个 ']'",
                'lines': [line],
                'severity': 'error'
            })

    return issues


def check_latex_environments(formulas: List[Dict]) -> List[Dict]:
    """检查LaTeX环境匹配"""
    issues = []
    envs = ['bmatrix', 'pmatrix', 'cases', 'aligned', 'equation', 'align', 'gather', 'matrix']

    for formula in formulas:
        content = formula['content']
        line = formula['line_num']

        for env in envs:
            begin_count = len(re.findall(rf'\\begin\{{{env}\}}', content))
            end_count = len(re.findall(rf'\\end\{{{env}\}}', content))
            if begin_count != end_count:
                issues.append({
                    'type': 'env_mismatch',
                    'message': f"LaTeX环境 {env} 不匹配: {begin_count} 个 begin vs {end_count} 个 end",
                    'lines': [line],
                    'severity': 'error'
                })

    return issues


def check_formula_complexity(formulas: List[Dict]) -> List[Dict]:
    """检查公式复杂度"""
    issues = []

    for formula in formulas:
        content = formula['content']
        line = formula['line_num']

        # 检查嵌套分数
        frac_count = len(re.findall(r'\\frac', content))
        if frac_count > 3:
            issues.append({
                'type': 'complex_formula',
                'message': f"公式包含 {frac_count} 个分数，结构较复杂",
                'lines': [line],
                'severity': 'info'
            })

        # 检查指数中的分式
        if re.search(r'e\^\{[^}]*\\frac', content):
            issues.append({
                'type': 'exponential_fraction',
                'message': "指数中包含分式，请确认渲染效果",
                'lines': [line],
                'severity': 'info'
            })

    return issues


def check_common_ocr_errors(formulas: List[Dict]) -> List[Dict]:
    """检查常见的OCR识别错误"""
    issues = []

    for formula in formulas:
        content = formula['content']
        line = formula['line_num']

        # 检查是否有不完整的希腊字母命令
        greek_letters = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu', 'pi', 'sigma', 'phi', 'psi', 'omega']
        for letter in greek_letters:
            # 检查是否有 \alpha 后面紧跟字母（可能是不完整的命令）
            # 但排除常见的组合，如 \alpha x, \beta y 等
            pattern = rf'\\{letter}([a-zA-Z])'
            matches = re.findall(pattern, content)
            for match in matches:
                # 排除常见的情况：空格、逗号、括号等
                if match not in [' ', ',', '.', ')', ']', '}', '+', '-', '*', '/', '=']:
                    issues.append({
                        'type': 'incomplete_command',
                        'message': f"可能存在不完整的LaTeX命令: \\{letter}{match}",
                        'lines': [line],
                        'severity': 'warning'
                    })

    return issues


def verify_formula_structure(markdown_file: str) -> Dict:
    """验证markdown文件中所有公式的结构正确性"""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    formulas = extract_formulas(content)

    # 运行所有检查
    all_issues = []
    all_issues.extend(check_bracket_matching(formulas))
    all_issues.extend(check_latex_environments(formulas))
    all_issues.extend(check_formula_complexity(formulas))
    all_issues.extend(check_common_ocr_errors(formulas))

    # 按严重程度排序
    severity_order = {'error': 0, 'warning': 1, 'info': 2}
    all_issues.sort(key=lambda x: severity_order.get(x['severity'], 3))

    results = {
        'total_formulas': len(formulas),
        'total_issues': len(all_issues),
        'errors': len([i for i in all_issues if i['severity'] == 'error']),
        'warnings': len([i for i in all_issues if i['severity'] == 'warning']),
        'infos': len([i for i in all_issues if i['severity'] == 'info']),
        'issues': all_issues
    }

    return results


def generate_report(results: Dict) -> str:
    """生成验证报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("公式结构验证报告（通用版）")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"总公式数: {results['total_formulas']}")
    lines.append(f"总问题数: {results['total_issues']}")
    lines.append(f"  - 错误: {results['errors']}")
    lines.append(f"  - 警告: {results['warnings']}")
    lines.append(f"  - 信息: {results['infos']}")
    lines.append("")

    if results['issues']:
        lines.append("问题详情:")
        lines.append("-" * 60)

        # 按严重程度分组显示
        for severity in ['error', 'warning', 'info']:
            severity_issues = [i for i in results['issues'] if i['severity'] == severity]
            if severity_issues:
                severity_name = {'error': '错误', 'warning': '警告', 'info': '信息'}[severity]
                lines.append(f"\n{severity_name}:")
                for issue in severity_issues:
                    lines.append(f"  行 {issue['lines']}: {issue['message']}")
    else:
        lines.append("所有公式结构检查通过")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_formula_structure.py <markdown_file>")
        sys.exit(1)

    markdown_file = sys.argv[1]
    results = verify_formula_structure(markdown_file)
    report = generate_report(results)
    print(report)

    # 保存报告到文件
    report_path = Path(markdown_file).parent / "formula_structure_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
