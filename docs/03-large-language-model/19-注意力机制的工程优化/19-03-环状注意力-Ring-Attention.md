---
title: "19.3 环状注意力（Ring Attention）"
source_docx: "第3部分 大语言模型/19.注意力机制的工程优化/19.3 环状注意力（Ring Attention）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 19.3 环状注意力（Ring Attention）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

Ring Attention（环状注意力）是分布式系统（多GPU/TPU）上的Flash Attention延伸，Google Gemini等模型均运用了此技术。

FlashAttention 解决的是单张显卡内，如何通过分块计算（Tiling）把超长序列塞进有限的 SRAM 中；Ring Attention 解决的是多张显卡间，如何通过分块轮转，把超长序列（比如100万+ Token）塞进集群的显存中，并打破单卡显存的物理上限。

假设你想训练一个上下文长度为1000万的模型。注意力机制要求Q必须和所有的K, V进行交互。即使使用了FlashAttention，单张H100也存不下这么长的KV Cache和中间激活值。这时候需要序列并行（Sequence Parallelism），把长序列切分到N张显卡上。

Ring Attention做法：每张显卡存一个Query块（Q矩阵的若干行，也就是若干个token的Query），让K, V数据块（每个数据块包含矩阵若干行）在显卡之间像“回转寿司”一样，通过高速互连网络流动，每张卡只处理流经它的那一小块数据，算完就传给下一张卡，绝不囤积数据。

> [图片内容待重建：img-009012eb5afc-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
其中计算依赖于Softmax的分块计算性质：

> [图片内容待重建：img-009012eb5afc-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
计算的具体步骤如下：

> [图片内容待重建：img-009012eb5afc-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-009012eb5afc-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
第i张显卡的输出O是一个和Q_i行数相同的矩阵（如果每张显卡只存一个Query向量，则O就是一个向量），是对于每个Query，根据目前已经经过该显卡的K、V得到的对V进行注意力加权的结果。每一轮计算后，更新统计量和输出O：

> [图片内容待重建：img-009012eb5afc-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。

## 参考文献

暂无已核验参考文献。
