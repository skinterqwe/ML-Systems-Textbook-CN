#!/usr/bin/env python3
"""
主程序入口
支持两种翻译模式：
  - HTML 模式（原有）：爬取网页 → 翻译 → 链接本地化 → 页头信息
  - QMD 模式（新增）：读取本地 .qmd → Gemini 翻译 → Quarto 渲染

项目：ML Systems Textbook 中文翻译
"""

import argparse
import asyncio
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# 添加src目录到Python路径
sys.path.insert(0, 'src')

# 公共模块
from config.logging_config import setup_logging
from config.settings import Config


class TranslationPipeline:
    """翻译流水线，整合所有处理步骤"""

    def __init__(self, config: Config = None):
        """
        初始化翻译流水线

        Args:
            config (Config): 配置对象，如果未提供则使用默认配置
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)

        # 初始化各个组件
        self.crawler = None
        self.translator = None
        self.link_localizer = None
        self.header_adder = None

        # 流程统计信息
        self.stats = {
            'crawl_success': 0,
            'crawl_failed': 0,
            'translate_success': 0,
            'translate_failed': 0,
            'translate_skipped': 0,
            'localize_links': 0,
            'add_headers': 0,
            'total_time': 0
        }

        self.logger.info("翻译流水线初始化完成")

    async def initialize_components(self):
        """初始化所有组件"""
        try:
            self.logger.info("正在初始化各个组件...")

            from crawler import WebCrawler
            from translator import HTMLTranslator
            from link_localizer import LinkLocalizer
            from header_info_adder import HeaderInfoAdder

            # 初始化爬虫
            self.crawler = WebCrawler()
            self.logger.info("✅ 爬虫组件初始化完成")

            # 初始化翻译器
            self.translator = HTMLTranslator()
            self.logger.info("✅ 翻译器组件初始化完成")

            # 初始化链接本地化器
            self.link_localizer = LinkLocalizer()
            self.logger.info("✅ 链接本地化器初始化完成")

            # 初始化页头信息添加器
            self.header_adder = HeaderInfoAdder()
            self.logger.info("✅ 页头信息添加器初始化完成")

            self.logger.info("🎉 所有组件初始化完成")

        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            raise

    async def step1_crawl_pages(self, urls_file: str = "src/config/urls.txt") -> bool:
        """
        步骤1：爬取网页内容

        Args:
            urls_file (str): URL配置文件路径

        Returns:
            bool: 是否成功
        """
        self.logger.info("=" * 60)
        self.logger.info("📡 步骤1：开始爬取网页内容")
        self.logger.info("=" * 60)

        try:
            # 检查URL文件是否存在
            if not Path(urls_file).exists():
                self.logger.error(f"URL配置文件不存在: {urls_file}")
                return False

            # 从文件读取URL并批量爬取
            from crawler import crawl_from_file
            results = await crawl_from_file(urls_file)

            if not results:
                self.logger.error("未能爬取到任何内容")
                return False

            # 统计结果
            success_count = sum(1 for r in results if r.get('success', False))
            failed_count = len(results) - success_count

            self.stats['crawl_success'] = success_count
            self.stats['crawl_failed'] = failed_count

            self.logger.info(f"✅ 爬取完成: 成功 {success_count} 个，失败 {failed_count} 个")

            return success_count > 0

        except Exception as e:
            self.logger.error(f"爬取阶段失败: {str(e)}")
            return False

    async def step2_translate_pages(self, force_translate: bool = False) -> bool:
        """
        步骤2：翻译爬取的HTML页面

        Args:
            force_translate (bool): 是否强制翻译，即使翻译文件已存在

        Returns:
            bool: 是否成功
        """
        self.logger.info("=" * 60)
        self.logger.info("🌍 步骤2：开始翻译HTML页面")
        self.logger.info("=" * 60)

        try:
            # 获取所有原始HTML文件（递归匹配嵌套目录）
            origin_dir = Path(self.config.ORIGIN_DIR)
            html_files = list(origin_dir.glob("**/*.html"))

            if not html_files:
                self.logger.error(f"未找到原始HTML文件在目录: {origin_dir}")
                return False

            self.logger.info(f"找到 {len(html_files)} 个HTML文件需要翻译")

            success_count = 0
            failed_count = 0
            skipped_count = 0

            # 逐个翻译文件
            for html_file in html_files:
                try:
                    self.logger.info(f"处理文件: {html_file.relative_to(origin_dir)}")

                    # 使用translate_html_file函数，它会自动检查文件是否已存在
                    from translator import translate_html_file
                    result = await translate_html_file(str(html_file), force_translate)

                    if result:
                        # 检查是否是跳过的文件
                        trans_dir = Path(self.config.TRANS_DIR)
                        # 保持嵌套目录结构
                        rel_path = html_file.relative_to(origin_dir)
                        target_file = trans_dir / rel_path
                        if target_file.exists() and not force_translate:
                            if "跳过已翻译文件" in str(result) or result == str(target_file):
                                skipped_count += 1
                                self.logger.info(f"⏭️  {rel_path} 已存在，跳过翻译")
                            else:
                                success_count += 1
                                self.logger.info(f"✅ {rel_path} 翻译完成")
                        else:
                            success_count += 1
                            self.logger.info(f"✅ {rel_path} 翻译完成")
                    else:
                        failed_count += 1
                        self.logger.error(f"❌ {html_file.relative_to(origin_dir)} 翻译失败")

                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"❌ {html_file.relative_to(origin_dir)} 翻译出错: {str(e)}")

            self.stats['translate_success'] = success_count
            self.stats['translate_failed'] = failed_count
            self.stats['translate_skipped'] = skipped_count

            self.logger.info(f"✅ 翻译阶段完成:")
            self.logger.info(f"   📁 总文件数: {len(html_files)}")
            self.logger.info(f"   ✅ 翻译成功: {success_count}")
            self.logger.info(f"   ⏭️  跳过文件: {skipped_count}")
            self.logger.info(f"   ❌ 翻译失败: {failed_count}")

            # 只要有文件被处理（翻译或跳过）就认为成功
            return (success_count + skipped_count) > 0

        except Exception as e:
            self.logger.error(f"翻译阶段失败: {str(e)}")
            return False

    async def step3_localize_links(self) -> bool:
        """
        步骤3：本地化链接

        Returns:
            bool: 是否成功
        """
        self.logger.info("=" * 60)
        self.logger.info("🔗 步骤3：开始本地化链接")
        self.logger.info("=" * 60)

        try:
            # 构建URL映射
            self.link_localizer.build_url_mapping()

            # 处理所有文件
            stats = self.link_localizer.process_all_files()

            self.stats['localize_links'] = stats.get('links_converted', 0)

            self.logger.info(f"✅ 链接本地化完成:")
            self.logger.info(f"   📁 处理文件: {stats.get('files_processed', 0)} 个")
            self.logger.info(f"   🔗 转换链接: {stats.get('links_converted', 0)} 个")

            return True

        except Exception as e:
            self.logger.error(f"链接本地化阶段失败: {str(e)}")
            return False

    async def step4_add_headers(self) -> bool:
        """
        步骤4：添加页头信息

        Returns:
            bool: 是否成功
        """
        self.logger.info("=" * 60)
        self.logger.info("📝 步骤4：开始添加页头信息")
        self.logger.info("=" * 60)

        try:
            # 处理所有文件
            stats = self.header_adder.process_all_files()

            self.stats['add_headers'] = stats.get('headers_added', 0)

            self.logger.info(f"✅ 页头信息添加完成:")
            self.logger.info(f"   📁 处理文件: {stats.get('files_processed', 0)} 个")
            self.logger.info(f"   🏷️  添加页头: {stats.get('headers_added', 0)} 个")

            return True

        except Exception as e:
            self.logger.error(f"页头信息添加阶段失败: {str(e)}")
            return False

    async def run_full_pipeline(self, urls_file: str = "src/config/urls.txt") -> Dict:
        """
        运行完整的翻译流水线

        Args:
            urls_file (str): URL配置文件路径

        Returns:
            Dict: 流程统计信息
        """
        start_time = time.time()

        self.logger.info("🚀 开始运行完整翻译流水线")
        self.logger.info("流程：爬虫 → 翻译 → 链接本地化 → 页头信息添加")

        try:
            # 初始化所有组件
            await self.initialize_components()

            # 步骤1：爬取网页
            if not await self.step1_crawl_pages(urls_file):
                self.logger.error("❌ 爬取阶段失败，终止流程")
                return self.stats

            # 步骤2：翻译页面
            if not await self.step2_translate_pages():
                self.logger.error("❌ 翻译阶段失败，终止流程")
                return self.stats

            # 步骤3：本地化链接
            if not await self.step3_localize_links():
                self.logger.error("❌ 链接本地化失败，终止流程")
                return self.stats

            # 步骤4：添加页头信息
            if not await self.step4_add_headers():
                self.logger.error("❌ 页头信息添加失败，终止流程")
                return self.stats

            # 计算总耗时
            self.stats['total_time'] = time.time() - start_time

            # 显示最终统计
            self.show_final_stats()

            return self.stats

        except Exception as e:
            self.logger.error(f"流水线执行失败: {str(e)}")
            return self.stats

    def show_final_stats(self):
        """显示最终统计信息"""
        self.logger.info("=" * 80)
        self.logger.info("🎉 翻译流水线执行完成！")
        self.logger.info("=" * 80)

        self.logger.info("📊 执行统计:")
        self.logger.info(f"   📡 爬取成功: {self.stats['crawl_success']} 个页面")
        self.logger.info(f"   📡 爬取失败: {self.stats['crawl_failed']} 个页面")
        self.logger.info(f"   🌍 翻译成功: {self.stats['translate_success']} 个页面")
        self.logger.info(f"   ⏭️  翻译跳过: {self.stats['translate_skipped']} 个页面")
        self.logger.info(f"   🌍 翻译失败: {self.stats['translate_failed']} 个页面")
        self.logger.info(f"   🔗 本地化链接: {self.stats['localize_links']} 个")
        self.logger.info(f"   📝 添加页头: {self.stats['add_headers']} 个")
        self.logger.info(f"   ⏱️  总耗时: {self.stats['total_time']:.2f} 秒")

        # 计算成功率
        total_pages = self.stats['crawl_success'] + self.stats['crawl_failed']
        if total_pages > 0:
            success_rate = (self.stats['translate_success'] / total_pages) * 100
            self.logger.info(f"   📈 成功率: {success_rate:.1f}%")

        self.logger.info("=" * 80)

        # 检查输出目录（递归匹配嵌套目录）
        trans_dir = Path(self.config.TRANS_DIR)
        if trans_dir.exists():
            html_files = list(trans_dir.glob("**/*.html"))
            self.logger.info(f"✨ 翻译完成的文件位于: {trans_dir}")
            self.logger.info(f"📁 共生成 {len(html_files)} 个翻译文件")


# 便捷函数
async def run_full_translation(urls_file: str = "src/config/urls.txt") -> Dict:
    """
    便捷函数：运行完整翻译流程

    Args:
        urls_file (str): URL配置文件路径

    Returns:
        Dict: 执行统计信息
    """
    pipeline = TranslationPipeline()
    return await pipeline.run_full_pipeline(urls_file)


async def run_single_step(step: str, **kwargs) -> bool:
    """
    便捷函数：运行单个步骤

    Args:
        step (str): 步骤名称 ('crawl', 'translate', 'localize', 'headers')
        **kwargs: 步骤参数

    Returns:
        bool: 是否成功
    """
    pipeline = TranslationPipeline()
    await pipeline.initialize_components()

    if step == 'crawl':
        return await pipeline.step1_crawl_pages(kwargs.get('urls_file', 'src/config/urls.txt'))
    elif step == 'translate':
        return await pipeline.step2_translate_pages()
    elif step == 'localize':
        return await pipeline.step3_localize_links()
    elif step == 'headers':
        return await pipeline.step4_add_headers()
    else:
        raise ValueError(f"未知步骤: {step}")


def run_qmd_translation(source_dir: str, output_dir: str, force: bool = False,
                         single_file: str = None) -> Dict:
    """
    运行 QMD 翻译流程。

    Args:
        source_dir: QMD 源文件目录
        output_dir: 翻译输出目录
        force: 是否强制重新翻译已存在的文件
        single_file: 只翻译指定文件（用于测试）

    Returns:
        统计信息字典
    """
    logger = logging.getLogger(__name__)
    from qmd_translator import QMDTranslator

    source_path = Path(source_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

    # 收集需要翻译的文件
    if single_file:
        qmd_files = [Path(single_file)]
    else:
        qmd_files = sorted(source_path.rglob('*.qmd'))
        # 跳过 _ 前缀的文件和目录（Quarto 内部文件）
        qmd_files = [
            f for f in qmd_files
            if not any(part.startswith('_') for part in f.relative_to(source_path).parts)
        ]

    if not qmd_files:
        logger.warning(f"未找到 .qmd 文件: {source_dir}")
        return stats

    stats['total'] = len(qmd_files)
    logger.info(f"找到 {len(qmd_files)} 个 .qmd 文件")

    # 初始化翻译器
    translator = QMDTranslator()

    # 需要复制的配套文件扩展名
    COMPANION_EXTS = {'.bib', '.json', '.yml', '.yaml'}

    for qmd_file in qmd_files:
        rel_path = qmd_file.relative_to(source_path)
        out_file = output_path / rel_path

        # 检查是否跳过
        if out_file.exists() and not force:
            logger.info(f"⏭️  跳过已存在文件: {rel_path}")
            stats['skipped'] += 1
            # 仍然复制配套文件（以防缺失）
            _copy_companion_files(qmd_file, out_file, COMPANION_EXTS, logger)
            continue

        logger.info(f"📄 开始翻译: {rel_path}")

        # 翻译文件
        success = translator.translate_qmd_file(qmd_file, out_file)

        if success:
            # 注入 engine: jupyter（避免 Quarto 默认用 R 引擎）
            _inject_jupyter_engine(out_file)

            # 复制配套文件（.bib, .json, .yml 等）
            _copy_companion_files(qmd_file, out_file, COMPANION_EXTS, logger)

            # 复制 images 目录
            _copy_images_dir(qmd_file, out_file, logger)

            stats['success'] += 1
            logger.info(f"✅ 翻译完成: {rel_path}")
        else:
            stats['failed'] += 1
            logger.error(f"❌ 翻译失败: {rel_path}")

    return stats


def _inject_jupyter_engine(output_file: Path):
    """在 frontmatter 中注入 engine: jupyter。"""
    content = output_file.read_text(encoding='utf-8')
    if 'engine: jupyter' in content:
        return

    if content.startswith('---'):
        # 在已有的 frontmatter 中注入
        content = content.replace('\n---\n', '\nengine: jupyter\n---\n', 1)
    else:
        # 没有 frontmatter，添加一个
        content = '---\nengine: jupyter\n---\n\n' + content

    output_file.write_text(content, encoding='utf-8')


def _copy_companion_files(source_file: Path, output_file: Path,
                          companion_exts: set, logger):
    """复制同目录下的配套文件（.bib, .json, .yml 等）到输出目录。"""
    source_dir = source_file.parent
    output_dir = output_file.parent

    for item in source_dir.iterdir():
        if item.suffix in companion_exts and item.is_file():
            dst = output_dir / item.name
            if not dst.exists() or dst.stat().st_mtime < item.stat().st_mtime:
                shutil.copy2(item, dst)
                logger.debug(f"  复制配套文件: {item.name}")


def _copy_images_dir(source_file: Path, output_file: Path, logger):
    """复制 images 目录到输出目录。"""
    source_dir = source_file.parent
    output_dir = output_file.parent
    images_dir = source_dir / 'images'

    if images_dir.exists() and images_dir.is_dir():
        dst_images = output_dir / 'images'
        if dst_images.exists():
            shutil.rmtree(dst_images)
        shutil.copytree(images_dir, dst_images)
        logger.info(f"  复制图片目录: images/")


def print_qmd_stats(stats: Dict):
    """打印 QMD 翻译统计信息。"""
    print()
    print("=" * 60)
    print("📊 QMD 翻译统计:")
    print(f"   📁 总文件数: {stats['total']}")
    print(f"   ✅ 翻译成功: {stats['success']}")
    print(f"   ⏭️  跳过文件: {stats['skipped']}")
    print(f"   ❌ 翻译失败: {stats['failed']}")
    print("=" * 60)


def run_deploy(trans_dir: str, book_dir: str) -> bool:
    """
    将翻译后的 .qmd 文件复制到 output/book/contents/ 覆盖英文原文。

    Args:
        trans_dir: 翻译输出目录（如 output/qmd_trans）
        book_dir: Quarto 源目录（如 output/book/contents）

    Returns:
        是否有文件被复制
    """
    logger = logging.getLogger(__name__)
    trans_path = Path(trans_dir)
    book_path = Path(book_dir)

    if not trans_path.exists():
        logger.error(f"翻译目录不存在: {trans_dir}")
        print(f"❌ 翻译目录不存在: {trans_dir}")
        print(f"请先运行翻译: python3.9 main.py --mode qmd")
        return False

    # 收集所有已翻译的 .qmd 文件
    trans_qmds = list(trans_path.rglob('*.qmd'))
    if not trans_qmds:
        logger.warning(f"翻译目录中没有 .qmd 文件: {trans_dir}")
        print(f"⚠️  翻译目录中没有 .qmd 文件")
        return False

    copied = 0
    skipped = 0

    for trans_file in trans_qmds:
        # 计算相对路径，找到对应的目标文件
        rel_path = trans_file.relative_to(trans_path)
        target_file = book_path / rel_path

        if not target_file.parent.exists():
            logger.warning(f"目标目录不存在，跳过: {rel_path.parent}")
            skipped += 1
            continue

        # 复制 .qmd 文件
        shutil.copy2(trans_file, target_file)
        logger.info(f"✅ 部署: {rel_path}")
        copied += 1

        # 复制同目录下的配套文件（.bib, .json, .yml 等）
        for item in trans_file.parent.iterdir():
            if item.suffix in {'.bib', '.json', '.yml', '.yaml'} and item.is_file():
                dst = target_file.parent / item.name
                if not dst.exists() or dst.stat().st_mtime < item.stat().st_mtime:
                    shutil.copy2(item, dst)
                    logger.debug(f"  配套文件: {item.name}")

        # 复制 images 目录
        images_dir = trans_file.parent / 'images'
        if images_dir.exists() and images_dir.is_dir():
            dst_images = target_file.parent / 'images'
            if dst_images.exists():
                shutil.rmtree(dst_images)
            shutil.copytree(images_dir, dst_images)
            logger.debug(f"  图片目录: images/")

    print()
    print("=" * 60)
    print("📊 部署统计:")
    print(f"   ✅ 已复制: {copied} 个文件")
    if skipped:
        print(f"   ⏭️  跳过: {skipped} 个文件（目标目录不存在）")
    print("=" * 60)

    if copied > 0:
        print(f"\n✨ 译文已复制到 {book_dir}/")
        print("下一步：提交并推送以触发 GitHub Pages 部署")
        print("  git add -f output/book/contents/")
        print("  git commit -m 'update: 部署中文翻译'")
        print("  git push origin master")

    return copied > 0


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description='ML Systems Textbook 翻译流水线',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  %(prog)s --mode html                         # 运行 HTML 翻译流水线
  %(prog)s --mode qmd                          # 翻译所有 QMD 文件
  %(prog)s --mode qmd --file path/to/file.qmd  # 只翻译指定文件
  %(prog)s --mode qmd --force                  # 强制重新翻译
  %(prog)s --mode qmd --deploy                 # 翻译并部署到 Quarto 源目录
  %(prog)s --deploy                            # 只部署（不翻译），需已有翻译结果
  %(prog)s --mode qmd --source /path/to/vol1/  # 指定源目录
  %(prog)s --mode qmd --output output/my_trans/ # 指定输出目录
"""
    )
    parser.add_argument('--mode', choices=['html', 'qmd'], default='html',
                        help='翻译模式：html（网页翻译）或 qmd（本地 .qmd 翻译），默认 html')
    parser.add_argument('--source', default='output/book/contents',
                        help='QMD 源目录，默认 output/book/contents')
    parser.add_argument('--output', default='output/qmd_trans',
                        help='QMD 输出目录，默认 output/qmd_trans')
    parser.add_argument('--force', action='store_true',
                        help='强制重新翻译已存在的文件')
    parser.add_argument('--file', default=None,
                        help='只翻译指定的单个 .qmd 文件（用于测试）')
    parser.add_argument('--deploy', action='store_true',
                        help='翻译后将译文复制到 Quarto 源目录（覆盖英文原文）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细日志')
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    # 设置日志
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level)

    if args.mode == 'qmd':
        # QMD 翻译模式
        print("=" * 80)
        print("🌍 ML Systems Textbook QMD 翻译模式")
        print("=" * 80)
        print(f"源目录: {args.source}")
        print(f"输出目录: {args.output}")
        if args.file:
            print(f"指定文件: {args.file}")
        if args.deploy:
            print(f"部署模式: 翻译后将覆盖 {args.source} 中的英文原文")
        print()

        try:
            start_time = time.time()
            stats = run_qmd_translation(
                source_dir=args.source,
                output_dir=args.output,
                force=args.force,
                single_file=args.file,
            )
            elapsed = time.time() - start_time
            stats['total_time'] = elapsed

            print_qmd_stats(stats)

            if stats['success'] > 0 or (stats['skipped'] > 0 and stats['failed'] == 0):
                print(f"\n⏱️  总耗时: {elapsed:.1f} 秒")
                print(f"✨ 翻译结果位于: {args.output}/")

                # --deploy：复制译文到 Quarto 源目录
                if args.deploy:
                    print()
                    print("=" * 80)
                    print("   开始部署译文到 Quarto 源目录")
                    print("=" * 80)
                    run_deploy(args.output, args.source)

            elif stats['skipped'] > 0 and stats['failed'] == 0:
                print(f"\n所有文件已存在，使用 --force 强制重新翻译")
            else:
                print(f"\n⚠️  没有成功翻译任何文件")

        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断执行")
        except Exception as e:
            print(f"\n❌ 执行失败: {str(e)}")
            import traceback
            traceback.print_exc()

    elif args.deploy:
        # 单独部署模式（不翻译，只复制已有翻译结果）
        print("=" * 80)
        print("   部署模式：将译文复制到 Quarto 源目录")
        print("=" * 80)
        run_deploy(args.output, args.source)

    else:
        # HTML 翻译模式（原有流程）
        print("=" * 80)
        print("🌍 ML Systems Textbook 翻译流水线")
        print("=" * 80)
        print("流程：爬虫 → 翻译 → 链接本地化 → 页头信息添加")
        print()

        # 检查必要文件
        urls_file = "src/config/urls.txt"
        if not Path(urls_file).exists():
            print(f"❌ 错误: URL配置文件不存在: {urls_file}")
            print("请确保该文件存在并包含要爬取的URL列表")
            return

        try:
            # 运行完整流水线
            stats = await run_full_translation(urls_file)

            if stats['translate_success'] > 0:
                print("\n🎉 翻译流水线执行成功！")
                print("您可以在 output/trans/ 目录中查看翻译结果")
            else:
                print("\n⚠️  翻译流水线执行完成，但没有成功翻译任何页面")
                print("请检查日志以了解详细信息")

        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断执行")
        except Exception as e:
            print(f"\n❌ 执行失败: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
