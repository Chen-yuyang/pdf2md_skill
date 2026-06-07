#!/usr/bin/env python3
"""
pre_check.py — Markdown公式的本地前置检查与自我修正

在LLM返回结果后、写入Markdown文件前，立即检查LaTeX语法错误。
如果发现错误，生成修正建议，可抛回给LLM进行自我修正。

使用方法:
    python pre_check.py <markdown_file>           # 检查并报告错误
    python pre_check.py <markdown_file> --fix     # 检查并尝试自动修正
    python pre_check.py <markdown_file> --json    # 输出JSON格式的错误列表

检查项目:
    - 括号匹配（圆括号、方括号、花括号）
    - LaTeX环境匹配（\\begin/\\end）
    - 常见OCR错误（希腊字母混淆、符号错误）
    - 公式结构完整性
"""

import sys
import re
import json
from pathlib import Path


def check_brackets(text):
    """检查括号匹配"""
    errors = []
    stack = []
    bracket_map = {')': '(', ']': '[', '}': '{'}
    open_brackets = set(bracket_map.values())

    in_math = False
    i = 0
    while i < len(text):
        char = text[i]

        # 跳过转义字符
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue

        # 跟踪数学模式
        if char == '$':
            in_math = not in_math

        if in_math:
            if char in open_brackets:
                stack.append((char, i))
            elif char in bracket_map:
                if stack and stack[-1][0] == bracket_map[char]:
                    stack.pop()
                else:
                    errors.append({
                        'type': 'bracket_mismatch',
                        'position': i,
                        'message': f"多余的右括号 '{char}'",
                        'context': text[max(0, i-10):i+10]
                    })

        i += 1

    # 报告未匹配的左括号
    for bracket, pos in stack:
        errors.append({
            'type': 'bracket_unclosed',
            'position': pos,
            'message': f"未闭合的左括号 '{bracket}'",
            'context': text[max(0, pos-10):pos+10]
        })

    return errors


def check_latex_environments(text):
    """检查LaTeX环境匹配"""
    errors = []
    env_stack = []

    # 匹配 \begin{env} 和 \end{env}
    pattern = r'\\(begin|end)\{(\w+)\}'
    for match in re.finditer(pattern, text):
        command, env_name = match.groups()
        pos = match.start()

        if command == 'begin':
            env_stack.append((env_name, pos))
        elif command == 'end':
            if env_stack and env_stack[-1][0] == env_name:
                env_stack.pop()
            else:
                errors.append({
                    'type': 'env_mismatch',
                    'position': pos,
                    'message': f"\\end{{{env_name}}} 没有对应的 \\begin{{{env_name}}}",
                    'context': text[max(0, pos-10):pos+20]
                })

    for env_name, pos in env_stack:
        errors.append({
            'type': 'env_unclosed',
            'position': pos,
            'message': f"\\begin{{{env_name}}} 没有对应的 \\end{{{env_name}}}",
            'context': text[max(0, pos-10):pos+20]
        })

    return errors


def check_common_ocr_errors(text):
    """检查常见OCR错误"""
    errors = []

    # 常见错误模式
    patterns = [
        # 混淆的希腊字母
        (r'(?<!\\)alpha(?![a-z])', '可能应该是 \\alpha'),
        (r'(?<!\\)beta(?![a-z])', '可能应该是 \\beta'),
        (r'(?<!\\)gamma(?![a-z])', '可能应该是 \\gamma'),
        (r'(?<!\\)delta(?![a-z])', '可能应该是 \\delta'),
        (r'(?<!\\)theta(?![a-z])', '可能应该是 \\theta'),
        (r'(?<!\\)sigma(?![a-z])', '可能应该是 \\sigma'),
        (r'(?<!\\)mu(?![a-z])', '可能应该是 \\mu'),

        # 缺少反斜杠的LaTeX命令
        (r'(?<![a-zA-Z\\])frac\{', '可能应该是 \\frac{'),
        (r'(?<![a-zA-Z\\])sqrt\{', '可能应该是 \\sqrt{'),
        (r'(?<!\\)sum(?![a-z])', '可能应该是 \\sum'),
        (r'(?<!\\)int(?![a-z])', '可能应该是 \\int'),
        (r'(?<!\\)prod(?![a-z])', '可能应该是 \\prod'),
        (r'(?<!\\)lim(?![a-z])', '可能应该是 \\lim'),
        (r'(?<!\\)max(?![a-z])', '可能应该是 \\max'),
        (r'(?<!\\)min(?![a-z])', '可能应该是 \\min'),

        # 常见符号错误
        (r'(?<!\\)times(?![a-z])', '可能应该是 \\times'),
        (r'(?<!\\)cdot(?![a-z])', '可能应该是 \\cdot'),
        (r'(?<!\\)partial(?![a-z])', '可能应该是 \\partial'),
        (r'(?<!\\)nabla(?![a-z])', '可能应该是 \\nabla'),
    ]

    for pattern, message in patterns:
        for match in re.finditer(pattern, text):
            errors.append({
                'type': 'ocr_suspect',
                'position': match.start(),
                'message': message,
                'context': text[max(0, match.start()-10):match.end()+10]
            })

    return errors


def check_formula_structure(text):
    """检查公式结构完整性"""
    errors = []

    # 检查 $$...$$ 块是否成对
    display_math = re.findall(r'\$\$', text)
    if len(display_math) % 2 != 0:
        errors.append({
            'type': 'display_math_odd',
            'position': 0,
            'message': f"$$ 数量为奇数({len(display_math)})，可能存在未闭合的display math",
            'context': ''
        })

    # 检查 $...$ 是否成对（简单检查，忽略$$）
    text_no_display = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    inline_math = re.findall(r'(?<!\$)\$(?!\$)', text_no_display)
    if len(inline_math) % 2 != 0:
        errors.append({
            'type': 'inline_math_odd',
            'position': 0,
            'message': f"$ 数量为奇数({len(inline_math)})，可能存在未闭合的inline math",
            'context': ''
        })

    return errors


def auto_fix_common_errors(text):
    """自动修正一些简单的错误"""
    fixed = text
    fixes = []

    # 修正缺少反斜杠的LaTeX命令
    replacements = [
        (r'(?<!\\)frac\{', r'\\frac{'),
        (r'(?<!\\)sqrt\{', r'\\sqrt{'),
        (r'(?<!\\)sum\b', r'\\sum'),
        (r'(?<!\\)int\b', r'\\int'),
        (r'(?<!\\)prod\b', r'\\prod'),
        (r'(?<!\\)lim\b', r'\\lim'),
        (r'(?<!\\)max\b', r'\\max'),
        (r'(?<!\\)min\b', r'\\min'),
        (r'(?<!\\)times\b', r'\\times'),
        (r'(?<!\\)cdot\b', r'\\cdot'),
        (r'(?<!\\)partial\b', r'\\partial'),
        (r'(?<!\\)nabla\b', r'\\nabla'),
    ]

    for pattern, replacement in replacements:
        new_text = re.sub(pattern, replacement, fixed)
        if new_text != fixed:
            fixes.append(f"修正: {pattern} -> {replacement}")
            fixed = new_text

    return fixed, fixes


def check_markdown(file_path):
    """检查Markdown文件中的所有问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    all_errors = []

    # 运行所有检查
    all_errors.extend(check_brackets(content))
    all_errors.extend(check_latex_environments(content))
    all_errors.extend(check_common_ocr_errors(content))
    all_errors.extend(check_formula_structure(content))

    return all_errors, content


def main():
    if len(sys.argv) < 2:
        print("Usage: python pre_check.py <markdown_file> [--fix] [--json]")
        sys.exit(1)

    file_path = sys.argv[1]
    fix_mode = '--fix' in sys.argv
    json_mode = '--json' in sys.argv

    if not Path(file_path).exists():
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    errors, content = check_markdown(file_path)

    if json_mode:
        print(json.dumps(errors, ensure_ascii=False, indent=2))
    elif errors:
        print(f"发现 {len(errors)} 个问题:")
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. [{error['type']}] {error['message']}")
            if error['context']:
                print(f"   上下文: ...{error['context']}...")

        if fix_mode:
            print("\n尝试自动修正...")
            fixed_content, fixes = auto_fix_common_errors(content)
            if fixes:
                for fix in fixes:
                    print(f"  [OK] {fix}")
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"\n已修正 {len(fixes)} 个问题，文件已更新: {file_path}")
            else:
                print("  没有可自动修正的问题")
    else:
        print("[OK] 未发现问题")


if __name__ == '__main__':
    main()
