#!/usr/bin/env python3
"""
enhance_image.py — 图像增强预处理脚本

用于提高PDF页面图像的质量，增强公式识别准确性。

使用方法:
    python enhance_image.py <input_image> <output_image>
    python enhance_image.py --batch <input_dir> <output_dir>
"""

import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def enhance_image(input_path: str, output_path: str, enhance_level: str = "standard") -> str:
    """
    增强图像质量

    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        enhance_level: 增强级别 (light/standard/strong)

    Returns:
        输出图像路径
    """
    img = Image.open(input_path)

    # 转换为RGB（如果是RGBA）
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # 根据增强级别应用不同的处理
    if enhance_level == "light":
        # 轻度增强
        img = ImageEnhance.Contrast(img).enhance(1.1)
        img = ImageEnhance.Sharpness(img).enhance(1.2)

    elif enhance_level == "standard":
        # 标准增强
        # 提高对比度
        img = ImageEnhance.Contrast(img).enhance(1.2)

        # 提高锐度
        img = ImageEnhance.Sharpness(img).enhance(1.3)

        # 轻微去噪
        img = img.filter(ImageFilter.MedianFilter(size=1))

    elif enhance_level == "strong":
        # 强力增强（用于模糊或低质量图像）
        # 提高对比度
        img = ImageEnhance.Contrast(img).enhance(1.4)

        # 提高锐度
        img = ImageEnhance.Sharpness(img).enhance(1.5)

        # 去噪（使用较小的filter size）
        img = img.filter(ImageFilter.MedianFilter(size=3))

        # 边缘增强
        img = img.filter(ImageFilter.EDGE_ENHANCE)

    # 保存图像
    img.save(output_path, quality=95)
    return output_path


def enhance_image_memory(input_path: str, enhance_level: str = "standard") -> Image.Image:
    """
    在内存中增强图像，不写入磁盘

    Args:
        input_path: 输入图像路径
        enhance_level: 增强级别 (light/standard/strong)

    Returns:
        增强后的PIL Image对象
    """
    img = Image.open(input_path)

    # 转换为RGB（如果是RGBA）
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # 根据增强级别应用不同的处理
    if enhance_level == "light":
        img = ImageEnhance.Contrast(img).enhance(1.1)
        img = ImageEnhance.Sharpness(img).enhance(1.2)

    elif enhance_level == "standard":
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Sharpness(img).enhance(1.3)
        img = img.filter(ImageFilter.MedianFilter(size=1))

    elif enhance_level == "strong":
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Sharpness(img).enhance(1.5)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = img.filter(ImageFilter.EDGE_ENHANCE)

    return img


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """
    将PIL Image对象转换为Base64字符串

    Args:
        img: PIL Image对象
        format: 图像格式 (PNG/JPEG)

    Returns:
        Base64编码的字符串
    """
    import io
    import base64

    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def enhance_for_formula(input_path: str, output_path: str) -> str:
    """
    专门为公式识别增强图像

    特点：
    - 更高的对比度，使公式更清晰
    - 更强的锐化，突出字符边缘
    - 保留细节，避免过度平滑
    """
    img = Image.open(input_path)

    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # 高对比度处理
    img = ImageEnhance.Contrast(img).enhance(1.5)

    # 高锐度处理
    img = ImageEnhance.Sharpness(img).enhance(1.6)

    # 使用USM锐化（Unsharp Mask）
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    img.save(output_path, quality=95)
    return output_path


def batch_enhance(input_dir: str, output_dir: str, enhance_level: str = "standard") -> list:
    """
    批量增强目录中的所有图像
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    enhanced_files = []

    for img_file in input_path.glob("*.png"):
        output_file = output_path / img_file.name
        enhance_image(str(img_file), str(output_file), enhance_level)
        enhanced_files.append(str(output_file))

    return enhanced_files


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python enhance_image.py <input_image> <output_image> [level]")
        print("  python enhance_image.py --batch <input_dir> <output_dir> [level]")
        print("")
        print("Levels: light, standard, strong")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        # 批量处理模式
        input_dir = sys.argv[2]
        output_dir = sys.argv[3]
        level = sys.argv[4] if len(sys.argv) > 4 else "standard"

        enhanced = batch_enhance(input_dir, output_dir, level)
        print(f"Enhanced {len(enhanced)} images")

    else:
        # 单文件处理模式
        input_image = sys.argv[1]
        output_image = sys.argv[2]
        level = sys.argv[3] if len(sys.argv) > 3 else "standard"

        enhance_image(input_image, output_image, level)
        print(f"Enhanced: {output_image}")


if __name__ == "__main__":
    main()
