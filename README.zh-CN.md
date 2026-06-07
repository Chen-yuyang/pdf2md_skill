# PDF2MD — PDF 转 Markdown 技能

[English README](README.md)

一个 **Claude Code 技能**，能够将 PDF 文档精确复刻为带有 LaTeX 公式的 Markdown 格式。专为标准文本提取失败的 PDF 设计——自定义字体编码、嵌入式字体、扫描文档、以及公式密集的学术论文。

## 核心优势

与传统 PDF 转 Markdown 工具（如 PyMuPDF、pdfplumber、pdfminer 等）相比，PDF2MD 采用**多模态图像识别方案**：

| 特性 | PDF2MD | 传统工具 (PyMuPDF, pdfplumber, pdfminer 等) |
|---|---|---|
| **核心方案** | 将页面转为图像，利用 LLM 多模态视觉能力转录 | 程序化提取嵌入式文本流 |
| **LaTeX 公式** | 完整 LaTeX 渲染 + 结构化验证 | 有限或无公式支持 |
| **扫描件 PDF** | 原生支持（读取图像） | 需要 OCR 层，经常失败 |
| **自定义字体** | 无问题（读取视觉输出） | 编码不匹配导致乱码 |
| **表格** | 忠实转录为 markdown/HTML 表格 | 格式经常损坏 |
| **图表/图形** | 可裁剪并作为图像包含 | 通常丢失 |
| **精度验证** | 5 阶段验证流水线 | 无验证机制 |
| **目录感知导航** | 解析目录构建章节-页码映射 | 逐页盲目提取 |

## 工作原理

### 核心原则

将每一页 PDF 转换为高分辨率图像（300-500 DPI），然后利用 Claude 的多模态能力进行视觉阅读和转录。这绕过了所有文本提取问题，能够忠实捕获公式、图表、表格和布局。

### 基本准则

> **每一页必须完整转录。不允许总结、省略或使用"等"——原文中的每一个字、每一个公式、每一个表格单元格都必须出现在输出中。**

### 工作流程概览

```
┌─────────────────────────────────────────────────────────┐
│ 阶段一：分析与设置                                        │
│  ├── 读取 PDF 结构和页数                                  │
│  ├── 解析目录（如有）→ 章节-页码映射                        │
│  ├── 计算页码偏移量                                       │
│  └── 创建输出目录和 tracking.json                         │
├─────────────────────────────────────────────────────────┤
│ 阶段二：批次处理（每批 10-15 页）                           │
│  ├── 页面转 PNG 图像 (pdftoppm, 400 DPI)                 │
│  ├── 图像增强（对比度、锐度、去噪）                          │
│  ├── 第一趟：多模态视觉完整转录                             │
│  ├── 第二趟：审稿人审核（对比图像与 markdown）                │
│  └── 批次验证（公式、编号、抽查）                            │
├─────────────────────────────────────────────────────────┤
│ 阶段三：图像处理（仅图像模式）                              │
│  └── 从页面图像中裁剪图表、示意图、表格                      │
├─────────────────────────────────────────────────────────┤
│ 阶段四：最终验证（所有步骤必须执行）                         │
│  ├── postprocess.py — 修复矩阵分隔符、重复内容              │
│  ├── verify_completeness.py — 页面/章节/公式编号连续性       │
│  ├── verify_formulas.py — LaTeX 语法和括号匹配              │
│  ├── verify_page_content.py — 逐页内容审计                  │
│  ├── cross_validate.py — 图像与 markdown 对比              │
│  └── 生成转换报告                                         │
├─────────────────────────────────────────────────────────┤
│ 阶段五：清理                                              │
│  └── 删除临时图像文件                                      │
└─────────────────────────────────────────────────────────┘
```

### 双趟转录模型

每页经历两趟处理以确保最大精度：

**第一趟 — 完整转录**：读取页面图像，一次性输出该页的所有 Markdown 内容（文字、公式、表格、图表）。

**第二趟 — 审稿人审核**：将原图和生成的 Markdown 一起发送给审稿人提示词，系统性检查：
- 遗漏内容（文字、公式、表格单元格、图注）
- 公式符号错误（变量名、下标、上标、希腊字母）
- 转录错误（错别字、标点、数字）
- 格式问题（LaTeX 语法、表格对齐）

这将每页的 API 调用从几十次降低到仅 2 次，同时提高了准确性。

## 工具脚本

所有脚本位于 `scripts/` 目录，均可独立运行。

### 转换与处理

| 脚本 | 功能 |
|---|---|
| `pdf2images.py` | 使用 `pdftoppm` 将 PDF 页面转为 PNG 图像 |
| `enhance_image.py` | 图像预处理 — 对比度、锐度、去噪（3 级：light/standard/strong） |
| `batch_process.py` | 并行批处理 — PDF 转换、图像增强、公式裁剪 |
| `crop_images.py` | 从页面图像中裁剪指定区域（图表、表格） |
| `crop_formula_regions.py` | 将页面切成横向条带并放大，用于公式验证 |
| `slice_horizontal.py` | 横向切条 — 从上到下阅读顺序，不会切断跨区域公式 |
| `parse_toc.py` | 从 PDF 提取目录、计算页码偏移、定位章节/习题 |
| `postprocess.py` | 修复常见格式问题 — 破损的矩阵分隔符、表格中的 LaTeX、重复内容 |

### 验证与校验

| 脚本 | 功能 |
|---|---|
| `verify_completeness.py` | 检查所有页面已处理、章节/公式/图表/表格编号连续 |
| `verify_formulas.py` | LaTeX 语法验证 — 括号匹配、环境匹配、符号完整性 |
| `verify_formula_structure.py` | 语义公式检查 — 复杂度分析、常见 OCR 错误模式 |
| `verify_page_content.py` | 逐页内容审计 — 跟踪的公式/图表/表格是否出现在 markdown 中 |
| `cross_validate.py` | 源图像与 markdown 对比 — 缺失页面、内容密度、重复标签 |
| `pre_check.py` | 写入前 LaTeX 验证，支持常见 OCR 错误自动修正 |

## 安装

### 系统依赖

```bash
# Ubuntu/Debian:
sudo apt-get install poppler-utils pdftk

# macOS:
brew install poppler pdftk-java

# Windows (通过 scoop 或 chocolatey):
scoop install poppler pdftk
```

### Python 依赖

```bash
pip install Pillow
```

### 安装为 Claude Code 技能

将技能复制到 Claude Code 技能目录：

```bash
# 克隆本仓库
git clone git@github.com:Chen-yuyang/pdf2md_skill.git

# 复制到 Claude Code 技能目录
cp -r pdf2md_skill ~/.claude/skills/pdf2md
```

或创建符号链接：

```bash
ln -s /path/to/pdf2md_skill ~/.claude/skills/pdf2md
```

## 使用方法

### 作为 Claude Code 技能

安装后，在任何 Claude Code 对话中触发：

```
Convert this PDF to markdown: ./document.pdf
```

```
PDF转markdown: ./homework.pdf
```

```
提取第3章的习题: ./textbook.pdf
```

### 输出模式

1. **纯文本模式** (`text`)：纯 markdown + LaTeX 公式。所有内容转录为文本，图像描述或省略。
2. **图文模式** (`image`)：markdown + 文本 + 正确裁剪的图像（图表、示意图、表格、公式）。

### 命令行脚本

```bash
# 将 PDF 页面转为图像
python scripts/pdf2images.py document.pdf -o output/images --dpi 400

# 增强图像质量
python scripts/enhance_image.py input.png output.png strong

# 批量增强目录中的所有图像
python scripts/enhance_image.py --batch input_dir/ output_dir/ standard

# 裁剪公式区域并放大
python scripts/crop_formula_regions.py page.png output/ --zoom 5

# 并行批处理
python scripts/batch_process.py document.pdf output/ --pages 1-20 --dpi 400 --workers 4

# 解析目录
python scripts/parse_toc.py document.pdf --find-exercises "第3章"

# 后处理 markdown
python scripts/postprocess.py output/

# 运行所有验证脚本
python scripts/verify_completeness.py output/
python scripts/verify_formulas.py output/document.md
python scripts/verify_page_content.py output/
python scripts/cross_validate.py output/source/ output/document.md

# 预检查 LaTeX 并自动修正
python scripts/pre_check.py output/document.md --fix
```

## 输出结构

```
output/
├── document.md              # 主 markdown 文件（增量构建）
├── tracking.json            # 逐页内容跟踪
├── verification_report.txt  # 完整性验证报告
├── formula_verification_report.txt
├── page_content_verification_report.txt
├── cross_validation_report.txt
├── images/                  # 裁剪的图表（图像模式）
│   ├── cropped/
│   └── page-XX.png
└── source/
    └── page-XX.png          # 源页面图像
```

## DPI 选择指南

| 场景 | DPI | 说明 |
|---|---|---|
| 标准 PDF | 400 | 推荐方案，清晰度与文件大小平衡 |
| 模糊/低质量扫描件 | 500 | 高质量方案，用于细节验证 |
| 清晰数字 PDF | 300 | 仅当文件大小受限时使用 |
| 公式密集页面 | 500 | 下标、上标、希腊字母需要高分辨率 |

## 图像增强级别

| 级别 | 适用场景 | 效果 |
|---|---|---|
| `light` | 质量较好的图像 | 轻度对比度 +1.1x，锐度 +1.2x |
| `standard` | 大多数 PDF | 对比度 +1.2x，锐度 +1.3x，中值去噪 |
| `strong` | 模糊/低质量、公式密集 | 对比度 +1.4x，锐度 +1.5x，中值去噪，边缘增强 |

## 验证流水线

技能强制执行 5 阶段验证流水线，**不可跳过任何步骤**：

1. **完整性检查** — 所有页面已处理，编号连续无缺漏
2. **公式语法** — 括号匹配、LaTeX 环境配对、符号完整性
3. **逐页内容审计** — 每个跟踪的公式/图表/表格都出现在 markdown 中
4. **交叉验证** — 源图像与 markdown 对比，检查内容密度
5. **抽查** — 随机选取页面重新读取并与原文对比

如果任何验证脚本报错，必须修复问题并重新运行脚本直到通过。

## 常见错误模式

### 公式符号混淆（最高频错误）

| 错误类型 | 示例 | 预防方法 |
|---|---|---|
| 希腊字母 vs 拉丁字母 | `$\alpha$` 写成 `$a$` | 放大 5 倍以上，检查笔画形状 |
| 下标错误 | `$x_i$` 写成 `$x_n$` | 逐字符放大对比 |
| 上标位置 | `$x^2$` 写成 `$x_2$` | 检查字符垂直位置 |
| 相似符号 | `$\phi$` vs `$\varphi$` | 对照原图笔画 |
| 求和上下限 | `$\sum_{i=1}^{N}$` vs `$\sum_{i=1}^{n}$` | 检查大小写 |

### 文字识别错误

| 错误类型 | 示例 | 预防方法 |
|---|---|---|
| 中文形近字 | "似然" (likelihood) vs "类似" (similar) | 理解上下文语义 |
| 数字格式 | 1,234 vs 1234 | 检查逗号分隔符 |
| 引用编号 | "式(3.4.22)" vs "式(3.4.23)" | 逐位核对编号 |

## 适用场景对比

| 场景 | 推荐工具 |
|---|---|
| 含公式的学术论文 | **PDF2MD** |
| 扫描件文档 | **PDF2MD** |
| 自定义/嵌入字体导致乱码的 PDF | **PDF2MD** |
| 需要保留表格/图表布局的文档 | **PDF2MD** |
| 大量结构简单的 PDF 批量转换 | 传统工具（更快） |
| 文本流清晰可提取的 PDF | 传统工具（够用） |

## License

Proprietary. See LICENSE.txt for complete terms.

## 贡献

这是一个个人技能项目。如有问题或建议，请在 GitHub 上提交 issue。
