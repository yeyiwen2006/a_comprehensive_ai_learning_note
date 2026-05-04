---
title: "16.2 词嵌入（Embedding）"
source_docx: "第3部分 大语言模型/16.大语言模型的基本原理/16.2 词嵌入（Embedding）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 16.2 词嵌入（Embedding）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

## 一、词嵌入（Embedding）的整体流程

Tokenizer（分词器）把句子切分成词（Token），然后去词表里查出每个词对应的整数ID。词嵌入层（Embedding Layer）接收Tokenizer输出的整数ID，并将其转化为包含语义的浮点数向量，供后续的Attention层进行处理。

## 二、Tokenizer（分词器）

输入一个原始文本字符串，如"The cat sat"。Tokenizer先将字符串分解为“词元”(Token)，再根据一个在训练前就构建好的、从“词”到“ID”的映射字典，每个 Token 转换为其对应的整数 ID。如["the", "cat", "sat"]转化为[2, 3, 4]，不是训练的对象。

## 三、Embedding Layer（词嵌入层）

它是神经网络内部的第一个层，输入是Tokenizer输出的整数ID序列，如[2, 3, 4]，输出这些ID对应的向量拼接成的矩阵。在数学上，这个过程可以用矩阵线性计算（无激活函数）表示。它的参数是每个Token的embedding向量表示，例如词汇表有 50,000 个词，每个词是一个300维向量，那这一层的参数量就是15,000,000。训练时根据输入和输出更新参数，通过参数的正确收敛（每个词嵌入向量能有效表达语义），实现对输入文段的正确输出表示。测试时，根据前向计算，得出每个Token的ID对应的嵌入向量。例如算出代表 "the" 的 300 维向量为[0.12, -0.45, ..., 0.88] ，代表 "cat" 的[0.67, 0.01, ..., -0.23]，代表 "sat" 的[-0.11, 0.98, ..., 0.51] ，输出[[0.12, ...], [0.67, ...], [-0.11, ...]]。

> [图片内容待重建：img-aa8de7a88860-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。

## 参考文献

暂无已核验参考文献。
