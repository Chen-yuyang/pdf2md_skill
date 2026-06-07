#!/usr/bin/env python3
"""
postprocess.py — Post-process pdf2md output to fix common formatting issues.

Fixes:
1. Broken matrix row separators (\ → \\)
2. LaTeX backslash issues in markdown table cells
3. Duplicate content detection
4. Common OCR transcription errors in formulas

Usage:
    python postprocess.py <output-dir>
"""

import re
import sys
from pathlib import Path


def fix_matrix_separators(text: str) -> int:
    """Fix broken matrix row separators inside LaTeX environments.

    In \\begin{bmatrix}...\\end{bmatrix}, row separators must be \\\\ (double backslash).
    A single \\ followed by space is NOT a row separator — it's just a space.
    """
    env_names = ['bmatrix', 'pmatrix', 'matrix', 'cases', 'aligned']
    fix_count = 0

    for env in env_names:
        pattern = rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}'

        def fix_env(match, e=env):
            nonlocal fix_count
            inner = match.group(1)
            # Replace single \ used as row separator with \\
            # A broken separator: \ that is NOT preceded by \ and NOT followed by a letter or { or }
            original = inner
            fixed = re.sub(r'(?<!\\)\\(?!\\|[a-zA-Z{}])', r'\\\\', inner)
            if fixed != original:
                fix_count += 1
            return f'\\begin{{{e}}}{fixed}\\end{{{e}}}'

        text = re.sub(pattern, fix_env, text, flags=re.DOTALL)

    return text, fix_count


def fix_table_backslashes(text: str) -> int:
    """Fix LaTeX backslash issues in markdown table cells.

    In markdown tables, \\ is interpreted as a line break, not LaTeX row separator.
    Single \\ in table cells gets consumed as escape character.
    """
    lines = text.split('\n')
    fix_count = 0
    in_table = False

    for i, line in enumerate(lines):
        if line.strip().startswith('|') and '|' in line[1:]:
            in_table = True
        elif in_table and not line.strip().startswith('|'):
            in_table = False

        if in_table and '$' in line:
            # Check for broken matrix notation inside table cells
            # Pattern: $...\begin{bmatrix}... single-backslash ... \end{bmatrix}...$
            if re.search(r'\$.*\\begin\{bmatrix\}.*(?<!\\)\\(?!\\|[a-zA-Z{}]).*\\end\{bmatrix\}.*\$', line):
                # This line has a matrix in a table cell with broken separators
                # We can't fix this reliably in-place — flag it instead
                fix_count += 1

    return fix_count


def detect_duplicate_content(text: str) -> list:
    """Detect potential duplicate content blocks."""
    lines = text.split('\n')
    duplicates = []

    # Look for repeated paragraph blocks (3+ consecutive lines appearing twice)
    seen_blocks = {}
    current_block = []
    block_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '' or stripped.startswith('#') or stripped.startswith('|'):
            if len(current_block) >= 3:
                block_key = '\n'.join(current_block[:5])  # Use first 5 lines as key
                if block_key in seen_blocks:
                    duplicates.append({
                        'first_occurrence': seen_blocks[block_key],
                        'second_occurrence': block_start,
                        'length': len(current_block)
                    })
                seen_blocks[block_key] = block_start
            current_block = []
            block_start = i + 1
        else:
            current_block.append(stripped)

    return duplicates


def check_formula_consistency(text: str) -> list:
    """Check for common formula consistency issues."""
    issues = []

    # Check for variables defined multiple times with different formulas
    # Pattern: $$... VARIABLE = ... $$ appearing multiple times
    eq_pattern = r'\$\$([^$]+)\$\$'
    equations = re.findall(eq_pattern, text)

    var_defs = {}
    for eq in equations:
        # Look for variable = expression patterns
        def_pattern = r'([A-Za-z_][A-Za-z0-9_]*(?:\^[^=]*)?)\s*='
        for match in re.finditer(def_pattern, eq):
            var_name = match.group(1)
            if var_name in var_defs:
                # Check if the definitions are different
                if var_defs[var_name] != eq.strip():
                    issues.append(f"Variable '{var_name}' defined multiple times with different formulas")
            var_defs[var_name] = eq.strip()

    # Check for missing time derivative dots
    # Common pattern: \alpha without \dot{\alpha} where dots should be
    dot_pattern = r'\\(?<!\\)(?:alpha|beta|gamma|theta|phi|psi)(?!\\)'
    # This is a heuristic — flag lines where Greek letters appear without dots
    # in contexts where time derivatives are expected (e.g., matrix elements)

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python postprocess.py <output-dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"ERROR: Directory does not exist: {output_dir}")
        sys.exit(1)

    # Find the main markdown file
    md_files = list(output_dir.glob("*.md"))
    if not md_files:
        print("ERROR: No markdown file found")
        sys.exit(1)

    md_path = md_files[0]
    print(f"Processing: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_length = len(content)

    # Fix 1: Matrix separators
    content, matrix_fixes = fix_matrix_separators(content)
    print(f"Fixed {matrix_fixes} matrix environments with broken separators")

    # Fix 2: Table backslash issues
    table_issues = fix_table_backslashes(content)
    print(f"Found {table_issues} table cells with potential LaTeX issues")

    # Check 3: Duplicate content
    duplicates = detect_duplicate_content(content)
    if duplicates:
        print(f"WARNING: Found {len(duplicates)} potential duplicate content blocks:")
        for dup in duplicates:
            print(f"  Lines {dup['first_occurrence']}-{dup['first_occurrence']+dup['length']} "
                  f"and {dup['second_occurrence']}-{dup['second_occurrence']+dup['length']}")

    # Check 4: Formula consistency
    formula_issues = check_formula_consistency(content)
    if formula_issues:
        print(f"WARNING: Found {len(formula_issues)} formula consistency issues:")
        for issue in formula_issues[:10]:  # Show first 10
            print(f"  - {issue}")

    # Write fixed content
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    new_length = len(content)
    print(f"\nFile size: {original_length} -> {new_length} bytes")
    print("Post-processing complete.")


if __name__ == "__main__":
    main()
