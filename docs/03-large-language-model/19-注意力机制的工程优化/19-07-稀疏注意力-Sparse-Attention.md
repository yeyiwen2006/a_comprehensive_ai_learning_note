---
title: "19.7 稀疏注意力（Sparse Attention）"
source_docx: "第3部分 大语言模型/19.注意力机制的工程优化/19.7 稀疏注意力（Sparse Attention）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 19.7 稀疏注意力（Sparse Attention）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

## 一、核心思想：认为并非所有 token 对之间都需要进行交互。通过引入结构性稀疏模式，只计算注意力矩阵中一部分重要的元素，将复杂度从O(n^2) 降低到 O(n*sqrt(n))或O(nlogn)。

## 二、典型代表

Blockwise Attention：将序列分块，只在块内或特定的块之间计算注意力。

Sliding Window Attention（滑动窗口注意力）：每个 token 只关注其前后一定窗口大小内的邻居 token。这在类似BERT这样的编码器中很常见。

Dilated Attention：类似于空洞卷积，在滑动窗口的基础上进行跳跃，以扩大感受野。

Global + Local Attention：指定少数 token（如 <s>）拥有全局注意力，可以关注所有 token，而其他 token 只进行局部注意力。

应用：Longformer、BigBird 等模型就采用了这种思想，能够处理极长文档。

## 三、DSA（Dynamic Sparse Attention，DeepSeek-V3.2，2025）

1.核心思想：“先粗筛，后细算”

> [图片内容待重建：img-3603ece21575-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
2.推理工作流

> [图片内容待重建：img-3603ece21575-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-3603ece21575-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-3603ece21575-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-3603ece21575-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
3.训练方法

（1）Lightning Indexer的训练目标

由于Top-K操作本身是不可导的（即无法直接通过Top-K选择反向传播主模型的预测误差来更新索引器），DeepSeek为Lightning Indexer设计了独立的监督信号。

Lightning Indexer被训练来预测对于每个token的Query和每个token的Key之间的注意力权重，训练目标是模仿原始全注意力（Dense Attention）的权重分布（准确说是所有注意力头的权重的平均值的分布）。

损失函数是n个KL散度的和：对于任意第i个token，它对第j个token的注意力分数（j=1,2,...,n）构成概率分布p(j|i)，我们计算p_Indexer(j|i)相对于p_Dense(j|i)的KL散度，再对i=1,2,...,n累加。

（2）整体训练步骤

第一步：在全注意力（Dense Attention）下，训练主模型。

第二步：冻结主模型，保持全注意力（Dense Attention）开启，初始化训练Lightning Indexer使之与主模型的注意力分布对齐。

第三步：开启稀疏化（Top-K Selection），同步用各自的损失函数训练主模型和Lightning Indexer。

## 参考文献

暂无已核验参考文献。
