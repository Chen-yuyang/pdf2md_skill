# PDF2MD 技能发布报告

## 发布信息

| 项目 | 详情 |
|---|---|
| 仓库地址 | https://github.com/Chen-yuyang/pdf2md_skill |
| 发布日期 | 2026-06-07 |
| 初始提交 | `9ec653f` — feat: initial release of pdf2md skill |
| 文件总数 | 20 个文件，约 4916 行 |

## 发布流程

### 1. 仓库初始化

```bash
mkdir pdf2md_skill && cd pdf2md_skill
git init
git remote add origin git@github.com:Chen-yuyang/pdf2md_skill.git
```

### 2. 文件准备

从 `~/.claude/skills/pdf2md/` 复制技能文件到仓库目录，排除 `__pycache__/` 等缓存文件：

```
pdf2md_skill/
├── SKILL.md              # Claude Code 技能定义
├── README.md             # 英文文档
├── README.zh-CN.md       # 中文文档
├── LICENSE.txt           # MIT 许可证
├── requirements.txt      # Python 依赖 (Pillow)
├── .gitignore
├── PUBLISH_REPORT.md     # 本报告
└── scripts/              # 14 个 Python 工具脚本
    ├── pdf2images.py
    ├── enhance_image.py
    ├── batch_process.py
    ├── crop_images.py
    ├── crop_formula_regions.py
    ├── slice_horizontal.py
    ├── parse_toc.py
    ├── postprocess.py
    ├── pre_check.py
    ├── verify_completeness.py
    ├── verify_formulas.py
    ├── verify_formula_structure.py
    ├── verify_page_content.py
    └── cross_validate.py
```

### 3. 文档编写

#### README 内容

两份 README（中英文）包含以下内容：

- shields.io 徽章（Python 版本、License、Claude Code、LaTeX）
- Quick Start 快速上手
- 与传统 PDF 提取工具（PyMuPDF、pdfplumber、pdfminer）的对比表
- 核心原理说明（多模态视觉识别方案）
- 双趟转录模型详解
- 5 阶段工作流程图
- 14 个脚本的功能说明和命令行用法
- DPI 选择指南与图像增强级别
- 验证流水线详解
- 常见错误模式及预防方法
- 适用场景对比表

#### 文档迭代

第一版 README 中引用了 Microsoft MarkItDown 作为对比对象，后根据反馈移除，改为与通用传统工具对比，并用适用场景推荐表替代了针对特定产品的对比章节。

### 4. GitHub 仓库配置

#### 安装 GitHub CLI

```bash
winget install --id GitHub.cli
```

#### 认证

由于网络环境限制，浏览器自动认证失败，改用 SSH 协议认证：

```bash
gh auth login --git-protocol ssh --web
```

流程：终端显示一次性代码 → 浏览器打开 github.com/login/device → 输入代码 → 授权完成。

#### 设置仓库元数据

```bash
gh repo edit Chen-yuyang/pdf2md_skill \
  --description "Claude Code skill: convert PDF to Markdown with LaTeX formulas via multimodal vision" \
  --add-topic pdf,markdown,latex,claude-code,skill,converter,multimodal,academic,ocr,pdf-conversion
```

### 5. 提交记录

| 提交 | 说明 |
|---|---|
| `9ec653f` | feat: initial release of pdf2md skill — 20 files, 4916 insertions |
| `ccebf41` | docs: replace MarkItDown references with generic tool comparisons |
| `b35ecc9` | docs: add badges and quick start section |

## 发布后 Checklist

- [x] 仓库公开可访问
- [x] 中英文双语 README
- [x] shields.io 徽章
- [x] Quick Start 快速上手
- [x] 仓库 Description 已设置
- [x] Topics 标签已添加（10 个）
- [x] `.gitignore` 排除缓存和临时文件
- [x] LICENSE 文件
- [ ] 添加截图/GIF 演示（待补充）
- [ ] 提交到 awesome 列表（待补充）
- [ ] 社区推广（待补充）

## 经验总结

1. **文档先行**：README 的质量直接决定点击率和 star 数。对比表、流程图、Quick Start 是必备元素。
2. **避免点名批评**：第一版用 MarkItDown 做对比引发了反馈，改为通用工具对比 + 适用场景推荐更合适。
3. **Topics 很重要**：GitHub 搜索主要靠 Topics 标签匹配，必须全部小写，建议 8-10 个。
4. **网络问题备选方案**：中国大陆环境下 GitHub 浏览器认证可能超时，SSH 认证是更可靠的方案。
5. **排除缓存文件**：`__pycache__/`、`.pyc` 等必须通过 `.gitignore` 排除。
