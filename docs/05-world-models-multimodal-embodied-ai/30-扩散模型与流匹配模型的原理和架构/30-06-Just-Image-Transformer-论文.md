---
title: "30.6 Just Image Transformer（论文）"
source_docx: "第5部分 世界模型、多模态生成与具身智能/30.扩散模型与流匹配模型的原理和架构/30.6 Just Image Transformer（论文）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 30.6 Just Image Transformer（论文）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

## 一、核心思想

> [图片内容待重建：img-a5089c6b0ba4-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 二、模型架构

> [图片内容待重建：img-a5089c6b0ba4-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
唯一新增的模块是在Transformer后加的一个全连接层，把生成的低维嵌入向量映射为高维的图像。这样做有效的原因在于，真实世界的高维图像斑块并不是随机杂乱的，它们具有极强的空间连贯性和规律，因此它们被紧紧约束在一个极低维的“流形”上。Transformer内部的低维隐变量已经足以捕捉这些低维的结构信息，最后的那个全连接层，本质上只是把这个低维结构“旋转”并“映射”回高维空间中对应的流形位置而已。

时间步和Diffusion Transformer一样，通过自适应层归一化的方式注入。

> [图片内容待重建：img-a5089c6b0ba4-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-a5089c6b0ba4-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 三、既然如此，为什么业界仍然使用原始扩散模型？

1.潜在空间已经避免了维度灾难

> [图片内容待重建：img-a5089c6b0ba4-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-a5089c6b0ba4-0006] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
2.动作空间的多样性

> [图片内容待重建：img-a5089c6b0ba4-0007] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-a5089c6b0ba4-0008] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
注意：这里的p(x)不是训练数据的联合概率密度，而是对于新数据本身的概率分布。

3.高噪声条件下的稳定性

> [图片内容待重建：img-a5089c6b0ba4-0009] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-a5089c6b0ba4-0010] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。

## 参考文献

暂无已核验参考文献。
