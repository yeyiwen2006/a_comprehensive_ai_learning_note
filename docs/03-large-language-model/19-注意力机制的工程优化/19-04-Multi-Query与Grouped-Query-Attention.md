---
title: "19.4 Multi-Query与Grouped-Query Attention"
source_docx: "第3部分 大语言模型/19.注意力机制的工程优化/19.4 Multi-Query与Grouped-Query Attention.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 19.4 Multi-Query与Grouped-Query Attention

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

## 一、MQA的基本思想

在MHA中，随着序列变长，显存占用巨大。内存带宽（Memory Bandwidth）成为核心限制。推理过程主要是矩阵乘向量（GEMV），是典型的内存带宽受限操作。GPU 花在“搬运 KV Cache 数据”上的时间远多于“计算”的时间。MQA（Multi-Query Attention）的核心思想非常简单粗暴：所有的 Query 头之间共享同一组 Key 和 Value 头。

MHA（Multi-Head）：H个 Query Heads，H个Key Heads，H个 Value Heads

MQA（Multi-Query）：H个 Query Heads，1个 Key Head，1个 Value Head

> [图片内容待重建：img-2f70b403483f-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
计算第i个头的注意力分数时：

> [图片内容待重建：img-2f70b403483f-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-2f70b403483f-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 二、GQA（Grouped-Query Attention）

MQA提高了速度，却容易影响生成质量。为了平衡MHA的高质量和MQA的高速度，现代模型引入了GQA，将Query头分组，每组共享一个Key/Value 头。

如：8个Query头，分为4组，每组 2 个Query头共享1个KV头。

KV Cache大小是MHA的1/2，是MQA的2倍。

效果：速度接近 MQA，质量接近 MHA。

## 参考文献与引用线索

> 本节由脚本自动检索正文中的引用线索，可能不完整；未能确定来源的位置会在下方标为待补引用。

### 待补引用或版权检查

- [待补引用] 本文含 Word 内嵌图片；开源版未上传图片。若图片来自教材、论文或技术报告，建议人工确认授权、补充来源或重画。
- [待补引用] 未自动检索到明确参考文献线索，建议人工补充可追溯来源。
