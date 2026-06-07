#!/usr/bin/env python3
"""
横向切条脚本：将竖长的PDF页面图像切成多个横向细条

优势：
- 符合从上到下的阅读习惯
- 不会切断跨区域的公式（同一公式在连续的条中）
- 可以逐条增强和识别，加快速度

使用方法：
    python slice_horizontal.py <input_image> <output_dir> [--strip-height 300] [--enhance] [--zoom 5]
"""

import argparse
import os
from pathlib import Path
from PIL import Image, ImageEnhance


def slice_page_horizontal(img_path, output_dir, strip_height=300):
    """
    将竖长的PDF页面切成多个横向细条

    Args:
        img_path: 输入图像路径
        output_dir: 输出目录
        strip_height: 每条的高度（像素），默认300px

    Returns:
        list: 切割后的横条文件路径列表
    """
    img = Image.open(img_path)
    w, h = img.size

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    strips = []

    for i in range(0, h, strip_height):
        end = min(i + strip_height, h)
        strip = img.crop((0, i, w, end))

        # 生成文件名
        strip_filename = f'strip_{i:04d}_{end:04d}.png'
        strip_path = os.path.join(output_dir, strip_filename)

        strip.save(strip_path)
        strips.append(strip_path)

        print(f'切割: {i}-{end} -> {strip_filename}')

    print(f'共切割 {len(strips)} 个横条')
    return strips


def enhance_strip(strip_path, output_path=None):
    """
    增强单个横条的图像质量

    Args:
        strip_path: 横条图像路径
        output_path: 输出路径（可选，默认覆盖原文件）

    Returns:
        str: 增强后的图像路径
    """
    if output_path is None:
        output_path = strip_path

    img = Image.open(strip_path)

    # 增强对比度和锐度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.5)

    img.save(output_path)
    return output_path


def zoom_strip(strip_path, zoom_level=5, output_path=None):
    """
    放大单个横条

    Args:
        strip_path: 横条图像路径
        zoom_level: 放大倍数，默认5倍
        output_path: 输出路径（可选，默认在原文件名后加_zoom5x）

    Returns:
        str: 放大后的图像路径
    """
    img = Image.open(strip_path)

    # 放大图像
    zoomed = img.resize(
        (img.width * zoom_level, img.height * zoom_level),
        Image.LANCZOS
    )

    # 生成放大后的文件名
    if output_path is None:
        base, ext = os.path.splitext(strip_path)
        output_path = f'{base}_zoom{zoom_level}x{ext}'

    zoomed.save(output_path)
    return output_path


def process_page(img_path, output_dir, strip_height=300, enhance=True, zoom_level=None):
    """
    完整处理一个页面：切割 -> 增强 -> 放大

    Args:
        img_path: 输入图像路径
        output_dir: 输出目录
        strip_height: 每条的高度（像素）
        enhance: 是否增强图像
        zoom_level: 放大倍数（None表示不放大）

    Returns:
        list: 处理后的横条文件路径列表
    """
    # 创建子目录
    strips_dir = os.path.join(output_dir, 'strips')
    enhanced_dir = os.path.join(output_dir, 'enhanced')
    zoomed_dir = os.path.join(output_dir, 'zoomed')

    # 切割横条
    print(f'=== 处理页面: {img_path} ===')
    strips = slice_page_horizontal(img_path, strips_dir, strip_height)

    # 增强横条
    enhanced_strips = []
    if enhance:
        print('\n--- 增强图像 ---')
        os.makedirs(enhanced_dir, exist_ok=True)
        for strip_path in strips:
            filename = os.path.basename(strip_path)
            enhanced_path = os.path.join(enhanced_dir, filename)
            enhance_strip(strip_path, enhanced_path)
            enhanced_strips.append(enhanced_path)
            print(f'增强: {filename}')
    else:
        enhanced_strips = strips

    # 放大横条
    if zoom_level:
        print(f'\n--- 放大 {zoom_level} 倍 ---')
        os.makedirs(zoomed_dir, exist_ok=True)
        for strip_path in enhanced_strips:
            filename = os.path.basename(strip_path)
            zoomed_path = os.path.join(zoomed_dir, filename)
            zoom_strip(strip_path, zoom_level, zoomed_path)
            print(f'放大: {filename}')

    print(f'\n=== 处理完成 ===')
    return enhanced_strips


def main():
    parser = argparse.ArgumentParser(description='将PDF页面图像切割成横向细条')
    parser.add_argument('input', help='输入图像路径')
    parser.add_argument('output', help='输出目录')
    parser.add_argument('--strip-height', type=int, default=300,
                        help='每条的高度（像素），默认300')
    parser.add_argument('--enhance', action='store_true', default=True,
                        help='增强图像质量（默认开启）')
    parser.add_argument('--no-enhance', action='store_false', dest='enhance',
                        help='不增强图像质量')
    parser.add_argument('--zoom', type=int, default=None,
                        help='放大倍数（可选）')

    args = parser.parse_args()

    # 处理页面
    process_page(
        args.input,
        args.output,
        strip_height=args.strip_height,
        enhance=args.enhance,
        zoom_level=args.zoom
    )


if __name__ == '__main__':
    main()
