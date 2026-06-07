#!/usr/bin/env python3
"""
parse_toc.py — 从PDF中提取目录结构并计算页码偏移量

用于智能内容定位：解析PDF的目录/大纲，构建章节-页码映射，
自动计算书页码与PDF物理页码之间的偏移量。

使用方法:
    python parse_toc.py <input.pdf>
    python parse_toc.py <input.pdf> --verify-page 93  # 校验特定页面的偏移量
    python parse_toc.py <input.pdf> --find-exercises "第3章"  # 定位某章习题

输出:
    - 目录结构（章节名 -> 书页码）
    - 页码偏移量
    - 各章习题的大致PDF页码范围
"""

import sys
import re
import subprocess
import json
from pathlib import Path


def get_pdf_outline(pdf_path):
    """尝试通过pdftk获取PDF书签/大纲"""
    try:
        result = subprocess.run(
            ['pdftk', pdf_path, 'dump_data'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None

        outline = []
        current_title = None
        current_page = None

        for line in result.stdout.split('\n'):
            if line.strip().startswith('BookmarkTitle:'):
                current_title = line.split(':', 1)[1].strip()
            elif line.strip().startswith('BookmarkPageNumber:'):
                current_page = int(line.split(':', 1)[1].strip())
                if current_title:
                    outline.append({
                        'title': current_title,
                        'pdf_page': current_page
                    })
                    current_title = None
                    current_page = None

        return outline if outline else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def extract_toc_from_images(pdf_path, toc_pages=range(1, 15), dpi=300):
    """
    通过图像识别提取目录内容
    假设目录在前几页（默认前15页）
    """
    import tempfile
    from pathlib import Path

    toc_entries = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # 转换前几页为图像
        for page_num in toc_pages:
            output_prefix = f"{tmpdir}/page"
            subprocess.run(
                ['pdftoppm', '-png', '-r', str(dpi),
                 '-f', str(page_num), '-l', str(page_num),
                 pdf_path, output_prefix],
                capture_output=True, timeout=60
            )

        # 读取每页图像，识别目录内容
        for page_num in toc_pages:
            img_path = f"{tmpdir}/page-{page_num:02d}.png"
            if not Path(img_path).exists():
                # 尝试不同的命名格式
                img_path = f"{tmpdir}/page-{page_num:04d}.png"
            if not Path(img_path).exists():
                continue

            # 这里需要调用多模态识别来读取目录
            # 返回识别结果，由调用者处理
            toc_entries.append({
                'page_num': page_num,
                'img_path': img_path
            })

    return toc_entries


def calculate_offset(toc_entries, pdf_path):
    """
    通过对比目录中的书页码和PDF页面上印刷的页码来计算偏移量

    基本逻辑：
    1. 目录说"第X章从书页Y开始"
    2. 找到PDF中对应的物理页码Z（通过书签或内容匹配）
    3. 偏移量 = Z - Y
    """
    offsets = []

    for entry in toc_entries:
        if 'book_page' in entry and 'pdf_page' in entry:
            offset = entry['pdf_page'] - entry['book_page']
            offsets.append(offset)

    if not offsets:
        return None

    # 使用最常见的偏移量
    from collections import Counter
    counter = Counter(offsets)
    most_common = counter.most_common(1)[0]

    return {
        'offset': most_common[0],
        'confidence': most_common[1] / len(offsets),
        'all_offsets': dict(counter)
    }


def find_chapter_exercises(toc, chapter_name, offset=0):
    """
    根据目录定位某章习题的大致页码范围

    策略：
    1. 找到当前章的起始页
    2. 找到下一章的起始页
    3. 习题通常在当前章最后20%-30%的页面中
    """
    chapters = sorted(toc.items(), key=lambda x: x[1])

    for i, (name, start_page) in enumerate(chapters):
        if chapter_name in name:
            # 找到当前章
            if i + 1 < len(chapters):
                next_start = chapters[i + 1][1]
            else:
                next_start = start_page + 50  # 最后一章，估计50页

            chapter_length = next_start - start_page
            # 习题通常在最后20-30%
            exercise_start = start_page + int(chapter_length * 0.7)
            exercise_end = next_start - 1

            return {
                'chapter': name,
                'chapter_start_book': start_page,
                'chapter_end_book': next_start - 1,
                'exercise_start_book': exercise_start,
                'exercise_end_book': exercise_end,
                'exercise_start_pdf': exercise_start + offset,
                'exercise_end_pdf': exercise_end + offset,
                'offset': offset
            }

    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_toc.py <input.pdf> [--verify-page N] [--find-exercises '章名']")
        sys.exit(1)

    pdf_path = sys.argv[1]
    verify_page = None
    find_exercises = None

    if '--verify-page' in sys.argv:
        idx = sys.argv.index('--verify-page')
        verify_page = int(sys.argv[idx + 1])

    if '--find-exercises' in sys.argv:
        idx = sys.argv.index('--find-exercises')
        find_exercises = sys.argv[idx + 1]

    print(f"分析PDF: {pdf_path}")
    print("=" * 60)

    # 尝试获取PDF书签
    outline = get_pdf_outline(pdf_path)

    if outline:
        print("\n发现PDF书签/大纲:")
        for item in outline:
            print(f"  {item['title']} -> PDF第{item['pdf_page']}页")
    else:
        print("\n未发现PDF书签，需要通过图像识别提取目录")
        print("请手动提供目录信息或让Claude读取目录页图像")

    if verify_page:
        print(f"\n校验页面 {verify_page} 的偏移量...")
        print("请提供该页面上印刷的书页码")

    if find_exercises:
        print(f"\n查找'{find_exercises}'的习题...")
        if outline:
            # 构建目录映射
            toc = {item['title']: item['pdf_page'] for item in outline}
            result = find_chapter_exercises(toc, find_exercises)
            if result:
                print(f"  习题大致范围: 书页{result['exercise_start_book']}-{result['exercise_end_book']}")
                print(f"  对应PDF页码: {result['exercise_start_pdf']}-{result['exercise_end_pdf']}")
            else:
                print(f"  未找到'{find_exercises}'的目录条目")

    # 输出JSON格式的结果
    result = {
        'outline': outline,
        'verify_page': verify_page,
        'find_exercises': find_exercises
    }
    print(f"\nJSON结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
