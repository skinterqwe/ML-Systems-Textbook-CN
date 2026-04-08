"""
页头信息添加模块
在翻译后的HTML文件页头添加原文链接和翻译者信息

项目：ML Systems Textbook 中文翻译
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag

from config.settings import TRANS_DIR


class HeaderInfoAdder:
    """在翻译后的网页头部添加原文链接和翻译者信息"""

    def __init__(self, trans_dir: str = None, urls_config: str = None):
        """
        初始化页头信息添加器

        Args:
            trans_dir (str): 翻译后文件目录，默认使用配置中的TRANS_DIR
            urls_config (str): URL配置文件路径，默认使用config/urls.txt
        """
        self.logger = logging.getLogger(__name__)

        # 设置目录路径
        self.trans_dir = Path(trans_dir) if trans_dir else Path(TRANS_DIR)
        self.urls_config = urls_config or "src/config/urls.txt"

        # 验证目录存在
        if not self.trans_dir.exists():
            raise FileNotFoundError(f"翻译目录不存在: {self.trans_dir}")

        # 文件相对路径到原始URL的映射字典
        self.file_url_mapping: Dict[str, str] = {}

        # 统计信息
        self.stats = {
            'files_processed': 0,
            'files_modified': 0,
            'headers_added': 0,
            'files_skipped': 0
        }

        # 翻译者信息
        self.translator_name = "北极的树"
        self.wechat_qr_url = "https://wechat-account-1251781786.cos.ap-guangzhou.myqcloud.com/wechat_account.jpeg"

        self.logger.info(f"页头信息添加器初始化完成，目标目录: {self.trans_dir}")

    def build_file_url_mapping(self) -> Dict[str, str]:
        """
        构建文件相对路径到原始URL的映射关系

        Returns:
            Dict[str, str]: 文件路径映射字典
        """
        try:
            self.file_url_mapping.clear()

            # 获取实际存在的HTML文件（递归）
            existing_files = set()
            for html_file in self.trans_dir.glob("**/*.html"):
                rel_path = str(html_file.relative_to(self.trans_dir))
                existing_files.add(rel_path)

            self.logger.info(f"找到 {len(existing_files)} 个现有HTML文件")

            # 读取URL配置文件
            urls_file = Path(self.urls_config)
            if urls_file.exists():
                with open(urls_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过注释和空行
                        if not line or line.startswith('#'):
                            continue

                        # 解析URL并生成本地相对路径
                        local_path = self._url_to_relative_path(line)

                        # 只映射实际存在的文件
                        if local_path in existing_files:
                            self.file_url_mapping[local_path] = line

            self.logger.info(f"构建了 {len(self.file_url_mapping)} 个文件URL映射")
            for filepath, url in sorted(self.file_url_mapping.items()):
                self.logger.debug(f"  {filepath} -> {url}")

            return self.file_url_mapping

        except Exception as e:
            self.logger.error(f"构建文件URL映射失败: {str(e)}")
            return {}

    def _url_to_relative_path(self, url: str) -> str:
        """
        将URL转换为本地相对路径（保持嵌套目录结构）

        Args:
            url (str): 原始URL

        Returns:
            str: 本地相对路径
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')

            # 移除 'book/' 前缀
            if path.startswith('book/'):
                path = path[5:]

            if not path:
                return 'index.html'

            # 确保有.html扩展名
            if not path.endswith('.html'):
                path += '.html'

            return path

        except Exception as e:
            self.logger.warning(f"URL转路径失败 {url}: {str(e)}")
            return "unknown.html"

    def create_header_html(self, original_url: str) -> str:
        """
        生成页头信息的HTML内容

        Args:
            original_url (str): 原始文章URL

        Returns:
            str: 生成的HTML字符串
        """
        header_html = f'''
        <div class="translation-info base-grid" style="margin-bottom: 20px;">
            <div style="grid-column: text;
                       display: flex;
                       align-items: center;
                       justify-content: space-between;
                       padding: 16px 0;
                       border-bottom: 1px solid var(--global-text-color-light, rgba(0,0,0,0.15));
                       font-size: 16px;
                       line-height: 1.5;
                       color: var(--global-text-color, currentColor);">
                <div style="display: flex;
                           flex-direction: column;
                           gap: 8px;">
                    <div>
                        <span style="font-weight: 600; color: var(--global-text-color, currentColor);">🔗 英文原文：</span>
                        <a href="{original_url}"
                           target="_blank"
                           rel="noopener noreferrer"
                           style="color: var(--global-theme-color, #004276);
                                  text-decoration: none;
                                  margin-left: 4px;"
                           onmouseover="this.style.textDecoration='underline'"
                           onmouseout="this.style.textDecoration='none'">
                           {original_url}
                        </a>
                    </div>
                    <div>
                        <span style="font-weight: 600; color: var(--global-text-color, currentColor);">✍️ 翻译：</span>
                        <span style="margin-left: 4px; color: var(--global-text-color, currentColor);">{self.translator_name}</span>
                    </div>
                </div>
                <div style="flex-shrink: 0;
                           display: flex;
                           flex-direction: column;
                           align-items: center;
                           gap: 6px;
                           margin-left: 20px;">
                    <img src="{self.wechat_qr_url}"
                         alt="微信二维码"
                         style="width: 80px;
                                height: 80px;
                                border-radius: 6px;
                                opacity: 0.9;"
                         loading="lazy">
                    <span style="font-size: 12px;
                                 color: var(--global-text-color-light, currentColor);
                                 opacity: 0.8;
                                 text-align: center;">
                        微信公众号
                    </span>
                </div>
            </div>
        </div>'''

        return header_html.strip()

    def find_insertion_point(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        找到合适的插入位置

        Args:
            soup (BeautifulSoup): 解析后的HTML文档

        Returns:
            Optional[Tag]: 插入位置的标签，如果找不到则返回None
        """
        try:
            # 查找 <div class="post distill"> 标签
            post_distill = soup.find('div', class_='post distill')
            if post_distill:
                self.logger.debug("找到插入点: <div class='post distill'>")
                return post_distill

            # 备选方案：查找包含 "post" 和 "distill" 类的div
            post_div = soup.find('div', class_=lambda x: x and 'post' in x and 'distill' in x)
            if post_div:
                self.logger.debug("找到备选插入点: div with 'post' and 'distill' classes")
                return post_div

            # Quarto 生成的页面：查找 main 或 article 标签
            main_tag = soup.find('main')
            if main_tag:
                self.logger.debug("找到插入点: <main>")
                return main_tag

            article_tag = soup.find('article')
            if article_tag:
                self.logger.debug("找到插入点: <article>")
                return article_tag

            # 最后备选：查找 d-title 标签的父容器
            d_title = soup.find('d-title')
            if d_title and d_title.parent:
                self.logger.debug("找到备选插入点: d-title的父容器")
                return d_title.parent

            # 查找 body 直接作为插入点
            body_tag = soup.find('body')
            if body_tag:
                self.logger.debug("找到插入点: <body>")
                return body_tag

            self.logger.warning("未找到合适的插入点")
            return None

        except Exception as e:
            self.logger.error(f"查找插入点失败: {str(e)}")
            return None

    def process_html_file(self, file_path: Path) -> bool:
        """
        处理单个HTML文件

        Args:
            file_path (Path): HTML文件路径

        Returns:
            bool: 处理是否成功
        """
        try:
            rel_path = file_path.relative_to(self.trans_dir)
            self.logger.info(f"处理文件: {rel_path}")

            # 检查是否有对应的原始URL
            rel_path_str = str(rel_path)
            if rel_path_str not in self.file_url_mapping:
                self.logger.warning(f"未找到文件 {rel_path} 的原始URL映射，跳过处理")
                self.stats['files_skipped'] += 1
                return True

            original_url = self.file_url_mapping[rel_path_str]

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 检查是否已经添加过页头信息
            if 'translation-info' in html_content:
                self.logger.info(f"⏭️  {rel_path}: 已包含页头信息，跳过处理")
                self.stats['files_skipped'] += 1
                return True

            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 查找插入点
            insertion_point = self.find_insertion_point(soup)
            if not insertion_point:
                self.logger.error(f"未找到 {rel_path} 的插入点")
                self.stats['files_skipped'] += 1
                return False

            # 生成页头信息HTML
            header_html = self.create_header_html(original_url)
            header_soup = BeautifulSoup(header_html, 'html.parser')

            # 插入页头信息（在容器的开头）
            if insertion_point.contents:
                insertion_point.insert(0, header_soup)
            else:
                insertion_point.append(header_soup)

            # 保存修改后的HTML
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            self.stats['files_processed'] += 1
            self.stats['files_modified'] += 1
            self.stats['headers_added'] += 1

            self.logger.info(f"✅ {rel_path}: 成功添加页头信息")
            return True

        except Exception as e:
            self.logger.error(f"处理文件失败 {file_path}: {str(e)}")
            return False

    def process_all_files(self) -> Dict[str, int]:
        """
        批量处理所有HTML文件

        Returns:
            Dict[str, int]: 处理统计信息
        """
        try:
            self.logger.info("开始批量添加页头信息...")

            # 重置统计信息
            self.stats = {
                'files_processed': 0,
                'files_modified': 0,
                'headers_added': 0,
                'files_skipped': 0
            }

            # 构建文件URL映射
            if not self.build_file_url_mapping():
                self.logger.error("无法构建文件URL映射，停止处理")
                return self.stats

            # 获取所有HTML文件（递归）
            html_files = list(self.trans_dir.glob("**/*.html"))
            if not html_files:
                self.logger.warning("未找到HTML文件")
                return self.stats

            self.logger.info(f"找到 {len(html_files)} 个HTML文件")

            # 处理每个文件
            success_count = 0
            for html_file in html_files:
                if self.process_html_file(html_file):
                    success_count += 1

            # 打印统计结果
            self.logger.info("=" * 50)
            self.logger.info("批量处理完成统计:")
            self.logger.info(f"  📁 总文件数: {len(html_files)}")
            self.logger.info(f"  ✅ 成功处理: {success_count}")
            self.logger.info(f"  📝 修改文件: {self.stats['files_modified']}")
            self.logger.info(f"  🏷️  添加页头: {self.stats['headers_added']}")
            self.logger.info(f"  ⏭️  跳过文件: {self.stats['files_skipped']}")
            self.logger.info("=" * 50)

            return self.stats

        except Exception as e:
            self.logger.error(f"批量处理失败: {str(e)}")
            return self.stats

    def get_stats(self) -> Dict[str, int]:
        """获取处理统计信息"""
        return self.stats.copy()


# 便捷函数
def add_headers_to_all_files(trans_dir: str = None) -> Dict[str, int]:
    """
    便捷函数：为所有HTML文件添加页头信息

    Args:
        trans_dir (str): 翻译文件目录，默认使用配置

    Returns:
        Dict[str, int]: 处理统计信息
    """
    adder = HeaderInfoAdder(trans_dir)
    return adder.process_all_files()


def add_header_to_single_file(file_path: str, trans_dir: str = None) -> bool:
    """
    便捷函数：为单个文件添加页头信息

    Args:
        file_path (str): HTML文件路径
        trans_dir (str): 翻译文件目录

    Returns:
        bool: 处理是否成功
    """
    adder = HeaderInfoAdder(trans_dir)
    adder.build_file_url_mapping()
    return adder.process_html_file(Path(file_path))


async def main():
    """主函数"""
    from config.logging_config import setup_logging

    setup_logging('INFO')

    print("页头信息添加工具")
    print("=" * 50)

    try:
        adder = HeaderInfoAdder()
        print("🔄 开始为所有HTML文件添加页头信息...")
        stats = adder.process_all_files()

        print("\n" + "=" * 60)
        print("🎉 批量页头信息添加完成！")
        print("=" * 60)
        print(f"📁 总文件数量: {stats['files_processed'] + stats['files_skipped']}")
        print(f"✅ 成功处理: {stats['files_processed']}")
        print(f"📝 修改文件数: {stats['files_modified']}")
        print(f"🏷️  添加页头数: {stats['headers_added']}")
        print(f"⏭️  跳过文件数: {stats['files_skipped']}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 批量处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n完成!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
