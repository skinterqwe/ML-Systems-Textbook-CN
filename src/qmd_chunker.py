"""
QMD 分块模块
将大型 .qmd 文件按 Markdown 标题分块，保持语义完整性。

项目：ML Systems Textbook 中文翻译
"""

import logging
import re
from typing import List, Tuple


class QMDChunker:
    """QMD 文件分块器，按 Markdown 标题分块，保持语义完整性。"""

    def __init__(self, max_chars: int = 60000):
        """
        Args:
            max_chars: 每个块的最大字符数
        """
        self.max_chars = max_chars
        self.logger = logging.getLogger(__name__)

    def split(self, content: str) -> Tuple[str, List[str]]:
        """
        将 QMD 内容分块。

        Args:
            content: 完整的 QMD 文件内容

        Returns:
            (frontmatter, chunks): frontmatter 字符串和分块列表
        """
        frontmatter, body = self._extract_frontmatter(content)

        # 按 ## 二级标题切割
        sections = self._split_by_heading(body, level=2)

        # 处理超大块
        chunks: List[str] = []
        for section in sections:
            if len(section) > self.max_chars:
                sub_sections = self._split_by_heading(section, level=3)
                for sub in sub_sections:
                    if len(sub) > self.max_chars:
                        chunks.extend(self._split_by_paragraphs(sub))
                    else:
                        chunks.append(sub)
            else:
                chunks.append(section)

        self.logger.info(f"分块完成: frontmatter + {len(chunks)} 个块")
        return frontmatter, chunks

    def merge(self, frontmatter: str, chunks: List[str]) -> str:
        """
        合并分块：加回 YAML frontmatter，块之间用空行分隔。

        Args:
            frontmatter: YAML frontmatter
            chunks: 翻译后的块列表

        Returns:
            合并后的完整 QMD 内容
        """
        parts: List[str] = []
        if frontmatter:
            parts.append(frontmatter)
        for chunk in chunks:
            chunk = chunk.rstrip('\n')
            if parts:
                parts.append('')  # 空行分隔
            parts.append(chunk)
        return "\n".join(parts) + "\n"

    def _extract_frontmatter(self, content: str) -> Tuple[str, str]:
        """
        分离 YAML frontmatter。

        Returns:
            (frontmatter, body): frontmatter（含 --- 分隔符）和正文
        """
        lines = content.split('\n')
        if not lines or lines[0].strip() != '---':
            return "", content

        # 找第二个 ---
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                frontmatter = '\n'.join(lines[:i + 1])
                body = '\n'.join(lines[i + 1:])
                return frontmatter, body

        # 没有闭合的 ---，视为无 frontmatter
        return "", content

    def _split_by_heading(self, content: str, level: int = 2) -> List[str]:
        """
        按指定级别的 Markdown 标题切割内容。

        不会将标题行本身切丢，标题行归属其所在的块。

        Args:
            content: 要切割的内容
            level: 标题级别（2 = ##, 3 = ###）

        Returns:
            切割后的块列表
        """
        prefix = '#' * level + ' '
        lines = content.split('\n')

        chunks: List[str] = []
        current_chunk_lines: List[str] = []

        for line in lines:
            # 检查是否是目标级别的标题行（允许前面有空格，但不能在代码块内）
            if re.match(rf'^{re.escape("#" * level)}\s', line):
                # 保存之前的块（如果有内容）
                if current_chunk_lines:
                    chunks.append('\n'.join(current_chunk_lines))
                current_chunk_lines = [line]
            else:
                current_chunk_lines.append(line)

        # 最后一个块
        if current_chunk_lines:
            chunks.append('\n'.join(current_chunk_lines))

        # 如果整个内容没有找到标题，返回完整内容作为一个块
        if not chunks:
            chunks = [content]

        return chunks

    def _split_by_paragraphs(self, content: str) -> List[str]:
        """
        按段落（空行）切割，不打断代码块。

        Args:
            content: 要切割的内容

        Returns:
            切割后的块列表
        """
        chunks: List[str] = []
        current_lines: List[str] = []
        current_chars = 0
        in_code_block = False

        lines = content.split('\n')

        for i, line in enumerate(lines):
            # 跟踪代码块状态
            if line.strip().startswith('```'):
                in_code_block = not in_code_block

            current_lines.append(line)
            current_chars += len(line) + 1

            # 在代码块外且遇到空行且已超过阈值时切割
            if (not in_code_block
                    and line.strip() == ''
                    and current_chars >= self.max_chars):
                chunks.append('\n'.join(current_lines))
                current_lines = []
                current_chars = 0

        # 最后一个块
        if current_lines:
            chunks.append('\n'.join(current_lines))

        # 如果仍然有超大块，强制按行切割
        final_chunks: List[str] = []
        for chunk in chunks:
            if len(chunk) > self.max_chars * 1.5:
                final_chunks.extend(self._force_split(chunk))
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _force_split(self, content: str) -> List[str]:
        """强制按行切割超大块，保证不打断代码块。"""
        lines = content.split('\n')
        chunks: List[str] = []
        current: List[str] = []
        current_chars = 0
        in_code_block = False

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block

            current.append(line)
            current_chars += len(line) + 1

            # 只在代码块外切割，且需要在空行处
            if (not in_code_block
                    and line.strip() == ''
                    and current_chars >= self.max_chars):
                chunks.append('\n'.join(current))
                current = []
                current_chars = 0

        if current:
            chunks.append('\n'.join(current))

        return chunks if chunks else [content]
