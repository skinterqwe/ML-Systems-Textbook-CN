# ML Systems Textbook 中文翻译

[ML Systems Textbook](https://mlsysbook.ai/book/)（机器学习系统教科书）的中文翻译项目。

**在线阅读**：[https://skinterqwe.github.io/ML-Systems-Textbook-CN/](https://skinterqwe.github.io/ML-Systems-Textbook-CN/)

## 项目简介

本项目将 ML Systems Textbook 从英文翻译为中文。这是一本涵盖机器学习系统全栈的技术教科书，共 27 个章节页面，分为 6 大部分：

- **系统基础**：机器学习导论、ML 系统概述、深度学习基础、DNN 架构
- **设计原则**：AI 工作流、数据工程、AI 框架、AI 训练
- **性能工程**：高效 AI、模型优化、硬件加速、基准测试
- **鲁棒部署**：MLOps、端侧学习、隐私安全、鲁棒 AI
- **可信系统**：负责任 AI、可持续 AI、AI for Good
- **机器学习系统前沿**：AGI 系统、总结

## 翻译状态

- **已翻译**：全部 27 个章节页面 + 术语表 + 前言/致谢等
- **翻译方式**：Gemini API（gemini-3-pro-preview）+ 手动补全
- **质量保障**：自动化语法检查 + 翻译遗漏扫描 + Grid Table 转 Pipe Table

## 使用方法

```bash
# 安装依赖（需要 Python 3.9+）
python3.9 -m pip install -r requirements.txt

# 配置 Gemini API 密钥
cp env.example .env
# 编辑 .env 填入 GEMINI_API_KEY

# 翻译单个文件（推荐）
python3.9 main.py --mode qmd --file output/book/contents/core/introduction/introduction.qmd

# 翻译全部文件
python3.9 main.py --mode qmd

# 强制重新翻译
python3.9 main.py --mode qmd --force

# 部署（将译文复制到 output/book/contents/ 覆盖英文原文）
python3.9 main.py --deploy

# 翻译并部署
python3.9 main.py --mode qmd --deploy
```

## 翻译流水线（QMD 模式）

```
.qmd 源文件（output/book/contents/）
  → QMDChunker.split() 分块（按 ## 标题）
  → QMDTranslator.translate_chunk():
      1. protect_all() — 9 层占位符保护（代码块、数学公式、交叉引用等）
      2. Gemini API 翻译
      3. restore_all() — while 循环递归恢复占位符
      4. _fix_quarto_newlines() — 修复 Quarto 标记粘连
  → 合并写出 → --deploy 复制到 output/book/contents/
  → git commit → push → GitHub Actions 自动构建部署
```

## 目录结构

```
ML-Systems-Textbook-CN/
├── main.py                      # 主入口（支持 --mode qmd/html）
├── src/
│   ├── qmd_translator.py        # QMD 翻译核心（9 层占位符保护、230+ 术语表）
│   ├── qmd_chunker.py           # QMD 分块器（按 ## 标题分块）
│   ├── gemini_api.py            # Gemini API 封装
│   └── config/settings.py       # 配置管理
├── scripts/
│   ├── check_translation_syntax.py  # 翻译语法检查
│   ├── run_checks.sh                # 全量检查脚本
│   └── fix_cross_references.py      # 交叉引用修复（CI post-render hook）
├── output/
│   ├── book/                    # Quarto website 源文件（英文+中文 .qmd）
│   │   ├── _quarto.yml          # Quarto 配置（导航、分册、构建选项）
│   │   ├── contents/            # 章节 .qmd 文件（已翻译为中文）
│   │   └── scripts/             # 构建脚本
│   └── qmd_trans/               # 翻译中间输出
├── .github/workflows/deploy-pages.yml  # CI 构建部署
├── requirements.txt
├── CLAUDE.md                    # Claude Code 项目指南
└── README.md
```

## 部署

- **远程仓库**：`git@github.com:skinterqwe/ML-Systems-Textbook-CN.git`
- **部署地址**：https://skinterqwe.github.io/ML-Systems-Textbook-CN/
- **CI 构建**：GitHub Actions 安装 Quarto + TeX Live + Inkscape，渲染 `output/book/` 并部署到 GitHub Pages
- **TikZ 渲染**：CI 中通过 LuaLaTeX 编译 TikZ 图表为 SVG（diagram.lua 过滤器）

## 技术栈

- Python 3.9+
- Google Gemini API（gemini-3-pro-preview）— 翻译引擎
- Quarto — 网站构建（含 diagram.lua TikZ 渲染）
- GitHub Actions — CI/CD 自动构建部署

## 许可证

本翻译项目仅用于学习交流，原书版权归原作者所有。
