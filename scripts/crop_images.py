"""Crop figures from PDF page images."""
from PIL import Image
import os
import sys
import json


def crop(src_path, dst_path, box):
    """Crop image and save.

    Args:
        src_path: Source image path
        dst_path: Destination image path
        box: (left, upper, right, lower) tuple
    """
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    img = Image.open(src_path)
    cropped = img.crop(box)
    cropped.save(dst_path)
    print(f"  {os.path.basename(src_path)} -> {os.path.basename(dst_path)}  ({cropped.size[0]}x{cropped.size[1]})")


def batch_crop(config_path, src_dir, dst_dir):
    """Batch crop using a JSON config file.

    Config format:
    [
        {
            "src": "page-01.png",
            "dst": "fig01_name.png",
            "box": [left, upper, right, lower]
        },
        ...
    ]
    """
    with open(config_path, 'r') as f:
        crops = json.load(f)

    os.makedirs(dst_dir, exist_ok=True)
    print(f"Processing {len(crops)} crops...")

    for item in crops:
        src = os.path.join(src_dir, item["src"])
        dst = os.path.join(dst_dir, item["dst"])
        box = tuple(item["box"])
        crop(src, dst, box)

    print(f"\nDone! {len(crops)} images cropped to {dst_dir}")


def interactive_crop(src_path, dst_path):
    """Interactive crop helper - shows image info and saves crop.

    Usage: Provide src_path, dst_path, and box coordinates.
    """
    img = Image.open(src_path)
    print(f"Source: {src_path}")
    print(f"Size: {img.size[0]}x{img.size[1]}")
    print(f"Mode: {img.mode}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Crop single: python crop_images.py <src> <dst> <left> <upper> <right> <lower>")
        print("  Batch crop:  python crop_images.py --batch <config.json> <src_dir> <dst_dir>")
        print("  Image info:  python crop_images.py --info <image_path>")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        if len(sys.argv) != 5:
            print("Usage: python crop_images.py --batch <config.json> <src_dir> <dst_dir>")
            sys.exit(1)
        batch_crop(sys.argv[2], sys.argv[3], sys.argv[4])

    elif sys.argv[1] == "--info":
        if len(sys.argv) != 3:
            print("Usage: python crop_images.py --info <image_path>")
            sys.exit(1)
        interactive_crop(sys.argv[2], "")

    else:
        if len(sys.argv) != 7:
            print("Usage: python crop_images.py <src> <dst> <left> <upper> <right> <lower>")
            sys.exit(1)
        crop(sys.argv[1], sys.argv[2],
             (int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])))


if __name__ == "__main__":
    main()
