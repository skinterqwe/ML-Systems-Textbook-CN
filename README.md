# ML Systems Textbook 中文翻译

[ML Systems Textbook](https://mlsysbook.ai/book/) 的中文翻译项目。

## 项目简介

本项目将 ML Systems Textbook（一本涵盖机器学习系统全栈的技术教科书）从英文翻译为中文，覆盖从基础概念到前沿部署的完整内容。

翻译范围包括 27 个章节页面，涵盖：
- **Systems Foundations**：深度学习基础、DNN 架构
- **Design Principles**：工作流、数据工程、框架、训练
- **Performance Engineering**：高效 AI、优化、硬件加速、基准测试
- **Robust Deployment**：MLOps、端侧学习、隐私安全、鲁棒 AI
- **Trustworthy Systems**：负责任 AI、可持续 AI、AI for Good
- **Frontiers**：前沿方向、总结

## 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 Gemini API 密钥
cp env.example .env
# 编辑 .env 文件，填入 GEMINI_API_KEY

# 运行翻译流水线
python main.py
```

## 流水线步骤

1. **爬取** — 使用 crawl4ai 爬取原始 HTML 页面
2. **翻译** — 通过 Gemini API 翻译为中文，保护数学公式和代码
3. **链接本地化** — 将绝对链接转换为本地相对链接
4. **页头添加** — 在页面顶部添加原文链接和译者信息

## 目录结构

```
ML-Systems-Textbook-CN/
├── main.py              # 主入口
├── src/
│   ├── crawler.py       # 网页爬取
│   ├── translator.py    # HTML 翻译（Gemini API）
│   ├── link_localizer.py    # 链接本地化
│   ├── header_info_adder.py # 页头信息添加
│   ├── gemini_api.py    # Gemini API 封装
│   └── config/
│       ├── settings.py  # 配置管理
│       └── urls.txt     # URL 列表（27 页）
├── output/
│   ├── origin/          # 原始 HTML
│   └── trans/           # 翻译后 HTML
└── requirements.txt
```

## 技术栈

- Python 3.8+
- crawl4ai — 网页爬取
- Google Gemini API — 翻译
- BeautifulSoup4 — HTML 解析
- Pydantic — 结构化输出
- playwright — 浏览器自动化

## 许可证

本翻译项目仅用于学习交流，原书版权归原作者所有。
