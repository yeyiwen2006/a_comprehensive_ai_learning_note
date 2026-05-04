---
title: "30.3 Diffusion U-Net"
source_docx: "第5部分 世界模型、多模态生成与具身智能/30.扩散模型与流匹配模型的原理和架构/30.3 Diffusion U-Net.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 30.3 Diffusion U-Net

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

U-Net采用卷积神经网络，前半部分类似Encoder，通过池化或步长＞1的卷积，使空间尺寸数不断减小、通道数不断增大；后半部分类似Decoder，空间尺寸数不断增大、通道数不断减小，主要有两种实现方法：

> [图片内容待重建：img-aa1f6c939310-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-aa1f6c939310-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-aa1f6c939310-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
但U-Net的可扩展性一般，且与当前基于Transformer的大模型架构不兼容。

## 参考文献

暂无已核验参考文献。
