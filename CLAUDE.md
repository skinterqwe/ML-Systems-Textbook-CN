# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ML Systems Textbook（https://mlsysbook.ai/book/）技术教科书的中文翻译项目。支持两种翻译模式：

- **QMD 模式**（主用）：读取本地 .qmd → 保护特殊元素 → Gemini 翻译 → 恢复 → Quarto 渲染 HTML
- **HTML 模式**（历史保留）：爬取原始 HTML → Gemini API 翻译 → 链接本地化 → 页头信息添加

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

# 强制重新翻译
python3.9 main.py --mode qmd --force

# 翻译并部署（将译文复制到 output/book/contents/ 覆盖英文原文）
python3.9 main.py --mode qmd --deploy

# 只部署不翻译（已有翻译结果）
python3.9 main.py --deploy

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

### QMD 翻译流程

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

### HTML 模式模块（历史保留）

- `src/crawler.py` — 使用 crawl4ai 爬取原始 HTML，保存到 `output/origin/`
- `src/translator.py` — 核心翻译模块。提取数学公式用占位符替换保护，通过 Gemini API 翻译后再恢复
- `src/link_localizer.py` — 将外部链接转换为本地相对路径
- `src/header_info_adder.py` — 在翻译后 HTML 中插入原文链接和译者信息

### 共用模块

- `src/gemini_api.py` — Gemini API 封装（google-genai SDK，默认 gemini-2.5-pro，支持代理）
- `src/config/settings.py` — 配置管理（路径、爬虫参数、翻译参数、QMD 配置）

### Quarto 构建后处理

- `output/book/scripts/fix_cross_references.py` — Post-render hook，修复 Quarto 渲染后 HTML 中未解析的交叉引用（`?@sec-xxx`）
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

## QMD 翻译机制与常见问题

### 占位符保护机制

**保护顺序（9 层）**：

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

**关键设计决策**：

- **占位符格式 `__PREFIX_N__`**：双下划线包裹，避免短名是长名前缀（如 `IX_PH_1` 是 `IX_PH_11` 的前缀）
- **恢复用 while 循环递归**：循环匹配占位符并替换，直到无占位符残留；恢复前先清理 Gemini 在占位符两侧添加的空格（正则排除 `_`）
- **内联数学不跨占位符**：遇到 `__PREFIX_N__` 格式的占位符时停止匹配，防止 `$` 被错误配对
- **块级数学行级匹配**：`$$` 必须在行首才被认为是公式标记，避免 `$$\times$2` 之类的行内 `$$` 被误匹配
- **`\index{}` 在 `:::` 之前保护**：因为 `\index` 可能出现在 `:::` 的 `fig-cap` 属性中
- **跨引用正则不贪婪到 `__`**：`[\w\-]+?(?=__|...)` 防止跨引用吃掉相邻的占位符名

### 翻译后检查机制

**第一层：自动化检查**（翻译后必做）
```bash
# 运行全部检查（翻译语法 + 重复标签 + 引用完整性 + 脚注 + 列表格式）
./scripts/run_checks.sh output/book/contents

# 单独检查翻译语法（交叉引用粘连、fence div 配对、shortcode 误包裹等）
python3 scripts/check_translation_syntax.py -d output/book/contents/ --strict
python3 scripts/check_translation_syntax.py -f output/book/contents/core/dl_primer/dl_primer.qmd
```

| 检查 | 脚本 | 说明 |
|------|------|------|
| 翻译语法（5 项） | `scripts/check_translation_syntax.py` | 交叉引用粘连、fence div 配对、shortcode 误包裹、`:::` 粘连、TikZ 结束符粘连 |
| 重复标签 | `scripts/content/check_duplicate_labels.py` | `{#fig-xxx}` 等标签重复定义 |
| 引用完整性 | `scripts/content/validate_citations.py` | `@key` 引用在 .bib 中是否存在 |
| 脚注检查 | `scripts/content/footnote_cleanup.py` | 未定义引用、未使用的定义 |
| 列表格式 | `scripts/utilities/check_list_formatting.py` | 冒号后列表缺空行 |

**翻译遗漏检测**（`check_translation_syntax.py` 不检查语言，需额外扫描）：
- **模式 A（整节未翻译）**：整个 chunk 保留英文。排除 TikZ/HTML 注释后扫描含 >5 个英文单词的行。
- **模式 B（chunk 内选择性跳过）**：`###`/`####` 标题和紧跟段落保持英文，但深层内容被翻译。需扫描英文标题行和以英文开头的非代码行。
- **模式 C（单句未翻译）**：散布在已翻译段落中，需逐段检查或部署页面验证。

**第二层：手动 qmd-lint skill**（详细检查工具）

**翻译后工作流**：1. 执行翻译 → 2. **自动检查**（`scripts/run_checks.sh`） → 3. 修复发现的问题 → 4. `--deploy` 部署 → 5. CI 构建后验证部署页面

### Gemini 翻译常见问题及修复

**`:::` 相关**：
- **`_fix_quarto_newlines` 多轮迭代**：3 轮循环修复 Gemini 翻译后的 `:::` 粘连，规则 7 处理闭合 `:::` 后紧跟文本（无换行）的情况
- **`:::` fence div 粘连到内容行**：`:::` 闭合标记可能粘连到图片引用或列表项末尾（如 `\noindent![](img.png):::`），导致 Quarto 无法正确解析 fence div 边界。修复方法：将 `:::` 移至新行
- **Fence div 未闭合**：Gemini 可能吞掉 `:::` 闭合标记，导致 fence div 配对失败。检查方法：用栈模拟解析，统计未闭合的 `:::` 块
- **Shortcode 误包裹在 `:::` 中**：`{{< margin-video >}}` 等 Quarto shortcode 是行内指令，不应放在 `:::` fence div 内。Gemini 可能错误地给 shortcode 加上 `:::` 前缀
- **Callout 内裸代码块**：`::: {.callout-example}` 内的 ` ``` ` 无语言标记会导致 Quarto 把后续 `:::` 当作代码块内容。需改为缩进代码块（4 空格）或加 `{.text}` 标记

**TikZ 相关**：
- **TikZ 代码块结束符粘连**：Gemini 翻译后，TikZ 代码块的 ` ``` ` 结束标记可能与后续描述文字合并到同一行（如 `` ```**描述文字**``），导致 Pandoc 无法识别代码块结束。修复方法：将 ` ``` ` 恢复到独立行
- **TikZ 代码块内的 LaTeX 语法完整性**：修复粘连问题时需注意代码块内 `\scalebox{}{}` 等命令的闭合括号 `}` 不能误删，否则 LuaLaTeX 编译失败导致 diagram.lua 无声地放弃渲染

**交叉引用与标题**：
- **交叉引用粘连中文**：`@fig-xxx` 后直接跟中文（如 `@fig-xxx展示了`），导致 Quarto 交叉引用解析器失败，页面报 `innerHTML` 错误。翻译后 .qmd 阶段修复正则：
  ```python
  # @sec-xxx中文 → @sec-xxx 中文（注意用 [a-zA-Z0-9_-]，不用 \w，因 Python 3 的 \w 匹配 CJK 字符）
  re.sub(r'(@(?:sec|fig|tbl|eq|lst)-)([a-zA-Z0-9_-]+)([\u4e00-\u9fff])',
         lambda m: f'{m.group(1)}{m.group(2)} {m.group(3)}', content)
  # [@xxx]中文 → [@xxx] 中文
  re.sub(r'(\[@[a-zA-Z0-9_-]+\])([\u4e00-\u9fff])',
         lambda m: f'{m.group(1)} {m.group(3)}', content)
  ```
  注：`fix_cross_references.py` 是构建后处理（修复 HTML），上述正则是翻译后修复（修复 .qmd），两者是不同阶段的操作。
- **标题与正文粘连**：`{#sec-...}` 后直接跟 `@tbl-...` 引用或正文（如 `### 标题 {#sec-xxx}@tbl-yyy 展示了...`），Quarto 无法正确解析标题。必须确保标题行以 `{#sec-...}` 结尾，后续内容换行

**表格**：
- **Grid Table 统一改为 Pipe Table**：Gemini 翻译后的所有 Grid Table（`+---+` 格式）都应改为 Pipe Table（`| col1 | col2 |` + `|:---|:---|`）。不仅中文——英文 Grid Table 含 `$` 数学公式也会因 Pandoc 宽度计算错误导致 `colspan` 合并列、表头与内容错位
- **表格标题粘连正文**：`{#tbl-xxx}@tbl-xxx 强调了...` — 表格标题 `: **标题** {#tbl-xxx}` 后直接跟正文段落，Quarto 将 `@tbl-xxx` 视为标题的一部分无法解析。需拆分为标题独立行 + 空行 + 正文段落

**批量 regex 副作用**：
- TikZ 结束符修复 `re.sub(r'```(\*\*)', ...)` 也会匹配 ` ```{.python} ` 中的 `{` 前面的反引号组，导致代码块属性被拆开（` ```\n{.python} `）。修复后必须扫描 ` ```\n{. ` 模式并回滚：`re.sub(r'```\n(\{[^}]+\})', r'```\1', content)`

## 目标网站

- 来源：https://mlsysbook.ai/book/（Quarto 生成，MathJax 3 公式）
- QMD 源文件：33 个 .qmd 文件，约 72,500 行（Vol 1）
- 英文原版 Quarto website 源文件位于 `output/book/`
- 共 27 个页面，分为前言、系统基础、设计原则、性能工程、鲁棒部署、可信系统、前沿、附录八个部分
- **翻译状态**：全部 27 个章节已翻译完成（截至 2026-04-24）

### 已翻译章节清单

| 分册 | 章节 | 翻译方式 |
|:---|:---|:---|
| 前言 | foreword、about、acknowledgements、socratiq | 标题手动翻译 |
| 系统基础 | introduction、ml_systems、dl_primer、dnn_architectures | Gemini API |
| 设计原则 | workflow、data_engineering、frameworks、training | Gemini API |
| 性能工程 | efficient_ai、optimizations、hw_acceleration、benchmarking | Gemini API |
| 鲁棒部署 | ops、ondevice_learning、privacy_security、robust_ai | Gemini API + 手动补全 |
| 可信系统 | responsible_ai、sustainable_ai、ai_for_good | Gemini API + 手动补全 |
| 前沿 | frontiers(AGI)、conclusion | Gemini API |
| 附录 | glossary、references、phd_survival_guide | Gemini API（术语名不翻译） |

### Gemini 翻译模型

- **当前模型**：`gemini-3-pro-preview`（通过代理访问）
- 配置方式：`GEMINI_MODEL_NAME=gemini-3-pro-preview` 环境变量
- 旧模型 `gemini-2.5-pro` 返回 `SETTLEMENT_PRICING_NOT_FOUND` 错误，已弃用
- 代理地址在 `src/gemini_api.py` 中配置

### 翻译后批量修复脚本

翻译完成后需运行批量修复，处理 Gemini 系统性问题：

```python
# 1. 交叉引用/脚注/引文粘连中文
content = re.sub(r'([\u4e00-\u9fff])(@(?:sec|fig|tbl|eq|lst)-)', r'\1 \2', content)
content = re.sub(r'(@(?:sec|fig|tbl|eq|lst)-[a-zA-Z0-9_-]+)([\u4e00-\u9fff])', r'\1 \2', content)
content = re.sub(r'(\[@[a-zA-Z0-9_-]+\])([\u4e00-\u9fff])', lambda m: f'{m.group(1)} {m.group(2)}', content)
content = re.sub(r'(\[\^[a-zA-Z0-9_-]+\])([\u4e00-\u9fff])', lambda m: f'{m.group(1)} {m.group(2)}', content)

# 2. TikZ 结束符粘连
content = re.sub(r'```(\*\*)', r'```\n\n\1', content)
content = re.sub(r'```([^{*\s])', r'```\n\n\1', content)
content = re.sub(r'```\n(\{[^}]+\})', r'```\1', content)  # rollback

# 3. ::: 闭合粘连文本
content = re.sub(r':::([^\s{])', r':::\n\n\1', content)

# 4. Python 代码块语言标记被拆开
content = re.sub(r'```\n\npython\n', '```python\n', content)
```

## 技术栈

Python 3.9+，Google Gemini API（gemini-3-pro-preview），Quarto（含 diagram.lua TikZ 渲染）
