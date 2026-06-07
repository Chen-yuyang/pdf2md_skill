# PDF2MD — PDF to Markdown Converter Skill

[中文版 README](README.zh-CN.md)

A **Claude Code skill** that converts PDF documents into precisely reproduced Markdown with LaTeX formulas. Designed for PDFs where standard text extraction fails — custom font encodings, embedded fonts, scanned content, and formula-heavy academic documents.

## Key Differentiators

Unlike traditional PDF-to-Markdown tools (e.g., Microsoft MarkItDown, PyMuPDF text extraction), PDF2MD takes a **multimodal image-based approach**:

| Feature | PDF2MD | Traditional Tools (MarkItDown, PyMuPDF, etc.) |
|---|---|---|
| **Core approach** | Convert pages to images, then use LLM multimodal vision to transcribe | Extract embedded text streams programmatically |
| **LaTeX formulas** | Full LaTeX rendering with structural verification | Limited or no formula support |
| **Scanned PDFs** | Works natively (reads images) | Requires OCR layer, often fails |
| **Custom fonts** | No issue (reads visual output) | Garbled characters from encoding mismatches |
| **Tables** | Faithful transcription with markdown/HTML tables | Often broken formatting |
| **Diagrams/Figures** | Can crop and include as images | Usually lost |
| **Accuracy verification** | 5-stage verification pipeline | No verification |
| **TOC-aware navigation** | Parses table of contents for smart page targeting | Page-by-page blind extraction |

## How It Works

### Core Principle

Convert every PDF page into a high-resolution image (300-500 DPI), then use Claude's multimodal capabilities to read and transcribe the content visually. This bypasses all text extraction issues and captures formulas, diagrams, tables, and layout faithfully.

### The Cardinal Rule

> Every page must be fully transcribed. No summarizing, no omitting, no "etc." — every word, every formula, every table cell from the original must appear in the output.

### Workflow Overview

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Analysis & Setup                               │
│  ├── Read PDF structure & page count                    │
│  ├── Parse TOC (if present) → chapter-page mapping      │
│  ├── Calculate page number offset                       │
│  └── Create output directory & tracking.json            │
├─────────────────────────────────────────────────────────┤
│ Phase 2: Batch Processing (10-15 pages per batch)       │
│  ├── Convert pages to PNG (pdftoppm, 400 DPI)          │
│  ├── Enhance images (contrast, sharpness, denoise)      │
│  ├── Pass 1: Full transcription via multimodal reading  │
│  ├── Pass 2: Reviewer audit (compare image vs markdown) │
│  └── Batch verification (formulas, numbering, spot-check│
├─────────────────────────────────────────────────────────┤
│ Phase 3: Image Processing (image mode only)             │
│  └── Crop figures, diagrams, tables from page images    │
├─────────────────────────────────────────────────────────┤
│ Phase 4: Final Verification (ALL steps mandatory)       │
│  ├── postprocess.py — fix matrix separators, duplicates │
│  ├── verify_completeness.py — page/section/eq numbering │
│  ├── verify_formulas.py — LaTeX syntax & bracket check  │
│  ├── verify_page_content.py — per-page content audit    │
│  ├── cross_validate.py — image vs markdown comparison   │
│  └── Generate conversion report                         │
├─────────────────────────────────────────────────────────┤
│ Phase 5: Cleanup                                        │
│  └── Remove temporary image files                       │
└─────────────────────────────────────────────────────────┘
```

### Two-Pass Transcription Model

Each page undergoes two passes for maximum accuracy:

**Pass 1 — Full Transcription**: Read the page image and output all Markdown content in one go (text, formulas, tables, figures).

**Pass 2 — Reviewer Audit**: Send both the original image and generated Markdown to a reviewer prompt that systematically checks for:
- Missing content (text, formulas, table cells, figure captions)
- Formula symbol errors (variable names, subscripts, superscripts, Greek letters)
- Transcription errors (typos, punctuation, numbers)
- Formatting issues (LaTeX syntax, table alignment)

This reduces API calls from dozens per page to just 2, while improving accuracy.

## Scripts

All scripts are in the `scripts/` directory. Each can be run standalone.

### Conversion & Processing

| Script | Purpose |
|---|---|
| `pdf2images.py` | Convert PDF pages to PNG images using `pdftoppm` |
| `enhance_image.py` | Image preprocessing — contrast, sharpness, denoise (3 levels: light/standard/strong) |
| `batch_process.py` | Parallel batch processing — PDF conversion, image enhancement, and formula cropping |
| `crop_images.py` | Crop specific regions from page images (figures, tables) |
| `crop_formula_regions.py` | Slice pages into horizontal strips and zoom for formula verification |
| `slice_horizontal.py` | Horizontal strip cutting — top-to-bottom reading order, no cross-region formula breaks |
| `parse_toc.py` | Extract TOC from PDF, compute page number offset, locate chapters/exercises |
| `postprocess.py` | Fix common formatting issues — broken matrix separators, LaTeX in tables, duplicates |

### Verification & Validation

| Script | Purpose |
|---|---|
| `verify_completeness.py` | Check all pages processed, section/equation/figure/table numbering sequential |
| `verify_formulas.py` | LaTeX syntax validation — bracket matching, environment matching, symbol completeness |
| `verify_formula_structure.py` | Semantic formula checks — complexity analysis, common OCR error patterns |
| `verify_page_content.py` | Per-page content audit — tracked equations/figures/tables appear in markdown |
| `cross_validate.py` | Source images vs markdown — missing pages, content density, duplicate tags |
| `pre_check.py` | Pre-write LaTeX validation with auto-fix for common OCR errors |

## Installation

### Prerequisites

```bash
# System dependencies
# Ubuntu/Debian:
sudo apt-get install poppler-utils pdftk

# macOS:
brew install poppler pdftk-java

# Windows (via scoop or chocolatey):
scoop install poppler pdftk
```

### Python Dependencies

```bash
pip install Pillow
```

### Install as Claude Code Skill

Copy the skill to your Claude Code skills directory:

```bash
# Clone this repo
git clone git@github.com:Chen-yuyang/pdf2md_skill.git

# Copy to Claude Code skills directory
cp -r pdf2md_skill ~/.claude/skills/pdf2md
```

Or symlink it:

```bash
ln -s /path/to/pdf2md_skill ~/.claude/skills/pdf2md
```

## Usage

### As a Claude Code Skill

Once installed, trigger the skill in any Claude Code conversation:

```
Convert this PDF to markdown: ./document.pdf
```

```
PDF转markdown: ./homework.pdf
```

```
提取第3章的习题: ./textbook.pdf
```

### Output Modes

1. **Text-only mode** (`text`): Pure markdown with LaTeX formulas. All content transcribed as text. Images described or omitted.
2. **Image+text mode** (`image`): Markdown with text and properly cropped images for figures, diagrams, tables, and formulas.

### Command-Line Scripts

```bash
# Convert PDF pages to images
python scripts/pdf2images.py document.pdf -o output/images --dpi 400

# Enhance image quality
python scripts/enhance_image.py input.png output.png strong

# Batch enhance all images in a directory
python scripts/enhance_image.py --batch input_dir/ output_dir/ standard

# Crop formula regions with zoom
python scripts/crop_formula_regions.py page.png output/ --zoom 5

# Parallel batch processing
python scripts/batch_process.py document.pdf output/ --pages 1-20 --dpi 400 --workers 4

# Parse table of contents
python scripts/parse_toc.py document.pdf --find-exercises "第3章"

# Post-process markdown
python scripts/postprocess.py output/

# Run all verification scripts
python scripts/verify_completeness.py output/
python scripts/verify_formulas.py output/document.md
python scripts/verify_page_content.py output/
python scripts/cross_validate.py output/source/ output/document.md

# Pre-check LaTeX with auto-fix
python scripts/pre_check.py output/document.md --fix
```

## Output Structure

```
output/
├── document.md              # Main markdown (incrementally built)
├── tracking.json            # Page-by-page content tracking
├── verification_report.txt  # Completeness verification report
├── formula_verification_report.txt
├── page_content_verification_report.txt
├── cross_validation_report.txt
├── images/                  # Cropped figures (image mode)
│   ├── cropped/
│   └── page-XX.png
└── source/
    └── page-XX.png          # Source page images
```

## DPI Selection Guide

| Scenario | DPI | Notes |
|---|---|---|
| Standard PDF | 400 | Recommended — good balance of clarity and file size |
| Fuzzy/low-quality scan | 500 | High quality for detail verification |
| Clear digital PDF | 300 | Only when file size is constrained |
| Formula-dense pages | 500 | Subscripts, superscripts, Greek letters need high resolution |

## Image Enhancement Levels

| Level | Use Case | Effects |
|---|---|---|
| `light` | Good quality images | Mild contrast +1.1x, sharpness +1.2x |
| `standard` | Most PDFs | Contrast +1.2x, sharpness +1.3x, median denoise |
| `strong` | Fuzzy/low-quality, formula-dense | Contrast +1.4x, sharpness +1.5x, median denoise, edge enhance |

## Verification Pipeline

The skill enforces a 5-stage verification pipeline. **No step can be skipped:**

1. **Completeness check** — all pages processed, numbering sequential, no gaps
2. **Formula syntax** — bracket matching, LaTeX environment pairing, symbol integrity
3. **Page content audit** — every tracked equation/figure/table appears in the markdown
4. **Cross-validation** — source images compared against markdown, content density checked
5. **Spot-check** — random pages re-read and compared against original

If any verification script reports errors, the issues must be fixed and the script re-run until it passes.

## Common Error Patterns

### Formula Symbol Confusion (Most Frequent)

| Error Type | Example | Prevention |
|---|---|---|
| Greek vs Latin | `$\alpha$` written as `$a$` | Zoom 5x+, check stroke shape |
| Subscript errors | `$x_i$` written as `$x_n$` | Character-by-character zoom comparison |
| Superscript position | `$x^2$` written as `$x_2$` | Check vertical position |
| Similar symbols | `$\phi$` vs `$\varphi$` | Compare against original strokes |
| Sum limits | `$\sum_{i=1}^{N}$` vs `$\sum_{i=1}^{n}$` | Check case |

### Text Recognition Errors

| Error Type | Example | Prevention |
|---|---|---|
| Chinese similar chars | "似然" (likelihood) vs "类似" (similar) | Understand context semantics |
| Number format | 1,234 vs 1234 | Check comma separators |
| Reference numbers | "式(3.4.22)" vs "式(3.4.23)" | Digit-by-digit comparison |

## License

Proprietary. See LICENSE.txt for complete terms.

## Contributing

This is a personal skill. For issues or suggestions, open an issue on GitHub.
