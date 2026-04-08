"""
HTML翻译模块
使用Gemini API进行智能翻译，保持HTML格式完全一致

项目：ML Systems Textbook 中文翻译
"""

import logging
import time
import json
import sys
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup, NavigableString, Comment

from gemini_api import GeminiAPI
from config.settings import OUTPUT_DIR, TRANS_DIR


class TranslationResponse(BaseModel):
    """翻译响应的结构化模型"""
    translated_html: str = Field(description="翻译后的完整HTML内容，保持原格式不变")


class MetadataTranslationResponse(BaseModel):
    """元数据翻译响应的结构化模型"""
    translated_title: str = Field(description="翻译后的页面标题")
    translated_description: str = Field(description="翻译后的页面描述")


class HTMLParts(BaseModel):
    """HTML各部分的结构化模型"""
    head_content: str = Field(description="head部分的完整内容")
    body_content: str = Field(description="body部分的完整内容")
    original_title: str = Field(description="原始页面标题")
    original_description: str = Field(description="原始页面描述")
    html_attrs: str = Field(description="html标签的属性")
    doctype: str = Field(description="文档类型声明")


class HTMLTranslator:
    """HTML翻译器，使用Gemini API进行智能翻译"""

    def __init__(self):
        """初始化翻译器"""
        self.logger = logging.getLogger(__name__)

        # 初始化Gemini API
        try:
            self.gemini_api = GeminiAPI()
            self.logger.info("Gemini API初始化成功")
        except Exception as e:
            self.logger.error(f"Gemini API初始化失败: {str(e)}")
            raise

        # 确保输出目录存在
        Path(TRANS_DIR).mkdir(parents=True, exist_ok=True)

        # 数学内容存储（用于占位符机制）
        self.math_content_store: Dict[str, str] = {}

        # 专业术语词典（ML/DL 全领域，80+ 条目）
        self.terminology = {
            # 基础概念
            "deep learning": "深度学习",
            "machine learning": "机器学习",
            "neural network": "神经网络",
            "artificial intelligence": "人工智能",
            "supervised learning": "监督学习",
            "unsupervised learning": "无监督学习",
            "semi-supervised learning": "半监督学习",
            "self-supervised learning": "自监督学习",
            "reinforcement learning": "强化学习",
            "transfer learning": "迁移学习",
            "representation learning": "表征学习",
            "feature extraction": "特征提取",
            "feature engineering": "特征工程",
            "data distribution": "数据分布",
            "generalization": "泛化",
            "overfitting": "过拟合",
            "underfitting": "欠拟合",
            "bias": "偏差",
            "variance": "方差",
            "regularization": "正则化",
            # 训练相关
            "gradient descent": "梯度下降",
            "stochastic gradient descent": "随机梯度下降",
            "backpropagation": "反向传播",
            "loss function": "损失函数",
            "cost function": "代价函数",
            "learning rate": "学习率",
            "batch size": "批量大小",
            "epoch": "轮次",
            "optimizer": "优化器",
            "momentum": "动量",
            "weight": "权重",
            "parameter": "参数",
            "hyperparameter": "超参数",
            "convergence": "收敛",
            "loss landscape": "损失面",
            "gradient": "梯度",
            "activation function": "激活函数",
            "dropout": "Dropout",
            "batch normalization": "批归一化",
            "layer normalization": "层归一化",
            "weight decay": "权重衰减",
            "learning rate schedule": "学习率调度",
            "warmup": "预热",
            "early stopping": "早停",
            "cross-validation": "交叉验证",
            "training set": "训练集",
            "validation set": "验证集",
            "test set": "测试集",
            # 网络架构
            "convolutional neural network": "卷积神经网络",
            "CNN": "CNN",
            "recurrent neural network": "循环神经网络",
            "RNN": "RNN",
            "LSTM": "LSTM",
            "GRU": "GRU",
            "transformer": "Transformer",
            "attention": "注意力机制",
            "self-attention": "自注意力",
            "multi-head attention": "多头注意力",
            "encoder": "编码器",
            "decoder": "解码器",
            "embedding": "嵌入",
            "fully connected layer": "全连接层",
            "dense layer": "密集层",
            "convolutional layer": "卷积层",
            "pooling layer": "池化层",
            "residual connection": "残差连接",
            "skip connection": "跳跃连接",
            "feedforward": "前馈",
            "hidden layer": "隐藏层",
            "output layer": "输出层",
            "input layer": "输入层",
            # 生成模型
            "large language model": "大语言模型",
            "LLM": "LLM",
            "GPT": "GPT",
            "BERT": "BERT",
            "diffusion model": "扩散模型",
            "generative adversarial network": "生成对抗网络",
            "GAN": "GAN",
            "variational autoencoder": "变分自编码器",
            "VAE": "VAE",
            "autoregressive": "自回归",
            "token": "Token",
            "tokenizer": "分词器",
            "vocabulary": "词汇表",
            "prompt": "提示",
            "fine-tuning": "微调",
            "pre-training": "预训练",
            "in-context learning": "上下文学习",
            "few-shot learning": "少样本学习",
            "zero-shot learning": "零样本学习",
            "instruction tuning": "指令微调",
            "RLHF": "RLHF",
            # 优化部署
            "quantization": "量化",
            "pruning": "剪枝",
            "distillation": "蒸馏",
            "knowledge distillation": "知识蒸馏",
            "model compression": "模型压缩",
            "inference": "推理",
            "latency": "延迟",
            "throughput": "吞吐量",
            "deployment": "部署",
            "serving": "服务化",
            "ONNX": "ONNX",
            "TensorRT": "TensorRT",
            "hardware acceleration": "硬件加速",
            "parallelism": "并行",
            "data parallelism": "数据并行",
            "model parallelism": "模型并行",
            "pipeline parallelism": "流水线并行",
            "distributed training": "分布式训练",
            "mixed precision": "混合精度",
            # 硬件相关
            "GPU": "GPU",
            "TPU": "TPU",
            "CUDA": "CUDA",
            "tensor core": "Tensor Core",
            "systolic array": "脉动阵列",
            "memory bandwidth": "内存带宽",
            "FLOPs": "FLOPs",
            "FLOPS": "FLOPS",
            "HBM": "HBM",
            "SRAM": "SRAM",
            "DRAM": "DRAM",
            "ASIC": "ASIC",
            "FPGA": "FPGA",
            # 可信AI
            "robustness": "鲁棒性",
            "adversarial attack": "对抗攻击",
            "adversarial example": "对抗样本",
            "fairness": "公平性",
            "bias in AI": "AI偏见",
            "privacy": "隐私",
            "differential privacy": "差分隐私",
            "federated learning": "联邦学习",
            "explainability": "可解释性",
            "interpretability": "可解释性",
            "responsible AI": "负责任的AI",
            "AI safety": "AI安全",
            "alignment": "对齐",
            "hallucination": "幻觉",
            # 系统相关
            "benchmark": "基准测试",
            "workload": "工作负载",
            "scalability": "可扩展性",
            "throughput": "吞吐量",
            "bottleneck": "瓶颈",
            "optimization": "优化",
            "scheduling": "调度",
            "load balancing": "负载均衡",
            "cache": "缓存",
            "memory hierarchy": "内存层次结构",
            "roofline model": "屋顶线模型",
            "MLOps": "MLOps",
            "pipeline": "流水线",
            "feature store": "特征存储",
            # 数据相关
            "data augmentation": "数据增强",
            "data preprocessing": "数据预处理",
            "label": "标签",
            "annotation": "标注",
            "ground truth": "真值",
            "data pipeline": "数据流水线",
            "data quality": "数据质量",
            # 常见缩写
            "API": "API",
            "SDK": "SDK",
            "NLP": "NLP",
            "CV": "CV",
            "IoT": "IoT",
            "REST": "REST",
            # 翻译UI相关
            "Footnotes": "脚注",
            "References": "参考文献",
            "Citation": "引用",
            "Authors": "作者",
            "Published": "发布日期",
            "Contents": "目录",
            "Chapter": "章",
            "Section": "节",
            "Figure": "图",
            "Table": "表",
            "Algorithm": "算法",
            "Equation": "方程",
            "Theorem": "定理",
            "Proof": "证明",
            "Definition": "定义",
            "Example": "示例",
            "Note": "注",
            "Summary": "总结",
            "Key Takeaways": "关键要点",
            "Exercises": "练习",
            "Quiz": "测验",
            "Glossary": "术语表",
            "Bibliography": "参考文献",
            "Appendix": "附录",
        }

        self.logger.info("HTML翻译器初始化完成")

    def extract_html_parts(self, html_content: str) -> HTMLParts:
        """
        提取HTML的各个部分

        Args:
            html_content (str): 完整的HTML内容

        Returns:
            HTMLParts: 分离后的HTML各部分
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 提取doctype
            doctype = "<!DOCTYPE html>"
            for item in soup.contents:
                if hasattr(item, 'name') and item.name is None:
                    doctype_str = str(item).strip()
                    if doctype_str.upper().startswith('<!DOCTYPE'):
                        doctype = doctype_str
                        break

            # 获取html标签属性
            html_tag = soup.find('html')
            html_attrs = ""
            if html_tag and html_tag.attrs:
                attrs_list = [f'{k}="{v}"' if isinstance(v, str) else f'{k}="{" ".join(v)}"'
                             for k, v in html_tag.attrs.items()]
                html_attrs = " " + " ".join(attrs_list)

            # 提取head内容
            head_tag = soup.find('head')
            head_content = str(head_tag) if head_tag else "<head></head>"

            # 提取body内容
            body_tag = soup.find('body')
            body_content = str(body_tag) if body_tag else "<body></body>"

            # 提取标题
            title_tag = soup.find('title')
            original_title = title_tag.get_text() if title_tag else ""

            # 提取描述
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            original_description = desc_tag.get('content', '') if desc_tag else ""

            parts = HTMLParts(
                head_content=head_content,
                body_content=body_content,
                original_title=original_title,
                original_description=original_description,
                html_attrs=html_attrs,
                doctype=doctype
            )

            return parts

        except Exception as e:
            self.logger.error(f"HTML解析失败: {str(e)}")
            raise

    def _clean_body_for_translation(self, body_content: str) -> str:
        """
        清理body内容，移除不需要翻译的部分，并使用占位符替换数学内容

        对于 Quarto 生成的页面，数学公式使用 span 标签（class 包含 'math'），
        而非 mjx-container。

        Args:
            body_content (str): 原始body内容

        Returns:
            str: 清理后的body内容
        """
        try:
            soup = BeautifulSoup(body_content, 'html.parser')

            # 移除注释
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # 清空数学内容存储，开始新的翻译任务
            self.math_content_store.clear()

            # 提取并替换数学公式标签
            # Quarto 使用 span.math（可能有 span.math-display, span.math 等）
            # 同时兼容 mjx-container（以防万一）
            math_elements = []

            # 查找 class 包含 'math' 的 span 标签
            for span in soup.find_all('span'):
                classes = span.get('class', [])
                if any('math' in cls for cls in classes):
                    math_elements.append(span)

            # 也查找 mjx-container（兼容性）
            mjx_containers = soup.find_all('mjx-container')
            math_elements.extend(mjx_containers)

            for i, element in enumerate(math_elements):
                placeholder = f"MATH_PLACEHOLDER_{i:03d}"
                # 保存完整的标签内容
                self.math_content_store[placeholder] = str(element)
                # 创建占位符标签
                placeholder_tag = soup.new_tag('span', **{'data-math-placeholder': placeholder})
                placeholder_tag.string = placeholder
                # 替换原标签
                element.replace_with(placeholder_tag)

            self.logger.info(f"提取了 {len(math_elements)} 个数学公式标签")

            return str(soup)

        except Exception as e:
            self.logger.error(f"内容清理失败: {str(e)}")
            return body_content

    def _translate_metadata(self, title: str, description: str) -> Optional[Dict[str, str]]:
        """
        翻译页面标题和描述

        Args:
            title (str): 原始标题
            description (str): 原始描述

        Returns:
            Optional[Dict[str, str]]: 翻译后的标题和描述
        """
        if not title and not description:
            return None

        try:
            terminology_list = "\n".join([f"- {en}: {zh}" for en, zh in self.terminology.items()])

            prompt = f"""你是一个专业的技术文档翻译专家，请翻译以下页面元数据：

专业术语对照表：
{terminology_list}

翻译要求：
1. 保持技术术语的一致性
2. 标题要简洁明了，符合中文习惯
3. 描述要准确传达原文含义，保持专业性

原始标题: {title}
原始描述: {description}

请只返回翻译后的标题和描述，不要添加任何解释。"""

            response = self.gemini_api.generate_structured_content(
                prompt=prompt,
                response_schema=MetadataTranslationResponse
            )

            if response:
                return {
                    'title': response.translated_title,
                    'description': response.translated_description
                }
            else:
                return None

        except Exception as e:
            self.logger.error(f"元数据翻译失败: {str(e)}")
            return None

    def _restore_math_content(self, translated_html: str) -> str:
        """
        将占位符替换回原始的数学内容

        Args:
            translated_html (str): 包含占位符的翻译后HTML

        Returns:
            str: 恢复数学内容后的HTML
        """
        try:
            if not self.math_content_store:
                return translated_html

            soup = BeautifulSoup(translated_html, 'html.parser')

            # 查找所有占位符标签
            placeholders = soup.find_all('span', attrs={'data-math-placeholder': True})
            restored_count = 0

            for placeholder_tag in placeholders:
                placeholder_key = placeholder_tag.get('data-math-placeholder')
                if placeholder_key in self.math_content_store:
                    # 获取原始数学内容
                    original_math = self.math_content_store[placeholder_key]
                    # 解析原始数学标签
                    math_soup = BeautifulSoup(original_math, 'html.parser')

                    # 尝试查找 mjx-container 或 span.math
                    math_tag = math_soup.find('mjx-container')
                    if not math_tag:
                        # 查找 class 包含 math 的 span
                        for span in math_soup.find_all('span'):
                            classes = span.get('class', [])
                            if any('math' in cls for cls in classes):
                                math_tag = span
                                break

                    if math_tag:
                        # 替换占位符
                        placeholder_tag.replace_with(math_tag)
                        restored_count += 1

            self.logger.info(f"恢复了 {restored_count} 个数学公式标签")
            return str(soup)

        except Exception as e:
            self.logger.error(f"恢复数学内容失败: {str(e)}")
            return translated_html

    def reassemble_html(self, parts: HTMLParts, translated_body: str,
                       translated_title: str = "", translated_description: str = "") -> str:
        """
        重新组装HTML

        Args:
            parts (HTMLParts): 原始HTML各部分
            translated_body (str): 翻译后的body内容
            translated_title (str): 翻译后的标题
            translated_description (str): 翻译后的描述

        Returns:
            str: 完整的翻译后HTML
        """
        try:
            # 首先恢复数学内容
            translated_body_with_math = self._restore_math_content(translated_body)

            # 解析head内容以更新标题和描述
            head_soup = BeautifulSoup(parts.head_content, 'html.parser')

            # 更新标题
            if translated_title:
                title_tag = head_soup.find('title')
                if title_tag:
                    title_tag.string = translated_title
                else:
                    new_title = head_soup.new_tag('title')
                    new_title.string = translated_title
                    if head_soup.head:
                        head_soup.head.insert(0, new_title)

            # 更新描述
            if translated_description:
                desc_tag = head_soup.find('meta', attrs={'name': 'description'})
                if desc_tag:
                    desc_tag['content'] = translated_description
                else:
                    if head_soup.head:
                        new_desc = head_soup.new_tag('meta', name='description', content=translated_description)
                        head_soup.head.append(new_desc)

            # 更新语言属性
            html_attrs_updated = parts.html_attrs
            if 'lang=' in html_attrs_updated:
                html_attrs_updated = re.sub(r'lang="[^"]*"', 'lang="zh-CN"', html_attrs_updated)
            elif html_attrs_updated:
                html_attrs_updated += ' lang="zh-CN"'
            else:
                html_attrs_updated = ' lang="zh-CN"'

            # 组装完整HTML
            doctype = parts.doctype if parts.doctype else "<!DOCTYPE html>"

            if head_soup.head:
                updated_head = str(head_soup.head)
            else:
                updated_head = parts.head_content

            complete_html = f"""{doctype}
<html{html_attrs_updated}>
{updated_head}
{translated_body_with_math}
</html>"""

            # 检查并修复HTML开头的多余文本
            complete_html = self._fix_html_prefix(complete_html)

            return complete_html

        except Exception as e:
            self.logger.error(f"HTML组装失败: {str(e)}")
            raise

    def _fix_html_prefix(self, html_content: str) -> str:
        """
        修复HTML开头的多余文本问题，并确保有正确的DOCTYPE声明

        Args:
            html_content (str): HTML内容

        Returns:
            str: 修复后的HTML内容
        """
        try:
            lines = html_content.split('\n')
            fixed_lines = []
            has_doctype = False

            for i, line in enumerate(lines):
                if i == 0 and line.strip().lower() == 'html':
                    self.logger.warning("检测到HTML开头多余的'html'文本，已移除")
                    continue
                elif i == 0 and line.strip() and not line.strip().startswith('<!DOCTYPE'):
                    if not line.strip().startswith('<'):
                        self.logger.warning(f"检测到HTML开头多余文本: '{line.strip()}'，已移除")
                        continue

                if line.strip().upper().startswith('<!DOCTYPE'):
                    has_doctype = True

                fixed_lines.append(line)

            if not has_doctype:
                self.logger.warning("检测到缺少DOCTYPE声明，已添加")
                fixed_lines.insert(0, '<!DOCTYPE html>')

            return '\n'.join(fixed_lines)

        except Exception as e:
            self.logger.error(f"修复HTML前缀失败: {str(e)}")
            return html_content

    def _build_translation_prompt(self, html_content: str) -> str:
        """
        构建翻译提示词

        Args:
            html_content (str): 要翻译的HTML内容

        Returns:
            str: 构建好的提示词
        """
        terminology_list = "\n".join([f"- {en}: {zh}" for en, zh in self.terminology.items()])

        prompt = f"""你是一个专业的技术文档翻译专家，专门翻译机器学习和深度学习相关的技术文章。

请将以下HTML内容从英文翻译成中文，要求：

1. **格式保持**：完全保持原HTML结构、标签、属性、CSS类名、ID等不变
2. **内容翻译**：只翻译HTML标签内的文本内容，不翻译HTML标签本身
3. **术语一致性**：使用以下专业术语对照表保持翻译一致性：
{terminology_list}

4. **翻译质量**：
   - 准确传达原文技术含义
   - 保持中文表达的流畅性和自然性
   - 保持技术文档的专业性和严谨性
   - 数学公式、代码片段、URL链接保持不变

5. **特殊处理**：
   - HTML注释不翻译
   - JavaScript代码不翻译
   - CSS样式不翻译
   - 属性值不翻译（如class名、id等）
   - 锚点链接（#开头）不翻译
   - 数学公式占位符（MATH_PLACEHOLDER_XXX）不翻译，保持原样

请只返回翻译后的完整HTML内容，不要添加任何解释或额外信息。

原HTML内容：
{html_content}"""

        return prompt

    async def _translate_body_content(self, body_content: str, context: str = "") -> Optional[Dict]:
        """
        翻译body内容（内部方法）

        Args:
            body_content (str): 要翻译的body内容
            context (str): 翻译上下文（可选）

        Returns:
            Optional[Dict]: 翻译结果字典，失败时返回None
        """
        if not body_content:
            return None

        try:
            prompt = self._build_translation_prompt(body_content)

            start_time = time.time()

            response = self.gemini_api.generate_structured_content_with_stream(
                prompt=prompt,
                response_schema=TranslationResponse
            )

            translation_time = time.time() - start_time

            if response and response.translated_html:
                translation_result = {
                    'original_html': body_content,
                    'translated_html': response.translated_html,
                    'original_length': len(body_content),
                    'translated_length': len(response.translated_html),
                    'translation_time': translation_time,
                    'success': True,
                    'timestamp': time.time(),
                    'context': context
                }

                return translation_result
            else:
                return None

        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return None

    async def translate_html(self, html_content: str, context: str = "") -> Optional[str]:
        """
        HTML翻译方法：分离head和body，只翻译必要内容，翻译元数据

        Args:
            html_content (str): 完整的HTML内容
            context (str): 翻译上下文（可选）

        Returns:
            Optional[str]: 翻译后保存的文件路径，失败时返回None
        """
        if not html_content:
            return None

        self.logger.info(f"开始翻译: {len(html_content):,}字符")
        start_time = time.time()

        try:
            # 1. 提取HTML各部分
            parts = self.extract_html_parts(html_content)

            # 2. 翻译元数据（标题和描述）
            translated_metadata = self._translate_metadata(
                parts.original_title,
                parts.original_description
            )

            translated_title = ""
            translated_description = ""
            if translated_metadata:
                translated_title = translated_metadata.get('title', '')
                translated_description = translated_metadata.get('description', '')

            # 3. 清理并翻译body内容
            cleaned_body = self._clean_body_for_translation(parts.body_content)
            body_reduction = len(parts.body_content) - len(cleaned_body)

            body_translation_result = await self._translate_body_content(cleaned_body, f"Body部分 - {context}")

            if not body_translation_result or not body_translation_result.get('success'):
                return None

            translated_body = body_translation_result['translated_html']

            # 4. 重新组装HTML
            complete_translated_html = self.reassemble_html(
                parts,
                translated_body,
                translated_title,
                translated_description
            )

            translation_time = time.time() - start_time

            # 保存翻译后的HTML，保持嵌套目录结构
            trans_dir = Path(TRANS_DIR)
            trans_dir.mkdir(parents=True, exist_ok=True)

            # 从context中提取文件路径，保持嵌套结构
            if "文件:" in context:
                input_file = context.split("文件:")[1].strip()
                input_path = Path(input_file)
                origin_dir = Path(OUTPUT_DIR) / "origin"
                try:
                    rel_path = input_path.relative_to(origin_dir)
                    filename = str(rel_path)
                except ValueError:
                    filename = input_path.name
            else:
                filename = "translated.html"

            file_path = trans_dir / filename

            # 确保父目录存在（嵌套路径）
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存翻译后的HTML
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(complete_translated_html)

            self.logger.info(f"翻译完成: {filename} ({translation_time:.1f}s, 节省{body_reduction/len(parts.body_content)*100:.0f}%内容)")

            return str(file_path)

        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return None

    async def translate_article(self, content: str, title: str = "", url: str = "") -> Optional[str]:
        """
        翻译完整文章

        Args:
            content (str): 文章HTML内容
            title (str): 文章标题（可选）
            url (str): 文章URL（可选）

        Returns:
            Optional[str]: 翻译后保存的文件路径
        """
        context = f"文章标题: {title}, URL: {url}" if title or url else ""
        return await self.translate_html(content, context)


# 便捷函数
async def translate_html_content(html_content: str, context: str = "") -> Optional[str]:
    """便捷函数：翻译HTML内容，返回保存的文件路径"""
    translator = HTMLTranslator()
    return await translator.translate_html(html_content, context)


async def translate_html_file(input_file: str, force_translate: bool = False) -> Optional[str]:
    """便捷函数：翻译HTML文件，保持嵌套目录结构保存到output/trans目录"""
    try:
        input_path = Path(input_file)
        trans_dir = Path(TRANS_DIR)
        origin_dir = Path(OUTPUT_DIR) / "origin"

        # 保持嵌套目录结构
        try:
            rel_path = input_path.relative_to(origin_dir)
            target_file = trans_dir / rel_path
        except ValueError:
            target_file = trans_dir / input_path.name

        # 检查目标文件是否已存在
        if target_file.exists() and not force_translate:
            logging.getLogger(__name__).info(f"⏭️  跳过已翻译文件: {target_file.relative_to(trans_dir)}")
            return str(target_file)

        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 翻译内容并保存
        translator = HTMLTranslator()
        saved_path = await translator.translate_html(html_content, f"文件: {input_file}", force_translate)

        return saved_path

    except Exception as e:
        logging.getLogger(__name__).error(f"翻译文件失败: {str(e)}")
        return None


async def test_batch():
    """批量翻译output/origin目录下的所有HTML文件"""
    print("=== 批量翻译HTML文件 ===")

    origin_dir = Path("output/origin")
    trans_dir = Path(TRANS_DIR)

    if not origin_dir.exists():
        print(f"❌ 源目录不存在: {origin_dir}")
        return

    # 递归获取所有HTML文件
    html_files = list(origin_dir.glob("**/*.html"))

    if not html_files:
        print("❌ 未找到HTML文件")
        return

    print(f"📁 找到 {len(html_files)} 个HTML文件")

    translator = HTMLTranslator()
    success_count = 0
    skip_count = 0
    error_count = 0

    for html_file in html_files:
        try:
            # 保持嵌套目录结构
            rel_path = html_file.relative_to(origin_dir)
            target_file = trans_dir / rel_path
            if target_file.exists():
                print(f"⏭️  跳过已翻译文件: {rel_path}")
                skip_count += 1
                continue

            print(f"\n🔄 开始翻译: {rel_path}")

            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()

            saved_path = await translator.translate_html(html_content, f"文件: {html_file}")

            if saved_path:
                print(f"✅ 翻译成功: {rel_path}")
                success_count += 1
            else:
                print(f"❌ 翻译失败: {rel_path}")
                error_count += 1

        except Exception as e:
            print(f"❌ 处理文件 {html_file} 时出错: {str(e)}")
            error_count += 1

    print(f"\n📊 批量翻译完成:")
    print(f"   ✅ 成功翻译: {success_count} 个文件")
    print(f"   ⏭️  跳过文件: {skip_count} 个文件")
    print(f"   ❌ 翻译失败: {error_count} 个文件")
    print(f"   📁 总文件数: {len(html_files)} 个文件")


async def main():
    """主测试函数"""
    from config.logging_config import setup_logging

    setup_logging('INFO')

    print("HTML翻译工具")
    print("=" * 50)

    await test_batch()

    print("\n完成!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
