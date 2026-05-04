---
title: "27.7 Memory Sparse Attention（论文）"
source_docx: "第4部分 大模型智能体与持续学习/27.基于上下文的持续学习/27.7 Memory Sparse Attention（论文）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 27.7 Memory Sparse Attention（论文）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

Memory Sparse Attention（MSA）是盛大集团研究团队提出的一种长上下文处理方法，将文档检索融入了注意力机制之中。

## 一、核心架构

### （一）基于文档检索的稀疏注意力

> [图片内容待重建：img-b4588b117ec7-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
和RAG的不同点：RAG基于模型无关的语义相似度（例如余弦相似度），这与模型内部进行下一Token预测的生成目标之间存在一条“优化鸿沟”；MSA则内置于模型中，生成Q、K、V所需的W_Q、W_K、W_V矩阵均为模型内置的矩阵，就可以将检索过程转变为可以端到端联合优化的注意力机制。

### （二）双层位置编码

> [图片内容待重建：img-b4588b117ec7-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 二、工作流

### （一）端到端训练阶段

> [图片内容待重建：img-b4588b117ec7-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
### （二）推理阶段

> [图片内容待重建：img-b4588b117ec7-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
由于单次检索准确度不够高，MSA还引入了记忆交错机制：

> [图片内容待重建：img-b4588b117ec7-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 三、内存并行与分层存储

> [图片内容待重建：img-b4588b117ec7-0006] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。

## 参考文献

暂无已核验参考文献。
