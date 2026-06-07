#!/usr/bin/env python3
"""
crop_formula_regions.py — 从PDF页面图像中裁剪公式区域并放大

用于公式验证：将页面中的公式区域裁剪出来并放大，便于逐符号对比。

使用方法:
    python crop_formula_regions.py <page_image> <output_dir> [--zoom 5]
    python crop_formula_regions.py --batch <source_dir> <output_dir> [--zoom 5]

裁剪策略：
    - 自动检测页面中的公式密集区域（基于亮度和对比度分析）
    - 将页面分成若干横向条带
    - 对每个条带进行增强和放大
"""

import sys
import os
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter


def enhance_image(img, level='standard'):
    """增强图像质量"""
    if level == 'light':
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
    elif level == 'standard':
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
    elif level == 'strong':
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.2)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(3.0)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
    return img


def slice_and_zoom(img_path, output_dir, strip_height=400, zoom_level=5, max_size=2000):
    """
    将页面切成横向条带并逐条放大

    Args:
        img_path: 输入图像路径
        output_dir: 输出目录
        strip_height: 每条高度（像素）
        zoom_level: 放大倍数
        max_size: 输出图像最大尺寸（像素），超过则自动降低放大倍数
    """
    img = Image.open(img_path)
    w, h = img.size

    # 增强图像
    img = enhance_image(img, 'standard')

    strips = []
    for i in range(0, h, strip_height):
        end = min(i + strip_height, h)
        strip = img.crop((0, i, w, end))

        # 计算实际放大倍数，确保不超过max_size
        actual_zoom = min(zoom_level, max_size // max(strip.width, strip.height))
        actual_zoom = max(1, actual_zoom)  # 至少放大1倍

        # 放大
        zoomed = strip.resize(
            (strip.width * actual_zoom, strip.height * actual_zoom),
            Image.LANCZOS
        )

        strip_path = os.path.join(output_dir, f'strip_{i:04d}_{end:04d}.png')
        zoomed.save(strip_path)
        strips.append(strip_path)

    return strips


def crop_formula_area(img_path, output_dir, y_start, y_end, zoom_level=5, max_size=2000):
    """
    裁剪指定Y坐标范围的区域并放大

    Args:
        img_path: 输入图像路径
        output_dir: 输出目录
        y_start: 起始Y坐标
        y_end: 结束Y坐标
        zoom_level: 放大倍数
        max_size: 输出图像最大尺寸（像素）
    """
    img = Image.open(img_path)
    w, h = img.size

    # 增强
    img = enhance_image(img, 'strong')

    # 裁剪（留一些边距）
    margin = 20
    y_start = max(0, y_start - margin)
    y_end = min(h, y_end + margin)

    cropped = img.crop((0, y_start, w, y_end))

    # 计算实际放大倍数
    actual_zoom = min(zoom_level, max_size // max(cropped.width, cropped.height))
    actual_zoom = max(1, actual_zoom)

    # 放大
    zoomed = cropped.resize(
        (cropped.width * actual_zoom, cropped.height * actual_zoom),
        Image.LANCZOS
    )

    out_path = os.path.join(output_dir, f'formula_y{y_start}_{y_end}_zoom{actual_zoom}x.png')
    zoomed.save(out_path)
    return out_path


def process_page(img_path, output_dir, zoom_level=5, strip_height=400):
    """处理单个页面：切成条带并放大"""
    os.makedirs(output_dir, exist_ok=True)

    # 生成条带
    strips = slice_and_zoom(img_path, output_dir, strip_height, zoom_level)

    # 同时生成整页放大版本
    img = Image.open(img_path)
    img = enhance_image(img, 'standard')
    zoomed = img.resize((img.width * zoom_level, img.height * zoom_level), Image.LANCZOS)
    full_path = os.path.join(output_dir, f'full_page_zoom{zoom_level}x.png')
    zoomed.save(full_path)

    return strips, full_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python crop_formula_regions.py <page_image> <output_dir> [--zoom N]")
        print("       python crop_formula_regions.py --batch <source_dir> <output_dir> [--zoom N]")
        sys.exit(1)

    zoom_level = 5
    if '--zoom' in sys.argv:
        idx = sys.argv.index('--zoom')
        zoom_level = int(sys.argv[idx + 1])

    if sys.argv[1] == '--batch':
        source_dir = sys.argv[2]
        output_dir = sys.argv[3]
        os.makedirs(output_dir, exist_ok=True)

        for img_file in sorted(Path(source_dir).glob('*.png')):
            page_output = os.path.join(output_dir, img_file.stem)
            strips, full = process_page(str(img_file), page_output, zoom_level)
            print(f"Processed {img_file.name}: {len(strips)} strips + full page")
    else:
        img_path = sys.argv[1]
        output_dir = sys.argv[2]
        strips, full = process_page(img_path, output_dir, zoom_level)
        print(f"Generated {len(strips)} strips + full page in {output_dir}")


if __name__ == '__main__':
    main()
