---
title: "11.7 Dueling DQN"
source_docx: "第2部分 强化学习/11.基于价值的强化学习/11.7 Dueling DQN.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 11.7 Dueling DQN

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

DQN中，D是一个同时由状态s和动作a决定的函数。但在某些状态下，智能体只需要知道“现在的环境好不好”（V值），而不关心具体动作的差异；而在需要通过做动作来避险或得分时，才需要关心“哪个动作比平均水平好”（A值）。如果我们将两者分开建模，V(s)专门负责看大局，评估当前环境好不好；A(s, a)专门负责看细节，评估在当前环境下，哪个动作比其他动作好，好多少。这种解耦使得V(s)可以在每一个样本中都被学习更新（因为无论选哪个动作，V(s)都是基础），从而大幅提升了训练效率。

> [图片内容待重建：img-afdddffda4c9-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-afdddffda4c9-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
从而我们把Q函数拆分如下：

> [图片内容待重建：img-afdddffda4c9-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
但问题在于，我们计算和更新的都是Q值，怎么从Q值中求出V和A？

我们可以获取同一个状态s上的所有动作a’（遍历），各个动作Q值的相对大小关系也就是它们的A值相对大小。一个方案是对于给定s，取让Q(s,a’)最大的动作a*，设A(s,a*)=0（最大动作优势值），V(s)=Q(s,a*)，则：

> [图片内容待重建：img-afdddffda4c9-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
另一方案是取所有动作优势值的平均值为0：

> [图片内容待重建：img-afdddffda4c9-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
这样虽然不严格满足贝尔曼最优方程，但在工程实现上更优。原因：

> [图片内容待重建：img-afdddffda4c9-0006] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。

## 参考文献

暂无已核验参考文献。
