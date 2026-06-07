---
name: pdf2md
description: "Convert PDF documents to precisely reproduced markdown format with LaTeX formulas. This skill MUST be used for ALL PDF to markdown conversions, especially when: standard text extraction fails, embedded fonts or garbled characters appear, documents contain mathematical formulas, tables, or figures, scanned documents need transcription, or any request to reproduce a PDF as markdown. TRIGGER on: 'convert PDF to markdown', 'PDF转markdown', 'PDF转MD', '复刻PDF', 'PDF精准复刻', 'extract PDF to markdown with formulas', '提取PDF中的公式', 'PDF作业题提取', or ANY request involving PDF conversion. DO NOT attempt PDF conversion without this skill - always use it for accurate results."
---

# PDF to Markdown Converter

Convert PDF documents into precisely reproduced markdown with LaTeX formulas. Designed for PDFs where standard text extraction fails (custom font encodings, embedded fonts, scanned content).

## 重要：必须执行的所有步骤

**在使用本技能时，你必须执行以下所有步骤，不可跳过、不可省略、不可标记为"可选"：**

1. ✅ **分析阶段**：读取PDF，确定DPI（300-500），识别页面结构。**如果检测到目录，解析目录构建章节-页码映射，计算偏移量，智能定位目标页面**
2. ✅ **目录校验**：转换第一页后立即验证页码偏移量是否正确，避免批量转换后才发现错误
3. ✅ **图像转换**：将PDF页面转为图像
4. ✅ **图像增强**：使用enhance_image.py增强图像质量（这一步不可跳过）
5. ✅ **转录阶段**：逐页转录，使用增强后的图像，每页转录后立即写后验证
6. ✅ **批次验证**：每批处理完后运行公式验证和结构检查
7. ✅ **后处理**：运行postprocess.py修复格式问题
8. ✅ **完整性验证**：运行verify_completeness.py检查页面、章节、编号完整性
9. ✅ **公式验证**：运行verify_formulas.py检查公式语法和结构
10. ✅ **逐页内容验证**：运行verify_page_content.py验证每页内容是否完整转录
11. ✅ **交叉验证**：运行cross_validate.py对比原PDF图像和markdown
12. ✅ **生成报告**：生成包含所有验证结果的转换报告

**如果任何验证脚本报错，必须修复后重新运行，直到通过为止。**

## Core Principle

Always use the model's multimodal capabilities. Convert PDF pages to images and read them directly — this bypasses all text extraction issues and captures formulas, diagrams, tables, and layout faithfully.

**The cardinal rule: every page must be fully transcribed. No summarizing, no omitting, no "etc." — every word, every formula, every table cell from the original must appear in the output.**

## Output Modes

Ask the user which mode they prefer:

1. **Text-only mode** (`text`): Pure markdown with LaTeX formulas. All content transcribed as text. Images are described or omitted.
2. **Image+text mode** (`image`): Markdown with text and properly cropped images for figures, diagrams, tables, and formulas that are hard to represent in LaTeX.

## Workflow

### Phase 1: Analysis & Setup

1. Read the PDF with the Read tool to understand total pages, structure, and content type

1.5. **目录解析（仅当检测到目录时触发）**：

在读取PDF后，检查是否存在目录（Table of Contents）。目录可能以两种形式出现：
- **PDF书签/大纲**：PDF元数据中的outline结构
- **页面中的目录文本**：书的前几页中可见的目录列表

**如果检测到目录，执行以下步骤：**

**Step A: 解析目录结构**
```python
# 从目录页中提取章节-页码映射
toc = {
    "第1章 绪论": 1,
    "第2章 统计与优化基础": 57,
    "第3章 贝叶斯决策": 79,
    # ... 章节名: 书页码
}
```

**Step B: 计算页码偏移量**
目录中的页码是书页码，PDF文件的页码是从0或1开始的物理页码。需要计算偏移量：
```python
# 读取目录中某个章节对应的PDF页面，对比页面上印刷的页码
# 例如：目录说"第3章从第79页开始"，但PDF第93页对应书页79
offset = pdf_page_number - book_page_number  # 例如: 93 - 79 = 14
```

**Step C: 构建页面查找表**
```python
page_lookup = {
    # 书页码 -> PDF页码
    "第2章_习题": (pdf_page_for_book_page(57), pdf_page_for_book_page(78)),
    "第3章_习题": (pdf_page_for_book_page(79), pdf_page_for_book_page(92)),
    # ...
}
```

**Step D: 智能定位策略**

有了目录结构后，可以像人一样智能定位内容：
- **课后习题**：通常在每章最后一节之后、下一章第一节之前
- **特定章节**：直接通过目录定位到起始页，不需要逐页扫描
- **前言/附录**：通常在目录之前或正文之后

**使用示例**：
```
用户："提取第3章的习题"
→ 从目录得知：第3章从书页79开始，第4章从书页105开始
→ 习题在第3章末尾，大约在书页90-104之间
→ 转换为PDF页码：93-118（偏移14）
→ 只需处理这些页面，而不是盲目扫描整个PDF
```

**偏移量校验**：
转换后，读取目标PDF页面的页眉/页脚，确认书页码与目录一致。如果不一致，调整偏移量。

**目录解析优化建议**：
1. **预解析目录**：在开始转换前，先读取目录页（通常是PDF的第7-14页），构建完整的章节-页码映射
2. **批量定位**：一次性确定所有目标章节的PDF页码，避免逐章查找浪费时间
3. **偏移量验证**：转换第一页后立即验证页码偏移量是否正确，避免批量转换后才发现错误
4. **并行处理**：使用 `batch_process.py` 并发转换多个章节的页面，显著提升效率

2. Determine which pages have extractable text vs. which need multimodal reading
3. Identify all sections, figures, tables, equations, and code blocks
4. Plan the output structure (heading hierarchy, image placement)
5. Create output directory structure:

```
output/
├── document.md              # Main markdown file (incrementally built)
├── tracking.json            # Page-by-page content tracking
├── images/                  # Cropped figures (image mode)
│   ├── cropped/
│   └── page-XX.png
└── source/
    └── page-XX.png          # Source page images for reference
```

6. Initialize `tracking.json`:
```json
{
  "total_pages": 0,
  "processed_pages": [],
  "sections_found": [],
  "equations_found": [],
  "figures_found": [],
  "tables_found": [],
  "batches": []
}
```

### 智能内容定位策略（目录解析后启用）

当目录解析成功后，可以像人一样智能定位内容，而不是盲目逐页扫描：

**课后习题定位**：
- 习题通常在每章最后一节之后、下一章第一节之前
- 策略：找到当前章的最后一节结束位置 → 读取接下来的几页 → 识别"习题"标题
- 例如：目录显示第3章从79页到104页，第4章从105页开始 → 习题大约在90-104页之间

**特定章节定位**：
- 直接通过目录定位到章节起始页，然后向后读取所需内容
- 不需要从第1页开始逐页扫描

**批量提取多章节习题**：
```
用户："提取第2、3、4章的习题"
→ 从目录得知各章页码范围
→ 计算每章习题的大致PDF页码
→ 并行转换和处理各章的习题页面
→ 比逐章顺序处理快得多
```

**偏移量自动校验**：
转换目标页面后，读取页面上的印刷页码（页眉/页脚），与目录中的书页码对比：
- 如果一致 → 偏移量正确，继续处理
- 如果不一致 → 调整偏移量，重新定位
- 这避免了"转了16页才发现第12章的页面其实是第13章内容"的问题

### Phase 2: Batch Processing with Verification

**Process pages in batches of 10-15.** Each batch follows this exact sequence:

#### Step 1: Convert batch pages to images

```bash
pdftoppm -png -r 400 -f <start> -l <end> <input.pdf> <temp-dir>/page
```

**DPI选择指南**：
- **400 DPI**：推荐默认选择，适用于大多数PDF
- **500 DPI**：适用于模糊或低质量的扫描文档
- **300 DPI**：仅适用于非常清晰的PDF

**DPI选择策略**：
| 场景 | DPI | 说明 |
|------|-----|------|
| 一般PDF | 400 | 推荐方案，清晰度与文件大小平衡 |
| 模糊PDF | 500 | 高质量方案，用于细节验证 |
| 清晰PDF | 300 | 仅当文件大小受限时使用 |

**重要**：对于公式密集的文档，优先使用400 DPI以确保下标、符号等细节清晰可辨。

**公式页面必须使用500 DPI**：含有大量下标、上标、希腊字母的页面，300-400 DPI不足以区分微小符号差异。宁可文件大一些，也不要因分辨率不足导致符号识别错误。

#### Step 1.5: 图像增强预处理（必须执行）

对转换后的图像进行增强处理，提高识别准确性。这一步不可跳过——增强后的图像能显著减少转录错误：

```bash
# 标准增强
python <skill-dir>/scripts/enhance_image.py <temp-dir>/page-XX.png <temp-dir>/enhanced-XX.png standard

# 公式专用增强（用于公式密集的页面）
python <skill-dir>/scripts/enhance_image.py <temp-dir>/page-XX.png <temp-dir>/enhanced-XX.png strong

# 批量增强
python <skill-dir>/scripts/enhance_image.py --batch <temp-dir>/ <temp-dir>/enhanced/ standard
```

**增强级别说明**：
- `light`: 轻度增强，适用于质量较好的图像
- `standard`: 标准增强，适用于大多数情况
- `strong`: 强力增强，适用于模糊或低质量图像

**公式页面必须使用 `strong` 增强**：标准增强可能不足以区分密集公式中的微小符号差异。对于含有下标、上标、希腊字母的页面，使用 `strong` 级别增强可以显著提高符号识别准确性。

#### Step 2: Read and transcribe each page

For each page in the batch:

1. **Read the page image** (推荐使用增强后的图像) using the Read tool (multimodal)
2. **Transcribe ALL content verbatim** — every word, every formula, every table cell:
   - Body text: transcribe verbatim, including footnotes
   - Formulas: convert to LaTeX (`$$...$$` for display, `$...$` for inline)
   - Tables: convert to markdown table format, preserving all cells
   - Code: wrap in ```code blocks```
   - Figure references: note the figure number and caption
   - Cross-references: preserve references like "见公式(1-5)" or "如图2-3所示"
   - Lists: preserve numbered and bulleted lists with nesting
   - Page headers/footers: extract chapter/section titles for context

3. **双趟模式（Two-Pass）验证**：

   **核心思路**：将"边写边验证"改为"先完整输出，再统一审核"。这样每页只需2次API调用（转录+审核），而不是几十次。

   **Pass 1: 完整转录**
   - 读取页面图像，完整输出该页的所有Markdown内容
   - 包括所有文字、公式、表格、图注
   - 不要中途停下来验证，一口气写完

   **Pass 2: 审稿人审核**
   Pass 1完成后，将原图和生成的Markdown一起发送，使用以下审稿人提示词：

   ```
   你是专业的PDF转Markdown审稿人。请对比原图和已生成的Markdown，找出以下问题：
   1. 遗漏的内容（文字、公式、表格、图注）
   2. 公式符号错误（变量名、下标、上标、希腊字母）
   3. 文字转录错误（错别字、标点、数字）
   4. 格式问题（LaTeX语法、表格对齐）

   高风险检查点：
   - $\alpha$ vs $a$, $\theta$ vs $0$, $\phi$ vs $\varphi$
   - $x_i$ vs $x_n$, $\sigma$ vs $\delta$, $\mu$ vs $u$
   - 分数结构、指数位置、根号范围
   - 矩阵维度、求和/积分上下限

   输出格式：直接输出修正后的完整Markdown，不要解释修改内容。
   ```

   **为什么这样更有效**：
   - 模型在"审核模式"下更专注，不容易陷入"确认偏误"
   - 一次性对比整页内容，能发现跨公式的关联错误
   - API调用从几十次降到2次，速度提升10-20倍

4. **Append content immediately to the output file** (do NOT accumulate in memory)

5. **Update tracking.json** for this page:
```json
{
  "page": 14,
  "section": "绪论",
  "content_type": ["text", "equation", "figure_ref"],
  "equations": ["(0-1)", "(0-2)"],
  "figures": ["图0-1 飞行控制系统的基本组成"],
  "tables": [],
  "word_count_approx": 350,
  "status": "complete"
}
```

#### 分区域识别策略（用于公式密集页面）

对于公式密集的页面，使用分区域识别提高准确性：

```bash
# 1. 将页面分割成多个区域（使用crop_images.py）
python <skill-dir>/scripts/crop_images.py <page-image> <output-dir> --mode grid --rows 2 --cols 2

# 2. 对每个区域单独识别
# 3. 合并识别结果
```

**区域划分建议**：
- 文本区域：正常识别
- 公式区域：使用strong增强 + 局部放大
- 表格区域：使用standard增强

**公式局部放大**：
对于复杂公式，可以：
1. 在图像中定位公式位置
2. 裁剪公式区域
3. 放大2-3倍
4. 单独识别
5. 合并到完整页面中

#### 图像增强与放大验证（补充参考）

> **注意**：在Two-Pass模式下，Pass 2的审稿人会自动发现符号错误，通常不需要手动裁剪放大。以下内容仅在以下情况使用：
> - Pass 2未能发现错误但用户报告仍有问题
> - 需要对特定公式进行深度验证
> - 教学或调试目的

**快速命令**：
```bash
# 横向切条放大（默认5倍）
python <skill-dir>/scripts/crop_formula_regions.py <page-image> <output-dir> --zoom 5

# 紧凑裁剪（推荐，避免API下采样）
python <skill-dir>/scripts/crop_formula_regions.py <page-image> <output-dir> --zoom 3

# 批量处理
python <skill-dir>/scripts/crop_formula_regions.py --batch <source-dir> <output-dir> --zoom 5
```

<details>
<summary>详细代码示例（点击展开）</summary>

##### 横向切条策略（替代左中右三等分）

**问题**：左中右三等分不符合阅读习惯，且会切断跨区域的公式

**解决方案**：将竖长的PDF页面切成多个横向细条，从上到下逐条阅读和放大

```python
from PIL import Image, ImageEnhance

def slice_page_horizontal(img_path, output_dir, strip_height=300):
    """
    将竖长的PDF页面切成多个横向细条
    strip_height: 每条的高度（像素），默认300px
    
    优势：
    - 符合从上到下的阅读习惯
    - 不会切断跨区域的公式（同一公式在连续的条中）
    - 可以逐条增强和识别，加快速度
    """
    img = Image.open(img_path)
    w, h = img.size
    strips = []
    
    for i in range(0, h, strip_height):
        end = min(i + strip_height, h)
        strip = img.crop((0, i, w, end))
        strip_path = f'{output_dir}/strip_{i:04d}_{end:04d}.png'
        strip.save(strip_path)
        strips.append(strip_path)
    
    return strips

def enhance_and_zoom_strip(strip_path, zoom_level=5):
    """
    增强并放大单个横条
    """
    img = Image.open(strip_path)
    
    # 增强图像
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.5)
    
    # 放大
    zoomed = img.resize((img.width * zoom_level, img.height * zoom_level), Image.LANCZOS)
    zoomed_path = strip_path.replace('.png', f'_zoom{zoom_level}x.png')
    zoomed.save(zoomed_path)
    
    return zoomed_path

# 使用示例：将页面切成横条并逐条放大
strips = slice_page_horizontal('source/page-XX.png', 'images/strips', strip_height=300)
for strip_path in strips:
    enhance_and_zoom_strip(strip_path, zoom_level=5)
```

##### 2. 自适应放大策略（替代固定放大）

**不是每个公式都放大，而是有选择性地放大**：

**需要放大的区域**：
- 复杂公式（有下标、分数、根号、矩阵）
- 关键数字和符号（如类别标签、向量格式）
- 之前容易出错的模式（如Rayleigh分布、联合概率密度）
- 模糊或不清晰的区域

**不需要放大的区域**：
- 简单文字（段落文字、标题）
- 已经清晰的公式
- 页眉页脚等无关区域

**判断方法**：
1. 先整体读取页面，理解内容
2. 识别出需要验证的关键区域
3. 只对这些区域进行放大验证

```python
def adaptive_zoom(page_image, regions_to_verify):
    """
    自适应放大：只对需要验证的区域进行放大
    regions_to_verify: 需要验证的区域列表 [(x1,y1,x2,y2), ...]
    """
    img = Image.open(page_image)
    
    # 增强图像
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.5)
    
    for i, (x1, y1, x2, y2) in enumerate(regions_to_verify):
        cropped = img.crop((x1, y1, x2, y2))
        zoomed = cropped.resize((cropped.width * 5, cropped.height * 5), Image.LANCZOS)
        zoomed.save(f'images/region_{i}_zoom5x.png')
```

##### 3. 先整体后局部的工作流

**Step 1: 整体扫描（快速）**
- 读取整页图像（不放大）
- 识别页面类型：文本页、公式页、图表页、混合页
- 确定需要转录的区域（跳过页眉页脚等无关区域）

**Step 2: 分区转录（中速）**
- 将页面分成逻辑区域（段落、公式、表格）
- 每个区域单独转录
- 公式转录时使用LaTeX格式
- 文字转录时保持原样

**Step 3: 验证重点（按需）**
- 只对高风险区域进行放大验证
- 不是每个公式都放大，而是有选择性地放大
- 利用多模态能力判断哪些区域需要验证

##### 4. 公式定位方法

**如何在图像中找到复杂公式的位置**：

**方法A：基于页面结构定位**
1. 先读取增强后的整页图像
2. 根据页面布局估算坐标：
   - 页边距：通常左边距50-100px，右边距50-100px
   - 行高：正文约30-40px，公式约40-60px
   - 段落间距：约20-30px
3. 公式通常位于段落之间，居中显示

**方法B：基于文本参考定位**
1. 找到公式前后的文字（如"其中"、"定义"、"如下"）
2. 在图像中定位这些文字的大致Y坐标
3. 公式通常在这些文字的下方或中间

**方法C：渐进式定位**
1. 先用3倍放大查看整页概览
2. 确定公式大致区域
3. 再用5-8倍放大查看具体公式

**坐标估算示例**：
```
页面尺寸：1400 x 2000 (典型A4在400DPI)
页边距：左80, 右80, 上60, 下60
内容区域：80-1320 (宽1240), 60-1940 (高1880)

公式通常在：
- X: 200-1200 (居中，左右留白)
- Y: 根据段落位置估算
```

##### 实际使用示例

**场景1：验证整个页面的所有内容**
```python
from PIL import Image, ImageEnhance

# 1. 增强图像
img = Image.open('source/page-XX.png')
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.8)
enhancer = ImageEnhance.Sharpness(img)
img = enhancer.enhance(2.5)

# 2. 分成左中右三个区域，每个区域放大5倍
w, h = img.size
regions = {
    'left': (0, 0, w//3, h),
    'center': (w//3, 0, 2*w//3, h),
    'right': (2*w//3, 0, w, h)
}

for name, coords in regions.items():
    cropped = img.crop(coords)
    zoomed = cropped.resize((cropped.width * 5, cropped.height * 5), Image.LANCZOS)
    zoomed.save(f'images/page-XX-{name}_zoom5x.png')
    print(f'保存 page-XX-{name}_zoom5x.png')

# 3. 用Read工具读取每个放大后的图像，逐区域验证
```

**场景2：验证一个特定的长公式**
```python
from PIL import Image, ImageEnhance

# 假设公式在页面中的位置是 (100, 1400, 1400, 1600)
# 公式宽度 1300px，超过页面宽度的60%，需要分段放大

img = Image.open('source/page-XX.png')
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.8)
enhancer = ImageEnhance.Sharpness(img)
img = enhancer.enhance(2.5)

# 分成3段
left, top, right, bottom = 100, 1400, 1400, 1600
segment_width = (right - left) // 3

for i in range(3):
    seg_left = left + i * segment_width
    seg_right = left + (i + 1) * segment_width if i < 2 else right
    cropped = img.crop((seg_left, top, seg_right, bottom))
    zoomed = cropped.resize((cropped.width * 5, cropped.height * 5), Image.LANCZOS)
    zoomed.save(f'images/formula-seg{i+1}_zoom5x.png')
    print(f'保存 formula-seg{i+1}_zoom5x.png')

# 用Read工具读取每个分段，逐段验证公式
```

**场景3：验证文字内容**
```python
from PIL import Image, ImageEnhance

# 假设要验证一段文字，位置在 (80, 500, 1320, 600)
img = Image.open('source/page-XX.png')
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.8)
enhancer = ImageEnhance.Sharpness(img)
img = enhancer.enhance(2.5)

# 裁剪文字区域并放大5倍
cropped = img.crop((80, 500, 1320, 600))
zoomed = cropped.resize((cropped.width * 5, cropped.height * 5), Image.LANCZOS)
zoomed.save('images/text-verify_zoom5x.png')

# 用Read工具读取放大后的文字，与markdown中的文字逐字对比
```

##### 3. 多轮迭代验证流程

**第一轮：整体概览（3倍）**
- 查看页面整体布局
- 确定公式和文字的大致位置
- 识别需要重点验证的区域

**第二轮：区域放大（5倍）**
- 对每个公式区域单独放大
- 检查下标、符号、分数结构
- 对比文字内容是否正确

**第三轮：细节验证（8倍）**
- 对可疑区域进一步放大
- 检查微小细节（点号、撇号、上下标）
- 逐字符对比确认

##### 4. 文字校验（不只是公式！）

**文字校验清单**：
- [ ] 段落文字是否完整转录（无遗漏、无添加）
- [ ] 中文标点是否正确（，。；：等）
- [ ] 数字格式是否一致（1,234 vs 1234）
- [ ] 英文大小写是否正确
- [ ] 专业术语是否准确（如"似然"不是"类似"）
- [ ] 章节标题编号是否正确
- [ ] 图表引用是否正确（"见图2-3"不是"见图2-4"）

**文字校验方法**：
```python
def verify_text_segment(img_path, bbox, expected_text):
    """
    校验特定区域的文字内容
    """
    # 1. 裁剪该区域
    img = Image.open(img_path)
    cropped = img.crop(bbox)

    # 2. 放大5倍查看
    zoomed = cropped.resize((cropped.width * 5, cropped.height * 5), Image.LANCZOS)
    zoomed.save('temp_text_verify.png')

    # 3. 用Read工具读取放大后的图像
    # 4. 与expected_text逐字对比
    # 5. 记录差异并修正
```

**文字校验重点区域**：
- 章节标题（编号、名称）
- 公式前后的说明文字
- 图表标题和标注
- 脚注和引用
- 表格内容

</details>

#### Step 3: Batch verification (after each batch)

After processing all pages in a batch, execute these checks:

1. **Page count check**: Verify all pages in the batch are marked "complete" in tracking.json
2. **Section continuity**: Verify section/heading numbering is sequential (no gaps)
3. **Equation numbering**: Verify equation tags are sequential within each chapter (no gaps or duplicates)
4. **Figure numbering**: Verify figure references are sequential
5. **Table numbering**: Verify table references are sequential
6. **公式验证**：运行公式验证脚本检查语法和结构
   ```bash
   python <skill-dir>/scripts/verify_formulas.py <output-dir>/document.md
   ```
7. **抽样深度验证**：随机抽取3-5个公式，使用Read工具重新读取原图，与markdown中的公式逐字符对比
8. **Spot-check**: Randomly select 1-2 pages from the batch, re-read the original image, and compare against the written markdown to confirm completeness

If any check fails, re-process the problematic pages before continuing.

### Phase 3: Image Processing (Image Mode Only)

1. Crop identified figures from page images using PIL:
   ```python
   from PIL import Image
   img = Image.open("page_image.png")
   cropped = img.crop((left, upper, right, lower))
   cropped.save("output/figure_name.png")
   ```

2. Use the multimodal Read tool to verify each crop is complete and correct
3. Adjust crop coordinates if content is cut off
4. Place cropped images in the output directory

### Phase 4: Final Verification

After all batches are complete, execute ALL of the following steps in order. Do not skip any step.

1. **Run the post-processing script** to fix common formatting issues:
   ```bash
   python <skill-dir>/scripts/postprocess.py <output-dir>
   ```
   This fixes: broken matrix separators, LaTeX in table cells, duplicate content.

2. **Run the completeness verification script**:
   ```bash
   python <skill-dir>/scripts/verify_completeness.py <output-dir>
   ```

3. **Run the unified formula verification script** (combines syntax + structure checks):
   ```bash
   python <skill-dir>/scripts/verify_formulas.py <output-dir>/document.md
   ```
   This checks: LaTeX syntax, bracket matching, symbol completeness, environment matching, common OCR errors.

4. **Run the page-by-page content verification** — this is the most critical quality gate:
   ```bash
   python <skill-dir>/scripts/verify_page_content.py <output-dir>
   ```
   This script reads tracking.json and the markdown, then verifies that all tracked equations, figures, tables, and sections for each page actually appear in the markdown. It reports missing content per page.

5. **Run cross-validation on ALL pages** — compare each page image against the markdown:
   ```bash
   python <skill-dir>/scripts/cross_validate.py <source-dir> <output-dir>/document.md
   ```
   This reads every page image and cross-references it against the markdown, reporting any discrepancies.

6. **If ANY verification script reports errors, fix them before proceeding.** Re-run the failing script after fixes until it passes.

7. **Generate the conversion report** with all verification results:
```markdown
---

## 转换报告

| 指标 | 数值 |
|------|------|
| 总页数 | X |
| 已处理页数 | X |
| 公式数量 | X |
| 图表数量 | X |
| 表格数量 | X |
| 章节数量 | X |
| 批次数 | X |
| 完整性检查 | 通过/未通过 |
| 逐页内容验证 | 通过/未通过 (X页通过/X页有问题) |
| 交叉验证 | 通过/未通过 (X页通过/X页有问题) |
| 公式验证 | X个问题/通过 |

### 验证详情
- 括号匹配：✓/✗
- 符号完整性：✓/✗
- LaTeX语法：✓/✗
- 逐页内容验证：X页通过，X页有问题
- 交叉验证：X页通过，X页有问题
```

8. **Final spot-check**: Read 3-5 random pages from the full document, compare against original PDF
9. **重点验证**：检查用户之前指出的问题（如第2章第9题、第10题）

### Phase 5: Cleanup

Remove temporary image files if the user doesn't need them:
```bash
rm -rf <temp-dir>
```

## Content Transcription Rules

### Text

- Transcribe **every word** from the original. Do not summarize, abbreviate, or omit.
- Preserve paragraph breaks and spacing
- Preserve emphasis (bold, italic) where visually clear
- Preserve numbered and bulleted lists with their nesting levels
- Include footnotes and endnotes

### Formulas

- **Display math**: Use `$$...$$` blocks. Preserve equation numbers with `\tag{x-x}`.
- **Inline math**: Use `$...$` for inline formulas within text.
- **Multi-line aligned formulas**: Use `\begin{aligned}...\end{aligned}` inside `$$...$$`
- **Matrices**: Use `\begin{bmatrix}...\end{bmatrix}` or `\begin{pmatrix}...\end{pmatrix}`
- **Piecewise functions**: Use `\begin{cases}...\end{cases}`
- **Fractions**: Use `\frac{a}{b}`
- **Greek letters**: `\alpha`, `\beta`, `\gamma`, `\delta`, `\theta`, `\phi`, `\psi`, `\omega`, etc.
- **Subscripts/Superscripts**: `x_i`, `C_{L\alpha}`, `V^2`
- **Vector/derivative notation**: `\dot{x}`, `\bar{X}`, `\ddot{x}`
- **Operators**: `\sin`, `\cos`, `\tan`, `\arctan`, `\sqrt`, `\int`, `\sum`
- **Cross-references**: Preserve references like "见式(1-5)" or "由式(2-13)可知"

### Formula Accuracy Verification

When transcribing formulas from page images, common OCR errors include:

- **Missing time derivative dots**: `\alpha` instead of `\dot{\alpha}`, `\beta` instead of `\dot{\beta}`
- **Wrong subscripts**: `C_L` instead of `C_l`, `M_a` instead of `M_\alpha`
- **Confused Greek/Latin**: `\alpha` vs `a`, `\theta` vs `0`, `\phi` vs `\varphi`
- **Wrong signs**: `+` instead of `-` in force/moment equations
- **Missing terms**: Incomplete fractions, missing square roots
- **Truncated matrices**: Wrong dimensions or missing rows/columns
- **Duplicate definitions**: Same variable defined multiple times with different formulas

After transcribing each page, verify:
1. Every `\dot{x}` and `\ddot{x}` has visible dots in the original
2. Subscripts match the original exactly (e.g., `C_{m_\alpha}` not `C_{ma}`)
3. Matrix dimensions are consistent (3x3 for coordinate transforms, etc.)
4. No variable is defined twice with contradictory formulas
5. Force/moment balance equations have consistent signs

If a formula looks suspicious, re-read the original page image to verify.

### 防止幻觉的转录规则

**核心原则**：如果看不清，宁可标记为[待确认]，也不要猜测。

**公式转录时的检查清单**：
1. **变量名确认**：是 $\alpha$ 还是 $\theta$？是 $w_n$ 还是 $\epsilon_i$？
2. **下标确认**：是 $x_i$ 还是 $x_n$？是 $\sigma^2$ 还是 $\sigma_w^2$？
3. **结构确认**：分数、指数、根号的位置是否正确？
4. **完整性确认**：参数声明、系数、常数是否遗漏？

**文字转录时的检查清单**：
1. **段落完整性**：是否遗漏了句子或段落？
2. **标点符号**：中文标点（，。；：）还是英文标点（,.;:）？
3. **数字格式**：1,234 还是 1234？小数点是.还是，？
4. **专业术语**：似然（likelihood）不是类似，先验（prior）不是先后
5. **引用编号**：见图2-3还是见图2-4？式(3.4.22)还是式(3.4.23)？
6. **章节编号**：4.2.1还是4.2.2？作业1还是作业2？

**高风险模式**（需要特别注意）：
- Rayleigh分布：$\frac{1}{\alpha^2} x e^{-x^2 / 2\alpha^2}$ 容易被误写为 $\frac{1}{\theta} e^{-\frac{x}{\theta}}$
- 联合概率密度：$p(x_1, x_2 ; \rho)$ 容易遗漏参数声明
- 高斯噪声：$w_n$ 容易被误写为 $\epsilon_i$
- 贝叶斯公式：后验分布的参数结构复杂，需要仔细核对
- 中文标点：逗号、句号、分号容易被误写为英文标点
- 引用编号：图表和公式的引用编号容易出错

**写后验证流程**：
每写完一个公式或一段文字，立即：
1. 重新读取原PDF图像
2. 找到该公式/文字的位置
3. 逐字符对比（公式对比符号，文字对比字符）
4. 如有差异，修正后再继续

**验证顺序**：
1. 先验证公式（高风险）
2. 再验证公式前后的说明文字
3. 最后验证段落整体完整性

### Tables

- Convert to markdown table format
- Preserve all cells — do not merge or omit rows/columns
- For complex tables with merged cells, use HTML table syntax or describe the structure
- Preserve table numbers and captions (e.g., "表1-1 力、力矩和速度的定义")

**CRITICAL: LaTeX in Markdown Tables**

Markdown table cells have special parsing rules that break LaTeX:

- **NEVER put `$$...$$` display math inside table cells** — it won't render
- **For simple inline math**: Use `$...$` inside cells (this usually works)
- **For complex formulas with matrices**: Move the formula OUTSIDE the table, reference it by number
- **For line breaks in table headers**: Use `<br>` not `\`
- **Backslash `\` in table cells**: Gets consumed as escape character — avoid when possible

Example of CORRECT table with formulas:
```markdown
| Variable | Formula |
|:---:|:---:|
| Force | $F = ma$ |
| Matrix | See Eq. (1-1) below |

$$\begin{bmatrix} F_x \\ F_y \\ F_z \end{bmatrix} = \begin{bmatrix} ma_x \\ ma_y \\ ma_z \end{bmatrix} \tag{1-1}$$
```

Example of WRONG approach (will break):
```markdown
| Variable | Formula |
|:---:|:---:|
| Force | $\begin{bmatrix}F_x\F_y\F_z\end{bmatrix}$ |  ← BROKEN: \ consumed by markdown
```

### Figures

- Note figure number and caption (e.g., "图1-4 飞机典型操纵机构示意图")
- In text mode: describe the figure content briefly
- In image mode: crop and include the figure image

### Cross-References

- Preserve all "见图x-x", "如式(x-x)所示", "参见表x-x" type references
- These are critical for document coherence and must not be omitted

## LaTeX Conventions

- Display math: `$$\int_0^1 f(x) dx$$`
- Inline math: `$\alpha$, $\beta$`
- Matrices: `\begin{bmatrix}...\end{bmatrix}`
- Named equations: `$$...\tag{1}$$`
- Fractions: `\frac{a}{b}`
- Greek: `\alpha`, `\beta`, `\phi`, `\theta`, `\psi`, etc.
- Subscripts: `x_i`, `C_{XT}`
- Superscripts: `x^2`, `V_T^2`
- Vector arrows: `\dot{x}`, `\bar{X}`
- Operators: `\sin`, `\cos`, `\arctan`, `\sqrt`
- Aligned equations: `\begin{aligned}...\end{aligned}`
- Cases/piecewise: `\begin{cases}...\end{cases}`

### Matrix Row Separators

Inside `\begin{bmatrix}...\end{bmatrix}` (and pmatrix, cases, aligned), use `\\` for row separators:

**CORRECT:**
```latex
$$\begin{bmatrix} x \\ y \\ z \end{bmatrix}$$
$$\begin{cases} a = 1 \\ b = 2 \end{cases}$$
```

**WRONG (will not render):**
```latex
$$\begin{bmatrix} x \ y \ z \end{bmatrix}$$  ← single \ is not a row separator
$$\begin{cases} a = 1 \ b = 2 \end{cases}$$
```

The `\\` must be a DOUBLE backslash. A single `\` followed by a space is just a space in LaTeX.

### Content Duplication Prevention

When appending content to the output file, ALWAYS verify before writing:
1. Read the last 5-10 lines of the output file
2. Confirm the content you're about to append is NOT already present
3. If it appears to be a duplicate, SKIP it and note the issue in tracking.json

This prevents the common error of accidentally appending the same page content twice.

## Image Cropping Guidelines

- Use `pdftoppm -r 200` for consistent resolution (200 DPI)
- Crop tightly around the figure content — remove page margins and headers/footers
- Include figure captions in the crop
- For multi-figure pages, crop each figure separately
- After cropping, always verify with multimodal Read that nothing is cut off
- If content extends beyond initial crop, adjust coordinates and re-crop

## Common Error Patterns — 高频出错模式

以下是从实际转换中总结的高频错误模式。转录时必须特别注意：

### 公式符号混淆（最高频错误）
| 错误类型 | 示例 | 如何避免 |
|---|---|---|
| 希腊字母vs拉丁字母 | $\alpha$ 写成 $a$，$\theta$ 写成 $0$ | 放大5倍以上，看笔画形状 |
| 下标错误 | $x_i$ 写成 $x_n$，$w_{ij}$ 写成 $w_{ii}$ | 逐字符放大对比 |
| 上标/下标位置 | $x^2$ 写成 $x_2$，$a_i^T$ 写成 $a_T^i$ | 检查字符垂直位置 |
| 相似符号 | $\phi$ vs $\varphi$，$\epsilon$ vs $\varepsilon$ | 对照原图笔画 |
| 求和上下限 | $\sum_{i=1}^{N}$ 写成 $\sum_{i=1}^{n}$ | 检查大小写 |
| 矩阵元素 | 行列数不一致，元素位置错位 | 逐行逐列核对 |

### 文字识别错误
| 错误类型 | 示例 | 如何避免 |
|---|---|---|
| 中文形近字 | "似然" 写成 "类似" | 理解上下文语义 |
| 数字格式 | 1,234 写成 1234 | 检查逗号分隔符 |
| 英文大小写 | "MLE" 写成 "Mle" | 专有名词保持大写 |
| 引用编号 | "式(3.4.22)" 写成 "式(3.4.23)" | 逐位核对编号 |

### 公式结构错误
| 错误类型 | 示例 | 如何避免 |
|---|---|---|
| 分数层级 | $\frac{a}{b+c}$ 写成 $\frac{a}{b}+c$ | 检查花括号范围 |
| 嵌套根号 | $\sqrt{a+\sqrt{b}}$ 结构错误 | 逐层检查括号 |
| 条件概率 | $p(x|C_i)$ 写成 $p(x,C_i)$ | 检查竖线位置 |

## Quality Checklist

Before delivering the final output:

### 内容完整性
- [ ] All pages processed and marked "complete" in tracking.json
- [ ] All sections from the original PDF are present
- [ ] All formulas are valid LaTeX and render correctly
- [ ] All equation numbers are sequential and match original
- [ ] All figure numbers are sequential and match original
- [ ] All table numbers are sequential and match original
- [ ] All tables are properly formatted with all cells
- [ ] All figure references point to existing image files (image mode)
- [ ] No text is garbled or missing
- [ ] No "etc.", "..." or summarizing shortcuts — all content transcribed
- [ ] Heading hierarchy matches the original document
- [ ] Page numbers or section references are preserved where meaningful
- [ ] Cross-references ("见图x-x", "式(x-x)") are preserved
- [ ] Spot-check passed on random pages
- [ ] Conversion report generated with accurate statistics

### 公式验证
- [ ] 每个公式都经过写后验证（重新读取原图对比）
- [ ] 变量名与原PDF一致（无 $\alpha/\theta$ 混淆）
- [ ] 下标与原PDF一致（无 $x_i/x_n$ 混淆）
- [ ] 参数声明完整（$p(x; \theta)$ 不是 $p(x)$）
- [ ] 分数、指数、根号结构正确
- [ ] 无遗漏的系数或常数
- [ ] 公式结构验证脚本通过
- [ ] 公式语法验证脚本通过
- [ ] 抽样深度验证通过（3-5个公式逐字符对比）
- [ ] 交叉验证脚本通过

### 文字验证（新增！）
- [ ] 段落文字完整转录（无遗漏、无添加）
- [ ] 中文标点正确使用（，。；：等）
- [ ] 数字格式一致（1,234 vs 1234）
- [ ] 英文大小写正确
- [ ] 专业术语准确（似然、先验、后验等）
- [ ] 章节标题编号正确
- [ ] 图表引用编号正确（见图2-3不是见图2-4）
- [ ] 公式引用编号正确（式(3.4.22)不是式(3.4.23)）

### 放大验证
- [ ] 横向页面分区域放大（左/中/右）
- [ ] 宽公式分段放大（至少3段）
- [ ] 每个区域都经过5倍以上放大验证
- [ ] 微小细节（点号、撇号、上下标）经过8倍放大确认

## Markdown格式一致性指南

### 标题层级规范

保持所有输出文件的标题层级一致：

```markdown
# 章节标题              # 一级标题：简短

## 编号或小节名         # 二级标题：简短

正文内容写在这里...     # 正文：详细描述

（1）子问题             # 正文：子编号（使用中文括号）
```

**重要：标题必须简短！**
- ❌ 错误：`## 1. 有一组数据集，样本均是平面上的二维数据...`（标题太长，导致字体缩小）
- ✅ 正确：`## 1.` + 正文描述
- ❌ 错误：`## 第一节 飞行控制系统的基本组成和工作原理`（标题太长）
- ✅ 正确：`## 1.1 飞行控制系统的基本组成` + 正文描述

长标题会导致渲染器自动缩小字体，造成"字体大小不一致"的问题。

### 不同场景的标题格式

**教材/习题**：
```markdown
# 第二章 统计与优化基础
## 2.1 概率论基础
## 习题
### 1.
### 2.
```

**论文/报告**：
```markdown
# 基于深度学习的图像分类方法研究
## 摘要
## 1 引言
## 2 相关工作
### 2.1 卷积神经网络
### 2.2 迁移学习
```

**技术文档**：
```markdown
# API参考手册
## 用户管理
### 创建用户
### 查询用户
```

### 公式格式规范

1. **Display Math**：使用 `$$...$$` 独占一行
2. **Inline Math**：使用 `$...$` 嵌入文本
3. **多行公式**：使用 `\begin{aligned}...\end{aligned}`
4. **矩阵**：使用 `\begin{bmatrix}...\end{bmatrix}`

### 字体大小一致性

Markdown渲染器对不同元素使用不同字体大小：
- **一级标题 (#)**：最大
- **二级标题 (##)**：中等
- **正文**：标准大小
- **公式**：根据渲染器不同可能有差异

**建议**：
1. 保持标题层级一致，不要跳级
2. 使用标准的Markdown语法，避免HTML标签
3. 如果需要特殊格式，使用LaTeX数学模式

### 表格格式规范

```markdown
| 列1 | 列2 | 列3 |
|:---:|:---:|:---:|
| 内容 | 内容 | 内容 |
```

- 使用冒号对齐：`:---:` 居中，`:---` 左对齐，`---:` 右对齐
- 表格内容保持简洁，复杂公式移到表格外
