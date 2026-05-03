---
title: "5.5 AdamW优化器"
source_docx: "第1部分 深度学习/5.优化算法/5.5 AdamW优化器.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 5.5 AdamW优化器

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

AdamW优化器（Adam with Decoupled Weight Decay）是对Adam优化器的一种改进。

## 一、提出背景：Adam自适应学习率对正则化项的错误缩放

> [图片内容待重建：img-33192d709eee-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-33192d709eee-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
我们需要的是Loss对参数的梯度太大时减小学习率，Loss对参数的梯度太小时增大学习率，而不应该影响正则化项。故需要把正则化项解耦出来。

## 二、AdamW的解决方案

> [图片内容待重建：img-33192d709eee-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
参数更新公式分为两部分，分别为Adam更新方向和独立权重衰减：

> [图片内容待重建：img-33192d709eee-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
权重衰减项直接作用于参数，不再受到学习率的缩放影响。这恢复了SGD中权重衰减的原始物理意义（即每次迭代让权重按比例收缩），使得模型的泛化能力通常优于Adam。

## 参考文献与引用线索

> 本节由脚本自动检索正文中的引用线索，可能不完整；未能确定来源的位置会在下方标为待补引用。

### 待补引用或版权检查

- [待补引用] 本文含 Word 内嵌图片；开源版未上传图片。若图片来自教材、论文或技术报告，建议人工确认授权、补充来源或重画。
- [待补引用] 未自动检索到明确参考文献线索，建议人工补充可追溯来源。
