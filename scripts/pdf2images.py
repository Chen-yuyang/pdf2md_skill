"""Convert PDF pages to PNG images using pdftoppm (poppler-utils)."""
import subprocess
import os
import sys
import argparse


def pdf2images(pdf_path, output_dir, dpi=200, first_page=None, last_page=None):
    """Convert PDF pages to PNG images.

    Args:
        pdf_path: Path to input PDF
        output_dir: Directory for output images
        dpi: Resolution (default 200)
        first_page: First page to convert (1-indexed)
        last_page: Last page to convert (1-indexed)

    Returns:
        List of output image paths
    """
    os.makedirs(output_dir, exist_ok=True)

    cmd = ["pdftoppm", "-png", f"-r{dpi}"]
    if first_page:
        cmd.extend(["-f", str(first_page)])
    if last_page:
        cmd.extend(["-l", str(last_page)])

    prefix = os.path.join(output_dir, "page")
    cmd.extend([pdf_path, prefix])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Collect output files
    images = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith("page") and f.endswith(".png")
    ])

    print(f"Converted {len(images)} pages to {output_dir}")
    return images


def main():
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG images")
    parser.add_argument("pdf", help="Input PDF path")
    parser.add_argument("--output-dir", "-o", default="images", help="Output directory")
    parser.add_argument("--dpi", type=int, default=200, help="Resolution (default: 200)")
    parser.add_argument("--first-page", "-f", type=int, help="First page (1-indexed)")
    parser.add_argument("--last-page", "-l", type=int, help="Last page (1-indexed)")
    args = parser.parse_args()

    images = pdf2images(
        args.pdf, args.output_dir, args.dpi,
        args.first_page, args.last_page
    )
    for img in images:
        print(img)


if __name__ == "__main__":
    main()
