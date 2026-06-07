#!/usr/bin/env python3
"""
batch_process.py — PDF页面的并发批处理

使用concurrent.futures并行处理PDF页面：
- PDF页面转换（pdftoppm）
- 图像增强（enhance_image.py）
- 图像切片（crop_formula_regions.py）

由于PDF页面之间相互独立，可以安全并行处理。

使用方法:
    python batch_process.py <input.pdf> <output_dir> [--pages 1-10] [--dpi 400] [--workers 4]
    python batch_process.py --enhance <source_dir> <output_dir> [--workers 4]
    python batch_process.py --crop <source_dir> <output_dir> [--workers 4] [--zoom 5]

参数:
    --pages: 指定页码范围，如 1-10 或 1,3,5-8
    --dpi: 图像分辨率（默认400）
    --workers: 并发工作线程数（默认4）
    --enhance: 仅执行图像增强
    --crop: 仅执行图像切片
    --zoom: 放大倍数（默认5）
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def parse_page_range(page_str):
    """解析页码范围，如 '1-10' 或 '1,3,5-8'"""
    pages = []
    for part in page_str.split(','):
        if '-' in part:
            start, end = part.split('-', 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def convert_page(pdf_path, page_num, output_dir, dpi=400):
    """转换单个PDF页面为图像"""
    output_prefix = os.path.join(output_dir, f"page-{page_num:04d}")

    cmd = [
        'pdftoppm', '-png', '-r', str(dpi),
        '-f', str(page_num), '-l', str(page_num),
        pdf_path, output_prefix
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if result.returncode == 0:
            # pdftoppm生成的文件名格式是 prefix-XX.png 或 prefix-XXXX.png
            # 尝试多种可能的文件名格式
            possible_names = [
                f"{output_prefix}-{page_num:02d}.png",
                f"{output_prefix}-{page_num:04d}.png",
                f"{output_prefix}.png",
            ]
            for name in possible_names:
                if os.path.exists(name):
                    return True, page_num, name
            # 如果都没找到，返回前缀（让调用者处理）
            return True, page_num, output_prefix
        else:
            return False, page_num, result.stderr.decode()
    except subprocess.TimeoutExpired:
        return False, page_num, "转换超时"
    except Exception as e:
        return False, page_num, str(e)


def enhance_page(img_path, output_dir, level='standard'):
    """增强单个图像"""
    script_dir = Path(__file__).parent
    enhance_script = script_dir / 'enhance_image.py'

    output_path = os.path.join(output_dir, os.path.basename(img_path))

    cmd = [
        sys.executable, str(enhance_script),
        img_path, output_path, level
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if result.returncode == 0:
            return True, img_path, output_path
        else:
            return False, img_path, result.stderr.decode()
    except Exception as e:
        return False, img_path, str(e)


def crop_page(img_path, output_dir, zoom=5):
    """切片单个图像"""
    script_dir = Path(__file__).parent
    crop_script = script_dir / 'crop_formula_regions.py'

    page_output = os.path.join(output_dir, Path(img_path).stem)

    cmd = [
        sys.executable, str(crop_script),
        img_path, page_output, '--zoom', str(zoom)
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if result.returncode == 0:
            return True, img_path, page_output
        else:
            return False, img_path, result.stderr.decode()
    except Exception as e:
        return False, img_path, str(e)


def batch_convert(pdf_path, output_dir, pages, dpi=400, workers=4):
    """并发转换多个PDF页面"""
    os.makedirs(output_dir, exist_ok=True)

    print(f"开始并发转换 {len(pages)} 个页面 (workers={workers}, dpi={dpi})")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(convert_page, pdf_path, page, output_dir, dpi): page
            for page in pages
        }

        for future in as_completed(futures):
            success, page_num, result = future.result()
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} 页面 {page_num}")
            results.append((success, page_num, result))

    elapsed = time.time() - start_time
    success_count = sum(1 for s, _, _ in results if s)
    print(f"\n转换完成: {success_count}/{len(pages)} 成功, 耗时 {elapsed:.1f}秒")

    return results


def batch_enhance(source_dir, output_dir, level='standard', workers=4):
    """并发增强多个图像"""
    os.makedirs(output_dir, exist_ok=True)

    # 查找所有PNG文件
    source_files = sorted(Path(source_dir).glob('*.png'))
    if not source_files:
        print(f"未找到PNG文件: {source_dir}")
        return []

    print(f"开始并发增强 {len(source_files)} 个图像 (workers={workers}, level={level})")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(enhance_page, str(f), output_dir, level): f
            for f in source_files
        }

        for future in as_completed(futures):
            success, src, result = future.result()
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {Path(src).name}")
            results.append((success, src, result))

    elapsed = time.time() - start_time
    success_count = sum(1 for s, _, _ in results if s)
    print(f"\n增强完成: {success_count}/{len(source_files)} 成功, 耗时 {elapsed:.1f}秒")

    return results


def batch_crop(source_dir, output_dir, zoom=5, workers=4):
    """并发切片多个图像"""
    os.makedirs(output_dir, exist_ok=True)

    # 查找所有PNG文件
    source_files = sorted(Path(source_dir).glob('*.png'))
    if not source_files:
        print(f"未找到PNG文件: {source_dir}")
        return []

    print(f"开始并发切片 {len(source_files)} 个图像 (workers={workers}, zoom={zoom})")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(crop_page, str(f), output_dir, zoom): f
            for f in source_files
        }

        for future in as_completed(futures):
            success, src, result = future.result()
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {Path(src).name}")
            results.append((success, src, result))

    elapsed = time.time() - start_time
    success_count = sum(1 for s, _, _ in results if s)
    print(f"\n切片完成: {success_count}/{len(source_files)} 成功, 耗时 {elapsed:.1f}秒")

    return results


def main():
    parser = argparse.ArgumentParser(description='PDF页面并发批处理')
    parser.add_argument('input', help='PDF文件路径或源目录路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--pages', help='页码范围，如 1-10 或 1,3,5-8')
    parser.add_argument('--dpi', type=int, default=400, help='图像分辨率（默认400）')
    parser.add_argument('--workers', type=int, default=4, help='并发工作线程数（默认4）')
    parser.add_argument('--enhance', action='store_true', help='仅执行图像增强')
    parser.add_argument('--crop', action='store_true', help='仅执行图像切片')
    parser.add_argument('--zoom', type=int, default=5, help='放大倍数（默认5）')
    parser.add_argument('--level', default='standard', help='增强级别（light/standard/strong）')

    args = parser.parse_args()

    if args.enhance:
        batch_enhance(args.input, args.output, args.level, args.workers)
    elif args.crop:
        batch_crop(args.input, args.output, args.zoom, args.workers)
    elif args.pages:
        pages = parse_page_range(args.pages)
        batch_convert(args.input, args.output, pages, args.dpi, args.workers)
    else:
        # 默认：转换前10页作为测试
        print("未指定操作模式，使用 --pages, --enhance, 或 --crop")
        parser.print_help()


if __name__ == '__main__':
    main()
