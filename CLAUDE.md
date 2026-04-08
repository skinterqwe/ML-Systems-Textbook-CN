# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ML Systems Textbook（https://mlsysbook.ai/book/）技术教科书的中文翻译项目。使用 Python 异步流水线完成：爬取原始 HTML → Gemini API 翻译 → 链接本地化 → 页头信息添加。翻译后的 HTML 文件部署在 `output/trans/` 目录。

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥（Gemini）
cp env.example .env
# 编辑 .env 添加 GEMINI_API_KEY

# 运行完整翻译流水线
python main.py
```

流水线按顺序执行四步：爬取 → 翻译 → 链接本地化 → 页头添加，支持增量更新（已翻译文件自动跳过）。

## 架构

`main.py` 是唯一入口，定义 `TranslationPipeline` 类，按顺序编排四个步骤，各步骤对应 `src/` 下的独立模块：

- `src/crawler.py` — 使用 crawl4ai 爬取原始 HTML，保存到 `output/origin/`，保持原始目录结构
- `src/translator.py` — 核心翻译模块。提取数学公式（`span.math` 或 `mjx-container`）用占位符替换保护，通过 Gemini API 翻译后再恢复。包含 80+ 条专业术语对照表（`self.terminology`）
- `src/link_localizer.py` — 将外部链接转换为本地相对路径（支持嵌套目录）
- `src/header_info_adder.py` — 在翻译后 HTML 中插入原文链接和译者信息
- `src/gemini_api.py` — Gemini API 封装
- `src/config/settings.py` — 配置管理（路径、爬虫参数、翻译参数）
- `src/config/urls.txt` — 待翻译的 URL 列表（27 个页面）

输出目录：`output/origin/`（原始 HTML，保持嵌套目录结构）、`output/trans/`（翻译后 HTML，同样保持嵌套目录结构）。

## 翻译机制要点

- 数学公式保护：Quarto 页面使用 `span.math` 标签，提取为 `MATH_PLACEHOLDER_NNN` 占位符，翻译后恢复
- 结构化翻译：元数据（标题、描述）和正文分别翻译，使用 Pydantic 模型约束 Gemini 输出格式
- 术语一致性：`translator.py` 中的 `terminology` 字典确保专业术语统一翻译（80+ 条目）
- 嵌套目录结构：URL 路径映射到本地保持目录层级，如 `contents/core/dl_primer/dl_primer.html`

## 目标网站

- 来源：https://mlsysbook.ai/book/（Quarto 生成，MathJax 3 公式）
- 共 27 个页面，分为 Frontmatter、Systems Foundations、Design Principles、Performance Engineering、Robust Deployment、Trustworthy Systems、Frontiers、Backmatter 八个部分

## 技术栈

Python 3.8+，crawl4ai，Google Gemini API（google-genai），BeautifulSoup4，Pydantic，playwright，aiohttp
