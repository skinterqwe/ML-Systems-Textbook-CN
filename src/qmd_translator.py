"""
QMD 翻译模块
使用 Gemini API 翻译 .qmd（Quarto Markdown）文件，保护特殊元素不被翻译。

项目：ML Systems Textbook 中文翻译
"""

import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gemini_api import GeminiAPI
from qmd_chunker import QMDChunker
from config.settings import Config


class QMDTranslator:
    """QMD 文件翻译器，保护 LaTeX/代码/数学公式等特殊元素。"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gemini_api = GeminiAPI()
        self.chunker = QMDChunker()

        # 占位符计数器和存储
        self._counter = 0
        self._stores: Dict[str, Dict[str, str]] = {}

        # 专业术语对照表（230+条）
        self.terminology = self._build_terminology()

    def _build_terminology(self) -> Dict[str, str]:
        """构建扩展的术语对照表。"""
        return {
            # --- 基础概念 ---
            "Machine Learning": "机器学习",
            "Deep Learning": "深度学习",
            "Neural Network": "神经网络",
            "Artificial Intelligence": "人工智能",
            "Supervised Learning": "监督学习",
            "Unsupervised Learning": "无监督学习",
            "Reinforcement Learning": "强化学习",
            "Transfer Learning": "迁移学习",
            "Federated Learning": "联邦学习",
            "Online Learning": "在线学习",
            # --- 模型架构 ---
            "Transformer": "Transformer",
            "attention": "注意力",
            "self-attention": "自注意力",
            "multi-head attention": "多头注意力",
            "Feed-Forward Network": "前馈网络",
            "embedding": "嵌入",
            "tokenization": "分词",
            "tokenizer": "分词器",
            "BPE": "BPE",
            "byte pair encoding": "字节对编码",
            "Convolutional Neural Network": "卷积神经网络",
            "CNN": "CNN",
            "Recurrent Neural Network": "循环神经网络",
            "RNN": "RNN",
            "LSTM": "LSTM",
            "Generative Adversarial Network": "生成对抗网络",
            "GAN": "GAN",
            "Variational Autoencoder": "变分自编码器",
            "VAE": "VAE",
            "Diffusion Model": "扩散模型",
            "Large Language Model": "大语言模型",
            "LLM": "LLM",
            "foundation model": "基础模型",
            # --- 训练相关 ---
            "training": "训练",
            "inference": "推理",
            "forward pass": "前向传播",
            "backward pass": "反向传播",
            "backpropagation": "反向传播",
            "gradient": "梯度",
            "gradient descent": "梯度下降",
            "stochastic gradient descent": "随机梯度下降",
            "SGD": "SGD",
            "learning rate": "学习率",
            "learning rate schedule": "学习率调度",
            "batch size": "批大小",
            "epoch": "轮次",
            "loss function": "损失函数",
            "cross-entropy": "交叉熵",
            "overfitting": "过拟合",
            "underfitting": "欠拟合",
            "regularization": "正则化",
            "dropout": "Dropout",
            "batch normalization": "批归一化",
            "layer normalization": "层归一化",
            "weight decay": "权重衰减",
            "data augmentation": "数据增强",
            "gradient accumulation": "梯度累积",
            "mixed precision": "混合精度",
            "activation checkpointing": "激活检查点",
            "loss landscape": "损失景观",
            "convergence": "收敛",
            "optimizer": "优化器",
            "Adam": "Adam",
            "AdamW": "AdamW",
            "momentum": "动量",
            # --- 模型压缩 ---
            "Model Compression": "模型压缩",
            "pruning": "剪枝",
            "quantization": "量化",
            "knowledge distillation": "知识蒸馏",
            "distillation": "蒸馏",
            "sparsity": "稀疏性",
            "structured pruning": "结构化剪枝",
            "unstructured pruning": "非结构化剪枝",
            "weight sharing": "权重共享",
            "low-rank decomposition": "低秩分解",
            "neural architecture search": "神经架构搜索",
            "NAS": "NAS",
            "operator fusion": "算子融合",
            "model serving": "模型服务化",
            "batching": "批处理",
            "dynamic batching": "动态批处理",
            # --- 量化相关 ---
            "FP32": "FP32",
            "FP16": "FP16",
            "BF16": "BF16",
            "bfloat16": "bfloat16",
            "INT8": "INT8",
            "INT4": "INT4",
            "post-training quantization": "训练后量化",
            "quantization-aware training": "量化感知训练",
            "QAT": "QAT",
            "PTQ": "PTQ",
            "calibration": "校准",
            "dynamic range": "动态范围",
            "fixed-point": "定点",
            "floating-point": "浮点",
            # --- 硬件与系统 ---
            "GPU": "GPU",
            "TPU": "TPU",
            "CPU": "CPU",
            "FPGA": "FPGA",
            "ASIC": "ASIC",
            "CUDA": "CUDA",
            "CUDA Core": "CUDA Core",
            "TensorCore": "TensorCore",
            "systolic array": "脉动阵列",
            "HBM": "HBM",
            "High Bandwidth Memory": "高带宽内存",
            "SRAM": "SRAM",
            "DRAM": "DRAM",
            "NVLink": "NVLink",
            "PCIe": "PCIe",
            "bandwidth": "带宽",
            "memory bandwidth": "内存带宽",
            "latency": "延迟",
            "throughput": "吞吐量",
            "utilization": "利用率",
            "arithmetic intensity": "算术强度",
            "roofline model": "屋顶线模型",
            "roofline": "屋顶线",
            "FLOPs": "FLOPs",
            "MACs": "MACs",
            "multiply-accumulate": "乘累加",
            "MXU": "MXU",
            "VPU": "VPU",
            "VMEM": "VMEM",
            "ICI": "ICI",
            "DCN": "DCN",
            "on-chip memory": "片上内存",
            "off-chip memory": "片外内存",
            # --- 并行与分布式 ---
            "parallelism": "并行性",
            "data parallelism": "数据并行",
            "model parallelism": "模型并行",
            "pipeline parallelism": "流水线并行",
            "tensor parallelism": "张量并行",
            "sharding": "分片",
            "distributed training": "分布式训练",
            "All-Reduce": "All-Reduce",
            "parameter server": "参数服务器",
            "synchronization": "同步",
            "asynchronous": "异步",
            # --- 框架与工具 ---
            "JAX": "JAX",
            "PyTorch": "PyTorch",
            "TensorFlow": "TensorFlow",
            "ONNX": "ONNX",
            "TensorRT": "TensorRT",
            "XLA": "XLA",
            "compiler": "编译器",
            "graph optimization": "图优化",
            "intermediate representation": "中间表示",
            "IR": "IR",
            "JIT": "JIT",
            "just-in-time compilation": "即时编译",
            # --- 数据相关 ---
            "dataset": "数据集",
            "data pipeline": "数据管道",
            "feature engineering": "特征工程",
            "feature store": "特征存储",
            "data preprocessing": "数据预处理",
            "data cleaning": "数据清洗",
            "label": "标签",
            "annotation": "标注",
            "ground truth": "真值",
            "benchmark": "基准测试",
            # --- 部署与运维 ---
            "deployment": "部署",
            "serving": "服务化",
            "edge computing": "边缘计算",
            "edge device": "边缘设备",
            "mobile device": "移动设备",
            "TinyML": "TinyML",
            "microcontroller": "微控制器",
            "MCU": "MCU",
            "model server": "模型服务器",
            "API": "API",
            "REST": "REST",
            "gRPC": "gRPC",
            "containerization": "容器化",
            "Docker": "Docker",
            "Kubernetes": "Kubernetes",
            "MLOps": "MLOps",
            "CI/CD": "CI/CD",
            "A/B testing": "A/B 测试",
            "canary deployment": "金丝雀部署",
            "blue-green deployment": "蓝绿部署",
            "monitoring": "监控",
            "observability": "可观测性",
            "drift detection": "漂移检测",
            # --- 评估指标 ---
            "accuracy": "准确率",
            "precision": "精确率",
            "recall": "召回率",
            "F1 score": "F1 分数",
            "AUC": "AUC",
            "ROC": "ROC",
            "perplexity": "困惑度",
            "BLEU": "BLEU",
            "throughput": "吞吐量",
            "latency": "延迟",
            "power consumption": "功耗",
            "energy efficiency": "能效",
            "TOPS": "TOPS",
            "TOPS/W": "TOPS/W",
            # --- 安全与伦理 ---
            "adversarial attack": "对抗攻击",
            "adversarial example": "对抗样本",
            "robustness": "鲁棒性",
            "fairness": "公平性",
            "bias": "偏差",
            "explainability": "可解释性",
            "interpretability": "可解释性",
            "privacy": "隐私",
            "differential privacy": "差分隐私",
            "Responsible AI": "负责任的AI",
            "AI safety": "AI安全",
            "alignment": "对齐",
            "hallucination": "幻觉",
            "Red Teaming": "红队测试",
            # --- 其他常见术语 ---
            "scaling": "扩展",
            "scaling law": "缩放定律",
            "emergent ability": "涌现能力",
            "in-context learning": "上下文学习",
            "few-shot": "少样本",
            "zero-shot": "零样本",
            "chain-of-thought": "思维链",
            "prompt engineering": "提示工程",
            "fine-tuning": "微调",
            "pre-training": "预训练",
            "checkpoint": "检查点",
            "artifact": "产物",
            "pipeline": "流水线",
            "workflow": "工作流",
            "dependency": "依赖",
            "bottleneck": "瓶颈",
            "trade-off": "权衡",
            "optimization": "优化",
            "performance": "性能",
            "efficiency": "效率",
            "scalability": "可扩展性",
            "reliability": "可靠性",
            "availability": "可用性",
            # --- QMD 书籍特有 ---
            "Footnotes": "脚注",
            "References": "参考文献",
            "Citation": "引用",
            "Authors": "作者",
            "Published": "发布日期",
            "Contents": "目录",
            "Chapter": "章节",
            "Figure": "图",
            "Table": "表",
            "Equation": "公式",
            "Appendix": "附录",
            "Glossary": "术语表",
            "Index": "索引",
            "Preface": "前言",
            "Foreword": "序言",
            "Acknowledgments": "致谢",
            "Learning Objectives": "学习目标",
            "Key Takeaways": "关键要点",
            "Summary": "总结",
            "Discussion": "讨论",
            "Exercises": "练习",
            "Quiz": "测验",
            "self-check": "自检",
        }

    def _next_placeholder(self, prefix: str) -> str:
        """生成下一个占位符。使用特殊分隔符避免短名是长名的前缀。"""
        self._counter += 1
        # 使用 __ 分隔前缀和序号，并在末尾加 __ 标记，避免前缀冲突
        placeholder = f"__{prefix}_{self._counter}__"
        return placeholder

    def protect_all(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        按顺序保护所有特殊元素。

        处理顺序：
        1. 代码块（```{python}...``` / ```{=latex}...``` / ```{.tikz}...```）
        2. 行间数学（$$...$$）
        3. 内联数学（$...$）
        4. 内联代码（`...`）
        5. 跨引用（@sec- / @fig- / @tbl- / [@...]）
        6. LaTeX 布局命令
        7. HTML 注释（<!-- -->）
        8. Quarto 指令标记（:::）
        9. fig-alt 属性值
        10. \\index{} 命令中的术语

        Returns:
            (protected_content, store): 占位符 -> 原始内容的映射
        """
        store: Dict[str, str] = {}
        self._counter = 0

        # 1. 代码块：```{...} ... ```
        content = self._protect_code_blocks(content, store)

        # 2. \index{...} 命令（必须在数学公式前，因为 \index{} 内可能含 $...$）
        content = self._protect_regex(content, store, r'\\index\{[^}]+\}', 'IX_PH')

        # 3. Quarto 指令标记（::: 行）— 在数学公式前，避免嵌套
        content = self._protect_quarto_directives(content, store)

        # 4. 行间数学 $$...$$（$$ 必须独占一行或前后有空白，不能是行内 $$）
        content = self._protect_block_math(content, store)

        # 5. 内联数学 $...$ （不能匹配 $$，不能跨段落）
        content = self._protect_inline_math(content, store)

        # 6. 内联代码 `...`
        content = self._protect_inline_code(content, store)

        # 7. 跨引用（匹配到双下划线前停止，避免吃掉占位符名）
        content = self._protect_regex(content, store, r'@(?:sec|fig|tbl|eq|lst)-[\w\-]+?(?=__|[\s,.;:!?}\)\]]|$)', 'XR_PH')
        content = self._protect_regex(content, store, r'\[@[^\]]+\]', 'XR_PH')

        # 8. LaTeX 布局命令
        content = self._protect_latex_commands(content, store)

        # 9. HTML 注释
        content = self._protect_regex(content, store, r'<!--[\s\S]*?-->', 'CM_PH')

        self.logger.info(f"保护完成: 生成 {len(store)} 个占位符")
        return content, store

    def restore_all(self, content: str, store: Dict[str, str]) -> str:
        """
        恢复所有占位符为原始内容。
        使用 while 循环递归恢复，避免嵌套结构还原错乱。
        同时修正大模型引入的多余空格。

        Args:
            content: 包含占位符的翻译后内容
            store: 占位符 -> 原始内容的映射

        Returns:
            恢复后的内容
        """
        # 清理大模型可能在占位符两侧添加的无效空格
        # 注意：不要删除 _ 和占位符之间的空格（_ 可能是 Markdown 斜体标记）
        content = re.sub(r'(?<=[^\s_])\s+(__[A-Z_]+_PH_\d+__)', r'\1', content)
        content = re.sub(r'(__[A-Z_]+_PH_\d+__)\s+(?=[^\s_])', r'\1', content)

        pattern = re.compile(r'__[A-Z_]+_PH_\d+__')
        
        while True:
            matches = set(pattern.findall(content))
            if not matches:
                break
            
            replaced_any = False
            for match in matches:
                if match in store:
                    content = content.replace(match, store[match])
                    replaced_any = True
            
            # 防止死循环（如果正则匹配出异常格式但store中没有）
            if not replaced_any:
                self.logger.warning(f"发现无法恢复的悬空占位符: {matches - set(store.keys())}")
                break

        return content

    def _protect_block_math(self, content: str, store: Dict[str, str]) -> str:
        """
        保护行间数学 $$...$$。
        $$ 必须在行首（或前面只有空白）或行尾（或后面只有空白/标记）。
        """
        lines = content.split('\n')
        result_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检查是否以 $$ 开头（行首 $$）
            if stripped.startswith('$$'):
                # 情况1: 单行 $$...$$（如 $$ formula $$ 或 $$ formula $$ {#eq-xxx}）
                # 检查行中间是否有另一个 $$
                rest = stripped[2:]  # 去掉开头的 $$
                close_pos = rest.find('$$')
                if close_pos >= 0:
                    # 单行 $$...$$ 块
                    placeholder = self._next_placeholder('MATH_D_PH')
                    store[placeholder] = line
                    result_lines.append(placeholder)
                    i += 1
                    continue

                # 情况2: 多行 $$...$$（$$ 独占一行或 $$ 后跟标记如 {#eq-xxx}）
                if stripped == '$$' or stripped.startswith('$$ '):
                    block_lines = [line]
                    i += 1
                    while i < len(lines):
                        block_lines.append(lines[i])
                        s = lines[i].strip()
                        if s == '$$' or s.startswith('$$ '):
                            break
                        i += 1
                    placeholder = self._next_placeholder('MATH_D_PH')
                    store[placeholder] = '\n'.join(block_lines)
                    result_lines.append(placeholder)
                    i += 1
                    continue

            result_lines.append(line)
            i += 1

        return '\n'.join(result_lines)

    def _protect_code_blocks(self, content: str, store: Dict[str, str]) -> str:
        """保护代码块（含裸 ``` 无语言标记的代码块）。"""
        # 先保护有语言标记的：```{python} / ```{.tikz} / ```{=latex} 等
        pattern_tagged = r'(```\{[^}]*\}\n[\s\S]*?```)'
        content = re.sub(pattern_tagged, self._make_replacer(store), content)

        # 再保护裸代码块（无语言标记）：独立行的 ``` 开始到下一个 ``` 结束
        pattern_bare = r'(^```\n[\s\S]*?^```$)'
        content = re.sub(pattern_bare, self._make_replacer(store), content, flags=re.MULTILINE)

        return content

    def _make_replacer(self, store):
        """创建占位符替换函数。"""
        def replacer(match):
            placeholder = self._next_placeholder('CODE_PH')
            store[placeholder] = match.group(1)
            return placeholder
        return replacer

    def _protect_inline_math(self, content: str, store: Dict[str, str]) -> str:
        """
        保护内联数学 $...$，不匹配 $$，不能跨段落，不能跨越占位符。
        """
        # 占位符格式为 __PREFIX_N__，检测 __ 开头
        def _at_placeholder(pos):
            """检查 pos 位置是否是占位符开头。"""
            if content[pos:pos + 2] != '__':
                return False
            # 找到下一个 __ 结束
            end = content.find('__', pos + 2)
            if end == -1:
                return False
            # 检查中间内容是否是有效的占位符格式
            inner = content[pos + 2:end]
            return '_' in inner and all(c.isalnum() or c == '_' for c in inner)

        result = []
        i = 0
        while i < len(content):
            # 跳过占位符（格式 __PREFIX_N__）
            if _at_placeholder(i):
                end = content.find('__', i + 2) + 2
                result.append(content[i:end])
                i = end
                continue

            # 跳过 $$
            if content[i:i + 2] == '$$':
                result.append('$$')
                i += 2
                continue

            # 检测 $ 开始的内联数学
            if content[i] == '$':
                # 前一个字符不能是 \（转义）
                if i > 0 and content[i - 1] == '\\':
                    result.append('$')
                    i += 1
                    continue

                # 找匹配的闭合 $（不能跨空行，不能跨越占位符）
                j = i + 1
                found = False
                while j < len(content):
                    # 遇到连续两个空行（段落边界），停止匹配
                    if content[j] == '\n' and j + 1 < len(content) and content[j + 1] == '\n':
                        break
                    # 遇到占位符，停止匹配
                    if _at_placeholder(j):
                        break
                    if content[j] == '$' and j > i + 1:
                        # 确保不是 $$ 的一部分
                        if content[j - 1] != '\\':
                            math_content = content[i:j + 1]
                            placeholder = self._next_placeholder('MATH_I_PH')
                            store[placeholder] = math_content
                            result.append(placeholder)
                            i = j + 1
                            found = True
                            break
                    j += 1

                if found:
                    continue

            result.append(content[i])
            i += 1

        return ''.join(result)

    def _protect_inline_code(self, content: str, store: Dict[str, str]) -> str:
        """
        保护内联代码 `...`。
        特别处理 ``{python}...`` 形式的 Quarto 内联代码。
        """
        # 先处理 ``{python}...`` 形式（双反引号包裹）
        content = self._protect_regex(content, store, r'``\{[^}]*\}[^`]*``', 'IC_PH')

        # 再处理普通内联代码 `...`
        # 不匹配已经被保护的占位符（占位符格式 __...__）
        def inline_code_replacer(match):
            text = match.group(0)
            # 跳过包含占位符的匹配
            if '__' in text and any(f'__{p}_' in text for p in
                                     ('CODE', 'MATH', 'QD', 'IX', 'IC', 'XR', 'LX', 'CM')):
                return text
            placeholder = self._next_placeholder('IC_PH')
            store[placeholder] = text
            return placeholder

        # 匹配 `...`，不匹配 ``（双反引号）
        content = re.sub(r'(?<!`)`(?!`)[^`]+(?!`)`(?!`)', inline_code_replacer, content)

        return content

    def _protect_latex_commands(self, content: str, store: Dict[str, str]) -> str:
        """保护 LaTeX 布局命令（\\chapterminitoc, \\noindent, \\newpage 等）。"""
        # 匹配独立的 LaTeX 命令（不是 \index{} 或 \begin/\end 环境）
        latex_commands = [
            r'\\chapterminitoc',
            r'\\noindent',
            r'\\newpage',
            r'\\clearpage',
            r'\\tableofcontents',
            r'\\listoffigures',
            r'\\listoftables',
            r'\\maketitle',
            r'\\thispagestyle\{[^}]*\}',
            r'\\vspace\*?\{[^}]*\}',
            r'\\hspace\*?\{[^}]*\}',
        ]

        for cmd_pattern in latex_commands:
            def replacer(match, _store=store):
                placeholder = self._next_placeholder('LX_PH')
                _store[placeholder] = match.group(0)
                return placeholder
            content = re.sub(cmd_pattern, replacer, content)

        return content

    def _protect_quarto_directives(self, content: str, store: Dict[str, str]) -> str:
        """
        保护 Quarto 指令标记（::: 行）。
        ::: 可能是开头（::: {attrs}）或结尾（:::），需要保持配对。
        title="..." 属性值不保护，以便被翻译。
        """
        def replacer(match):
            line = match.group(0)
            # 检查是否有 title="..." 属性
            title_match = re.search(r'title="([^"]*)"', line)
            if title_match:
                title_text = title_match.group(1)
                # 将 title 值留在引号中，其余部分用占位符保护
                # 例如：::: {.callout-tip title="Learning Objectives"}
                # 变为：__QD_PH_1__"Learning Objectives"__QD_PH_2__
                # store: __QD_PH_1__ -> ::: {.callout-tip title=
                #        __QD_PH_2__ -> }
                before_title = line[:title_match.start()] + 'title='  # "::: {.callout-tip title="
                after_title = line[title_match.end():]  # "}"
                ph_before = self._next_placeholder('QD_PH')
                store[ph_before] = before_title
                ph_after = self._next_placeholder('QD_PH')
                store[ph_after] = after_title
                # 返回：占位符 + "title原文" + 占位符
                return ph_before + '"' + title_text + '"' + ph_after
            else:
                placeholder = self._next_placeholder('QD_PH')
                store[placeholder] = line
                return placeholder

        # 匹配行首的 ::: 开头或结尾
        content = re.sub(r'^\s*:{3,}.*$', replacer, content, flags=re.MULTILINE)

        return content

    def _fix_quarto_newlines(self, content: str) -> str:
        """
        修复翻译后 Quarto 指令的换行问题。
        Gemini 可能将独立行的 ::: 与其他内容合并到同一行。
        Quarto 要求 ::: fence div 前后都有空行才能正确解析。
        """
        for _ in range(3):
            # --- 处理 ::: {attrs} 开启标记 ---

            # 1. ::: {attrs} 前面不是空行 → 插入空行
            content = re.sub(r'([^\n])(\n)(:::\s*\{[^}]*\})', r'\1\n\n\3', content)

            # 2. ::: {attrs} 前面没有换行 → 插入空行
            content = re.sub(r'([^\n])(:::\s*\{[^}]*\})', r'\1\n\n\2', content)

            # 3. ::: {attrs} 后面紧跟非空白内容 → 在后面插入换行
            content = re.sub(r'(:::\s*\{[^}]*\})([^\n])', r'\1\n\2', content)

            # 4. ::: {attrs} 后面紧跟换行但不是空行 → 插入空行
            content = re.sub(r'(:::\s*\{[^}]*\})\n([^\n])', r'\1\n\n\2', content)

            # --- 处理单独的 ::: 闭合标记 ---

            # 5. ::: 闭合标记前面不是空行 → 插入空行
            content = re.sub(r'([^\n])(\n):::(\s*\n)', r'\1\n\n:::\3', content)

            # 6. ::: 闭合标记前面没有换行 → 插入空行
            #    如 '文本。:::\n' → '文本。\n\n:::\n'
            content = re.sub(r'([^\n]):::(\s*\n)', r'\1\n\n:::\2', content)

            # 7. ::: 闭合标记后面紧跟非空白内容（无换行）→ 把 ::: 拆出来
            #    如 '文本。:::下一段' → '文本。\n\n:::\n\n下一段'
            content = re.sub(r'([^\n]):::([^\n\s])', r'\1\n\n:::\n\n\2', content)

            # 7b. 行首 ::: 后紧跟非空白内容（无换行）→ 把 ::: 拆出来
            #     如 '\n:::中文文本' → '\n:::\n\n中文文本'
            content = re.sub(r'(^:::)([^\n\s{])', r'\1\n\n\2', content, flags=re.MULTILINE)

            # 8. ::: 闭合标记后面紧跟换行但不是空行 → 插入空行
            content = re.sub(r'(:::)(\n)([^\n\s])', r'\1\n\n\3', content)

        return content

    def _protect_regex(self, content: str, store: Dict[str, str],
                       pattern: str, prefix: str) -> str:
        """通用正则保护方法。"""
        def replacer(match):
            placeholder = self._next_placeholder(prefix)
            store[placeholder] = match.group(0)
            return placeholder

        return re.sub(pattern, replacer, content)

    def _build_translation_prompt(self, content: str) -> str:
        """构建翻译提示词。"""
        terminology_list = "\n".join(
            [f"- {en}: {zh}" for en, zh in
             sorted(self.terminology.items(), key=lambda x: len(x[0]), reverse=True)[:50]]
        )

        return f"""你是一个专业的技术文档翻译专家，专门翻译机器学习系统相关的技术教材。

请将以下 Quarto Markdown 内容从英文翻译成中文。

【格式规则】
1. 这是 Quarto Markdown 格式，包含 Markdown 语法和 Quarto 指令
2. 所有占位符（格式为 __XX_PH_N__，如 __CODE_PH_0__, __MATH_D_PH_3__, __QD_PH_5__, __IC_PH_12__, __IX_PH_6__）必须原样保留，不能修改、拆分、翻译或在占位符内部及两侧添加任何字符（包括空格）
3. Markdown 标记（#, ##, *, **, -, >, |）保持不变
4. 图片路径保持不变
5. 表格格式保持不变
6. 保持原文的换行结构：如果原文中占位符前后有换行，译文中也必须保留相同的换行。不要将多个占位符合并到同一行
7. 【极其重要】__QD_PH_N__ 占位符（对应 Quarto 的 ::: 标记）必须独占一行！不允许将 __QD_PH_N__ 占位符与段落文本合并到同一行。原文中 __QD_PH_N__ 如果独占一行（前后有换行），译文中也必须独占一行。例如：
   ✅ 正确：
   这是一段文字。

   __QD_PH_1__

   下一段文字。
   ❌ 错误：
   这是一段文字。__QD_PH_1__下一段文字。

【翻译规则】
1. 专业术语使用术语对照表：
{terminology_list}

2. 准确传达技术含义，保持中文流畅自然
3. 斜体、加粗文本的内容需要翻译，标记符号保持不变
4. fig-alt 属性中的图片描述文本需要翻译
5. 不翻译：占位符、URL、引用标记（如 @sec-xxx、[@xxx]）、标签 ID
6. 如果原文中两个占位符之间有换行（如 __QD_PH_1__\\n\\n__QD_PH_2__），译文中必须保持完全相同的换行结构
7. 当看到 __QD_PH_N__"英文文本"__QD_PH_M__ 的模式时（即两个 __QD_PH__ 占位符之间夹着引号包裹的文本），引号内的文本需要翻译，但引号和占位符必须原样保留
8. 代码块（用 \`\`\` 包裹的内容）中的自然语言描述文本需要翻译成中文。只有真正的代码（如 Python、JavaScript、SQL 等编程语言）和数学公式保持英文。示例性文字、伪代码中的英文描述、对话式内容都应翻译。代码块的 \`\`\` 标记保持不变。

【示例】
输入：
In this chapter, we discuss __IC_PH_1__ and __IC_PH_2__. A typical loss function is __MATH_I_PH_1__, defined as:
__MATH_D_PH_1__
__QD_PH_1__
See @sec-optimization for details.
__QD_PH_2__

输出：
在本章中，我们讨论 __IC_PH_1__ 和 __IC_PH_2__。一个典型的损失函数是 __MATH_I_PH_1__，定义如下：
__MATH_D_PH_1__
__QD_PH_1__
有关详细信息，请参阅 @sec-optimization。
__QD_PH_2__

【内容】
{content}

请直接返回翻译后的完整内容。"""

    def translate_chunk(self, content: str, context_prefix: str = "") -> Optional[str]:
        """
        对单个块执行：保护 → Gemini 翻译 → 恢复。

        Args:
            content: 要翻译的 QMD 内容块
            context_prefix: 上下文前缀（用于日志）

        Returns:
            翻译后的内容，失败返回 None
        """
        if not content.strip():
            return content

        try:
            # 1. 保护特殊元素
            protected, store = self.protect_all(content)

            # 2. 构建提示词
            prompt = self._build_translation_prompt(protected)

            # 3. 调用 Gemini API
            start_time = time.time()
            translated = self.gemini_api.generate_text(prompt)
            elapsed = time.time() - start_time

            if not translated:
                self.logger.error(f"Gemini API 返回空结果 {context_prefix}")
                return None

            # 4. 恢复占位符
            restored = self.restore_all(translated, store)

            # 4.5 修复 Quarto 指令的换行
            restored = self._fix_quarto_newlines(restored)

            self.logger.info(
                f"翻译完成 {context_prefix}: {len(content)} → {len(restored)} 字符 "
                f"({elapsed:.1f}s)"
            )

            return restored

        except Exception as e:
            self.logger.error(f"翻译失败 {context_prefix}: {e}")
            return None

    def translate_qmd_file(self, file_path: Path, output_path: Path) -> bool:
        """
        翻译完整的 QMD 文件。

        流程：读取 → 分块 → 逐块翻译 → 合并 → 写出

        Args:
            file_path: 输入 QMD 文件路径
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始翻译文件: {file_path.name}")
            start_time = time.time()

            # 读取文件
            content = file_path.read_text(encoding='utf-8')
            self.logger.info(f"文件大小: {len(content):,} 字符, {content.count(chr(10)):,} 行")

            # 分块
            frontmatter, chunks = self.chunker.split(content)
            self.logger.info(f"分块结果: frontmatter + {len(chunks)} 个块")

            # 逐块翻译
            translated_chunks: List[str] = []
            for i, chunk in enumerate(chunks):
                context = f"[{file_path.name}] 块 {i + 1}/{len(chunks)}"
                self.logger.info(f"翻译 {context}")

                translated = self.translate_chunk(chunk, context)
                if translated is None:
                    # 翻译失败，保留原文
                    self.logger.warning(f"块 {i + 1} 翻译失败，保留原文")
                    translated_chunks.append(chunk)
                else:
                    translated_chunks.append(translated)

            # 合并
            result = self.chunker.merge(frontmatter, translated_chunks)

            # 写出
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result, encoding='utf-8')

            elapsed = time.time() - start_time
            self.logger.info(
                f"文件翻译完成: {file_path.name} → {output_path} "
                f"({elapsed:.1f}s, {len(chunks)} 块)"
            )

            return True

        except Exception as e:
            self.logger.error(f"翻译文件失败 {file_path}: {e}")
            return False
