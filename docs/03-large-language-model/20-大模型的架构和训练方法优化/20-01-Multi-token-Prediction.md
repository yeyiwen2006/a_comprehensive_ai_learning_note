---
title: "20.1 Multi-token Prediction"
source_docx: "第3部分 大语言模型/20.大模型的架构和训练方法优化/20.1 Multi-token Prediction.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 20.1 Multi-token Prediction

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

## 一、Multi-Token Prediction（MTP）的提出背景

由于LLM的推理是自回归的，每次生成一个token，都要在显存中加载一轮完整的模型参数，导致显存带宽成为推理速度的显著瓶颈。同时，在利用Next token prediction进行训练的过程中，模型只能学习基于当前预测下一个token的质量，而无法拥有更远的“视野”。Multi-Token Prediction（MTP）通过在训练和推理中每一次并行生成多个token，来解决这些问题。

## 二、Blockwise Parallel Decoding

这是Google于2018年提出的范式，也是MTP的初始形态。

1.模型架构

> [图片内容待重建：img-271a2036f5e4-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
如图，主干网络是训练好的多层decode-only的Transformer网络，经过多层前向计算后，最终隐藏层输出h维度（＝embedding维度）的logit。上面接了多个输出Head，每个Head负责预估一个token。每个Head有三层：首先是一个共享的FFN层，将logit做宽映射（h维->4h维）；然后再过一个非共享的FFN层，将logit维度还原（4h维->h维），经残差连接，得到h维embedding向量。最后，再将结果送入到词表投影层得到每个词的概率分布。

2.生成范式

> [图片内容待重建：img-271a2036f5e4-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
MTP的生成过程是一个“Predict-Verify”的循环过程。先一次性预测K个token，然后利用Transformer的并行性，如图通过掩码的方式实现并行验证。如果预测全部正确，相当于用2次推理的时间实现了K次推理。

进一步地，重叠第n步的verify阶段和第n+1步的predict阶段，能进一步提高推理性能。如图，先预测出3个token，然后在验证阶段，仍然每次都预测3个token。如由于第2个正确，可以以其为条件生成第3个“car”、第4个“this”和第5个“week”，由于最初预测的第3个对不上，故最初的预测只能留下“in”和“the”，然后这里生成的第3~5个就可以直接作为新的一轮预测，后续再验证此时生成的第4和第5个，以此类推，不需要重新预测3个token。

> [图片内容待重建：img-271a2036f5e4-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
本质上，这就是利用多token生成的并行性，把后续根据“in”“the”这两个正确的token进行新一轮预测的步骤并入之前的验证步骤。

## 三、Meta's MTP

如图，Meta让每个头不仅仅是FFN层，还有Transformer层，从而可以处理更复杂的序列上下文关系。

> [图片内容待重建：img-271a2036f5e4-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 四、DeepSeek MTP

> [图片内容待重建：img-271a2036f5e4-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-271a2036f5e4-0006] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
训练阶段：Main Model：由t1生成t2；由t1，t2生成t3；……；由t1~t10生成eos token；计算平均Cross-Entropy Loss。MTP Model 1：MTP Module：由t1，t2生成t3；……；由t1~t9生成eos token；计算平均Cross-Entropy Loss。后续的MTP Module以此类推。

> [图片内容待重建：img-271a2036f5e4-0007] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
从模型架构上看，DeepSeek在Meta工作的基础上，还在MTP的Transformer层前加上了额外的输入。这个额外输入在训练时是ground truth的t2和t3，以防止细微误差导致“跑偏”；在推理时则是模型自身预测的t2和t3（虽然运用了上一次预测，但这里并非退化为Next token prediction，因为自身预测的t2和t3只经过轻量级MTP模块，不经过全模型，故仍为MTP）。MTP头的损失：

> [图片内容待重建：img-271a2036f5e4-0008] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
DeepSeek原论文中插图如下：

> [图片内容待重建：img-271a2036f5e4-0009] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 参考文献与引用线索

> 本节由脚本自动检索正文中的引用线索，可能不完整；未能确定来源的位置会在下方标为待补引用。

### 自动检索到的引用线索

- DeepSeek原论文中插图如下：

### 待补引用或版权检查

- [待补引用] 本文含 Word 内嵌图片；开源版未上传图片。若图片来自教材、论文或技术报告，建议人工确认授权、补充来源或重画。
