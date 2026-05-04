---
title: "30.3 Diffusion U-Net"
source_docx: "第5部分 世界模型、多模态生成与具身智能/30.扩散模型与流匹配模型的原理和架构/30.3 Diffusion U-Net.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 30.3 Diffusion U-Net


U-Net采用卷积神经网络，前半部分类似Encoder，通过池化或步长＞1的卷积，使空间尺寸数不断减小、通道数不断增大；后半部分类似Decoder，空间尺寸数不断增大、通道数不断减小，主要有两种实现方法：

**1. 转置卷积（Transposed Convolution）**

这是 U-Net 解码器中使用的核心放大技术。它不仅仅是简单的图像插值，而是一个带有可学习参数的逆向空间扩散过程。

在标准卷积中，我们可以将其表示为矩阵乘法 $\mathbf{Y}=\mathbf{C}\mathbf{X}$，其中 $\mathbf{C}$ 是由卷积核转换而来的稀疏矩阵，此过程将大维度的 $\mathbf{X}$ 压缩为小维度的 $\mathbf{Y}$。

转置卷积则是将输出特征图通过乘以 $\mathbf{C}$ 的转置矩阵 $\mathbf{C}^T$（并通过反向传播学习权重）还原到更大的空间：

$$
\mathbf{X}'=\mathbf{C}^T\mathbf{Y}
$$

工作流：

以卷积核大小 $K=3$、步长 $S=2$、填充 $P=1$ 为例：

1. **内部零填充（Zero-padding expansion）**：在输入特征图的相邻像素之间插入 $S-1$ 个零。这会将低分辨率输入的空间尺寸强行撑大。
2. **边界填充**：在扩展后的特征图四周边缘添加额外的零填充（数量由 $K$ 和 $P$ 决定，以精确对齐所需输出的尺寸）。
3. **标准卷积映射**：对上述经过两次填充的巨大特征图，应用一个标准的 $K\times K$ 卷积核（此时卷积的步长固定为 1）。
4. **特征输出**：卷积核在滑动计算过程中，将原始孤立像素的值与其权重相乘并“扩散”到周围插零的区域，最终输出平滑的高分辨率特征图。

**2. 双线性插值（Bilinear Interpolation）**

这是一种无参数的纯数学插值方法。它通过计算目标像素在原图中对应位置周围四个已知像素的加权平均值来生成新像素。它的计算成本极低，但无法像转置卷积那样根据数据集的特征自适应学习放大规则。

但U-Net的可扩展性一般，且与当前基于Transformer的大模型架构不兼容。

## 参考文献

暂无已核验参考文献。
