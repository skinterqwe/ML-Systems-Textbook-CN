# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ML Systems Textbook（https://mlsysbook.ai/book/）技术教科书的中文翻译项目。支持两种翻译模式：

- **HTML 模式**（原有）：爬取原始 HTML → Gemini API 翻译 → 链接本地化 → 页头信息添加
- **QMD 模式**（主用）：读取本地 .qmd → 保护特殊元素 → Gemini 翻译 → 恢复 → Quarto 渲染 HTML

英文原版 Quarto website 源文件位于 `output/book/`，通过 GitHub Actions 在线构建并部署到 GitHub Pages。

**重要约束**：每次执行翻译只会将 `output/book/contents/` 中的英文 .qmd 文件替换成翻译后的中文版本，不会修改任何其他文件（包括 `_quarto.yml`、配置文件、脚本、扩展等）。

## 运行命令

```bash
# 安装依赖（需要 Python 3.9+）
python3.9 -m pip install -r requirements.txt

# 配置 API 密钥（Gemini）
cp env.example .env
# 编辑 .env 添加 GEMINI_API_KEY

# 运行 QMD 翻译模式（推荐）
python3.9 main.py --mode qmd

# 指定源目录和输出目录
python3.9 main.py --mode qmd --source /path/to/vol1/ --output output/qmd_trans/

# 强制重新翻译
python3.9 main.py --mode qmd --force

# 翻译并部署（将译文复制到 output/book/contents/ 覆盖英文原文）
python3.9 main.py --mode qmd --deploy

# 只部署不翻译（已有翻译结果）
python3.9 main.py --deploy

# 运行 HTML 翻译流水线（原有）
python3.9 main.py

# 渲染单个翻译后的 .qmd 为 HTML（需要安装 Quarto）
quarto render output/qmd_trans/introduction/introduction.qmd --to html --no-execute
```

## GitHub Pages 部署

- 远程仓库：`git@github.com:skinterqwe/ML-Systems-Textbook-CN.git`
- 部署地址：https://skinterqwe.github.io/ML-Systems-Textbook-CN/
- CI 工作流：`.github/workflows/deploy-pages.yml`
- 构建方式：CI 中安装 Quarto + TeX Live + Inkscape，在线渲染 `output/book/` 并部署到 GitHub Pages
- **TikZ 渲染**：CI 中通过 LuaLaTeX 编译 TikZ 为 SVG（`diagram.lua` 过滤器），需安装 `texlive-luatex` 包
- **交叉引用修复**：`_quarto.yml` 中配置了 `post-render` hook，每次构建后自动运行 `scripts/fix_cross_references.py` 修复未解析的交叉引用
- **部署流程**：翻译 output/qmd_trans/ → `--deploy` 复制到 output/book/contents/ → `git add -f` + commit + push → CI 自动构建部署

### CI 所需的系统依赖

```
texlive-latex-base texlive-latex-extra texlive-latex-recommended
texlive-fonts-recommended texlive-pictures texlive-luatex
lmodern inkscape
```

### GitHub Pages 配置要点

1. 仓库 Settings → Pages → Source 选择 **GitHub Actions**
2. `output/book/` 源文件（不含 `_build/`）需提交到仓库
3. `.gitignore` 中 `output/` 被忽略，但 `output/book/` 通过反向规则纳入
4. `output/book/_build/` 和 `.quarto/` 在 `output/book/.gitignore` 中排除
5. 修改 `output/book/` 下的文件后，提交时需用 `git add -f` 强制添加（因为 `output/` 在 `.gitignore` 中）

## 架构

`main.py` 是唯一入口，支持 `--mode html/qmd` 切换模式。HTML 模式相关模块（crawler、translator 等）为延迟导入，避免 QMD 模式下缺少 crawl4ai 等依赖。

### QMD 翻译完整流程

```
.qmd 源文件（output/book/contents/）
  → QMDChunker.split() 分块（分离 YAML frontmatter + 按 ## 标题分块）
  → 对每个块执行 QMDTranslator.translate_chunk():
      1. protect_all() — 9 层占位符保护
      2. Gemini API 翻译
      3. restore_all() — while 循环递归恢复占位符
      4. _fix_quarto_newlines() — 修复 ::: 标记粘连（3 轮迭代）
  → QMDChunker.merge() 合并
  → 写出 .qmd 到 output/qmd_trans/
  → 注入 engine: jupyter 到 frontmatter
  → --deploy 时复制到 output/book/contents/ 覆盖英文原文
```

### QMD 模式模块

- `src/qmd_chunker.py` — 按 Markdown 标题（`##`）分块，支持 YAML frontmatter 分离，最大块 60000 字符
- `src/qmd_translator.py` — QMD 翻译核心模块。230+ 条术语表，9 层占位符保护机制，_fix_quarto_newlines 修复 Gemini 翻译后的 ::: 粘连

### HTML 模式模块

- `src/crawler.py` — 使用 crawl4ai 爬取原始 HTML，保存到 `output/origin/`，保持原始目录结构
- `src/translator.py` — 核心翻译模块。提取数学公式用占位符替换保护，通过 Gemini API 翻译后再恢复。包含 80+ 条专业术语对照表
- `src/link_localizer.py` — 将外部链接转换为本地相对路径（支持嵌套目录）
- `src/header_info_adder.py` — 在翻译后 HTML 中插入原文链接和译者信息

### 共用模块

- `src/gemini_api.py` — Gemini API 封装（google-genai SDK，默认 gemini-2.5-pro，支持代理）
- `src/config/settings.py` — 配置管理（路径、爬虫参数、翻译参数、QMD 配置）

### Quarto 构建后处理

- `output/book/scripts/fix_cross_references.py` — Post-render hook，修复 Quarto 未解析的交叉引用（`?@sec-xxx`）
  - 通过 `_quarto.yml` 的 `post-render` 配置自动运行
  - 动态扫描 `_build/html/` 中所有 HTML 文件的 `id="sec-xxx"` 属性，建立 section ID → 文件路径映射（1690+ 个 ID）
  - 支持三种未解析引用模式：`quarto-xref`、`<strong>?@sec-</strong>`、EPUB 的 `@sec-` 链接
  - 硬编码映射（`CHAPTER_MAPPING`）优先于动态映射，确保顶级章节使用正确的标题
  - 章节标题在 `CHAPTER_TITLES` 中定义，不带 "Chapter N:" 前缀（因 `number-sections: false`）

## TikZ 渲染机制

英文原版 Quarto website 使用 `pandoc-ext/diagram` 扩展（`_extensions/pandoc-ext/diagram/diagram.lua`）渲染 TikZ 图表：

1. QMD 中的 `.tikz` 代码块被 diagram.lua 过滤器拦截
2. 用 standalone documentclass 包裹 TikZ 代码，注入 `header-includes` 中的 LaTeX 包
3. 调用 LuaLaTeX 编译为 PDF
4. 通过 Inkscape 将 PDF 转换为 SVG，嵌入 HTML 页面

**关键配置**（`output/book/_quarto.yml`）：
- `diagram.engine.tikz.execpath: lualatex`
- `diagram.engine.tikz.output-format: svg`
- `diagram.engine.tikz.header-includes`：30+ 个 LaTeX 包和自定义颜色定义

**注意事项**：
- `tikzjax.lua` 过滤器会拦截 `.tikz` 代码块导致 diagram.lua 无法处理，已移除
- CI 中必须安装 `texlive-luatex`（包含 `luaotfload` 模块），否则 LuaLaTeX 报错 `module 'luaotfload-main' not found`
- `--no-execute` 不影响 diagram.lua 的 TikZ 编译，仅跳过 Python 代码块执行
- 构建时间约 11 分钟（含 TeX Live 安装和 TikZ 编译）

## QMD 翻译机制要点

### 占位符保护顺序（9 层）

| 顺序 | 元素 | 占位符格式 | 说明 |
|------|------|-----------|------|
| 1 | 代码块（```{python}...```） | `__CODE_PH_N__` | 不翻译 |
| 2 | `\index{...}` 命令 | `__IX_PH_N__` | 保护原文 |
| 3 | Quarto 指令（`:::` 行） | `__QD_PH_N__` | 保护语法 |
| 4 | 块级数学（`$$...$$`） | `__MATH_D_PH_N__` | 行首 $$ 匹配 |
| 5 | 内联数学（`$...$`） | `__MATH_I_PH_N__` | 不跨段落/占位符 |
| 6 | 内联代码（`` `...` ``） | `__IC_PH_N__` | 不翻译 |
| 7 | 跨引用（`@sec-`/`[@...]`） | `__XR_PH_N__` | 不翻译 |
| 8 | LaTeX 命令 | `__LX_PH_N__` | 不翻译 |
| 9 | HTML 注释 | `__CM_PH_N__` | 不翻译 |

### 关键设计决策

- **占位符格式 `__PREFIX_N__`**：使用双下划线包裹，避免短名是长名前缀（如 `IX_PH_1` 是 `IX_PH_11` 的前缀）
- **恢复用 while 循环递归**：循环匹配占位符并替换，直到无占位符残留；恢复前先清理 Gemini 在占位符两侧添加的空格（正则排除 `_`）
- **内联数学不跨占位符**：遇到 `__PREFIX_N__` 格式的占位符时停止匹配，防止 `$` 被错误配对
- **块级数学行级匹配**：`$$` 必须在行首才被认为是公式标记，避免 `$$\times$2` 之类的行内 `$$` 被误匹配
- **`\index{}` 在 `:::` 之前保护**：因为 `\index` 可能出现在 `:::` 的 `fig-cap` 属性中
- **跨引用正则不贪婪到 `__`**：`[\w\-]+?(?=__|...)` 防止跨引用吃掉相邻的占位符名

### 翻译后工作流

1. 执行翻译 → 2. **用 qmd-lint skill 检查** → 3. 修复发现的问题 → 4. `--deploy` 部署

### Gemini 翻译常见问题及修复

- **`_fix_quarto_newlines` 多轮迭代**：3 轮循环修复 Gemini 翻译后的 `:::` 粘连，规则 7 处理闭合 `:::` 后紧跟文本（无换行）的情况
- **`:::` fence div 粘连到内容行**：`:::` 闭合标记可能粘连到图片引用或列表项末尾（如 `\noindent![](img.png):::`），导致 Quarto 无法正确解析 fence div 边界。修复方法：将 `:::` 移至新行
- **TikZ 代码块结束符粘连**：Gemini 翻译后，TikZ 代码块的 ` ``` ` 结束标记可能与后续描述文字合并到同一行（如 `` ```**描述文字**``），导致 Pandoc 无法识别代码块结束。修复方法：将 ` ``` ` 恢复到独立行
- **TikZ 代码块内的 LaTeX 语法完整性**：修复粘连问题时需注意代码块内 `\scalebox{}{}` 等命令的闭合括号 `}` 不能误删，否则 LuaLaTeX 编译失败导致 diagram.lua 无声地放弃渲染
- **Callout 内裸代码块**：`::: {.callout-example}` 内的 ` ``` ` 无语言标记会导致 Quarto 把后续 `:::` 当作代码块内容。需改为缩进代码块（4 空格）或加 `{.text}` 标记

## 目标网站

- 来源：https://mlsysbook.ai/book/（Quarto 生成，MathJax 3 公式）
- QMD 源文件：33 个 .qmd 文件，约 72,500 行（Vol 1）
- 英文原版 Quarto website 源文件位于 `output/book/`
- 共 27 个页面，分为 Frontmatter、Systems Foundations、Design Principles、Performance Engineering、Robust Deployment、Trustworthy Systems、Frontiers、Backmatter 八个部分

## 技术栈

Python 3.9+，Google Gemini API（google-genai），Quarto，BeautifulSoup4，Pydantic，crawl4ai，playwright
