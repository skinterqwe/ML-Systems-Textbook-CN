"""
链接本地化模块
将HTML文件中的绝对链接转换为本地相对链接

项目：ML Systems Textbook 中文翻译
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from config.settings import TRANS_DIR


class LinkLocalizer:
    """将HTML文件中的绝对链接转换为本地相对链接"""

    def __init__(self, trans_dir: str = None, urls_config: str = None):
        """
        初始化链接本地化器

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

        # URL映射字典：绝对URL -> 本地相对路径
        self.url_mapping: Dict[str, str] = {}

        # 统计信息
        self.stats = {
            'files_processed': 0,
            'files_modified': 0,
            'links_converted': 0,
            'links_skipped': 0
        }

        # 基础域名模式
        self.base_domain = "https://mlsysbook.ai/book"

        self.logger.info(f"链接本地化器初始化完成，目标目录: {self.trans_dir}")

    def build_url_mapping(self) -> Dict[str, str]:
        """
        构建URL到本地文件的映射关系

        Returns:
            Dict[str, str]: URL映射字典
        """
        try:
            self.url_mapping.clear()

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
                            self.url_mapping[line] = local_path
                            # 同时处理带尾部斜杠的版本
                            if line.endswith('/'):
                                self.url_mapping[line.rstrip('/')] = local_path
                            else:
                                self.url_mapping[line + '/'] = local_path

            self.logger.info(f"构建了 {len(self.url_mapping)} 个URL映射")
            for url, path in sorted(self.url_mapping.items()):
                self.logger.debug(f"  {url} -> {path}")

            return self.url_mapping

        except Exception as e:
            self.logger.error(f"构建URL映射失败: {str(e)}")
            return {}

    def _url_to_relative_path(self, url: str) -> str:
        """
        将URL转换为本地相对路径（保持嵌套目录结构）

        Args:
            url (str): 原始URL

        Returns:
            str: 本地相对路径，如 contents/core/dl_primer/dl_primer.html
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

    def _is_local_link(self, url: str) -> bool:
        """
        判断是否为需要本地化的链接

        Args:
            url (str): 要检查的URL

        Returns:
            bool: 是否为本地链接
        """
        if not url:
            return False

        # 跳过锚点链接
        if url.startswith('#'):
            return False

        # 跳过其他协议
        if url.startswith(('mailto:', 'tel:', 'javascript:')):
            return False

        # 检查是否为目标域名的链接
        return url.startswith(self.base_domain)

    def _convert_links_in_html(self, html_content: str, current_file_path: Path = None) -> Tuple[str, int]:
        """
        转换HTML内容中的链接，计算正确的相对路径

        Args:
            html_content (str): 原始HTML内容
            current_file_path (Path): 当前文件路径（用于计算相对路径）

        Returns:
            Tuple[str, int]: (转换后的HTML内容, 转换的链接数量)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            converted_count = 0

            # 查找所有带href属性的标签
            for tag in soup.find_all(attrs={'href': True}):
                href = tag.get('href')

                if self._is_local_link(href):
                    # 规范化URL（移除尾部斜杠进行匹配）
                    normalized_url = href.rstrip('/')

                    # 检查是否有对应的本地文件
                    target_path = None
                    if href in self.url_mapping:
                        target_path = self.url_mapping[href]
                    elif normalized_url in self.url_mapping:
                        target_path = self.url_mapping[normalized_url]

                    if target_path:
                        # 计算从当前文件到目标文件的相对路径
                        if current_file_path:
                            current_dir = current_file_path.parent
                            target_abs = self.trans_dir / target_path
                            try:
                                rel_link = os.path.relpath(target_abs, current_dir)
                                tag['href'] = rel_link
                            except ValueError:
                                tag['href'] = target_path
                        else:
                            tag['href'] = target_path

                        converted_count += 1
                        self.logger.debug(f"转换链接: {href} -> {tag['href']}")
                    else:
                        self.logger.debug(f"未找到本地文件映射: {href}")
                        self.stats['links_skipped'] += 1

            # 查找所有带src属性的标签（处理资源文件）
            for tag in soup.find_all(attrs={'src': True}):
                src = tag.get('src')

                if self._is_local_link(src):
                    self.logger.debug(f"跳过资源文件: {src}")

            return str(soup), converted_count

        except Exception as e:
            self.logger.error(f"转换HTML链接失败: {str(e)}")
            return html_content, 0

    def process_html_file(self, file_path: Path) -> bool:
        """
        处理单个HTML文件

        Args:
            file_path (Path): HTML文件路径

        Returns:
            bool: 处理是否成功
        """
        try:
            self.logger.info(f"处理文件: {file_path.relative_to(self.trans_dir)}")

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 转换链接（传入当前文件路径以计算相对路径）
            converted_content, converted_count = self._convert_links_in_html(original_content, file_path)

            # 如果有转换，则保存文件
            if converted_count > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(converted_content)

                self.stats['files_modified'] += 1
                self.stats['links_converted'] += converted_count
                self.logger.info(f"✅ {file_path.relative_to(self.trans_dir)}: 转换了 {converted_count} 个链接")
            else:
                self.logger.info(f"⏭️  {file_path.relative_to(self.trans_dir)}: 无需转换")

            self.stats['files_processed'] += 1
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
            self.logger.info("开始批量处理HTML文件...")

            # 重置统计信息
            self.stats = {
                'files_processed': 0,
                'files_modified': 0,
                'links_converted': 0,
                'links_skipped': 0
            }

            # 构建URL映射
            if not self.build_url_mapping():
                self.logger.error("无法构建URL映射，停止处理")
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
            self.logger.info(f"  🔗 转换链接: {self.stats['links_converted']}")
            self.logger.info(f"  ⏭️  跳过链接: {self.stats['links_skipped']}")
            self.logger.info("=" * 50)

            return self.stats

        except Exception as e:
            self.logger.error(f"批量处理失败: {str(e)}")
            return self.stats

    def get_stats(self) -> Dict[str, int]:
        """获取处理统计信息"""
        return self.stats.copy()


# 便捷函数
def localize_all_links(trans_dir: str = None) -> Dict[str, int]:
    """
    便捷函数：本地化所有HTML文件中的链接

    Args:
        trans_dir (str): 翻译文件目录，默认使用配置

    Returns:
        Dict[str, int]: 处理统计信息
    """
    localizer = LinkLocalizer(trans_dir)
    return localizer.process_all_files()


def localize_single_file(file_path: str, trans_dir: str = None) -> bool:
    """
    便捷函数：本地化单个文件中的链接

    Args:
        file_path (str): HTML文件路径
        trans_dir (str): 翻译文件目录

    Returns:
        bool: 处理是否成功
    """
    localizer = LinkLocalizer(trans_dir)
    localizer.build_url_mapping()
    return localizer.process_html_file(Path(file_path))


async def main():
    """主函数"""
    from config.logging_config import setup_logging

    setup_logging('INFO')

    print("链接本地化工具 - 批量处理模式")
    print("=" * 50)

    try:
        localizer = LinkLocalizer()
        print("🔄 开始处理所有HTML文件...")
        stats = localizer.process_all_files()

        print("\n" + "=" * 60)
        print("🎉 批量链接本地化完成！")
        print("=" * 60)
        print(f"📁 总文件数量: {stats['files_processed']}")
        print(f"✅ 成功处理: {stats['files_processed']}")
        print(f"📝 修改文件数: {stats['files_modified']}")
        print(f"🔗 转换链接数: {stats['links_converted']}")
        print(f"⏭️  跳过链接数: {stats['links_skipped']}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 批量处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n完成!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
