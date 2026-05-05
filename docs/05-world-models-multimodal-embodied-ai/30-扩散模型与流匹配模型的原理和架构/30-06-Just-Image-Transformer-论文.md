---
title: "30.6 Just Image Transformer（论文）"
source_docx: "第5部分 世界模型、多模态生成与具身智能/30.扩散模型与流匹配模型的原理和架构/30.6 Just Image Transformer（论文）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 30.6 Just Image Transformer（论文）


> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

## 一、核心思想

当今主流的扩散模型（如 DDPM）和流匹配模型（Flow Matching）通常训练神经网络去预测噪声 $\epsilon$ 或速度 $v$。JiT 指出，预测干净数据（x-prediction）与预测含噪量（$\epsilon$ 或 v-prediction）在数学本质上是完全不同的。

这一结论建立在**流形假设（Manifold Assumption）**之上：

- **干净图像 $x$**：高维像素空间 $\mathbb{R}^D$ 中的自然图像并非均匀分布，而是高度集中在一个极低维的流形 $\mathcal{M}$ 上（$d\ll D$）。
- **噪声 $\epsilon$**：高斯噪声是各向同性的，它游离于流形之外（off-manifold），散布在整个高维空间 $\mathbb{R}^D$ 中。
- **速度 $v$**：在流匹配中，$v=\epsilon-x$，同样是高维空间中游离于流形之外的量。

当网络被要求预测 $\epsilon$ 或 $v$ 时，它被迫去拟合一个覆盖整个高维空间的无结构映射。而当网络被要求直接预测 $x$ 时，其预测目标被严格限制在低维的自然图像流形 $\mathcal{M}$ 上。这种目标的降维极大地降低了神经网络的拟合难度，使得模型能够在不依赖 Latent 空间降维的情况下，直接在高分辨率像素空间（如 $512\times512$）中高效运作。
## 二、模型架构

JiT 的架构可以说是“除了标准的图像 Transformer，什么都没有”。

1. **无 Tokenizer 与无 Latent 空间**：完全抛弃了主流架构中使用的 VAE 预训练模型，直接对原始像素（Raw Pixels）进行操作。
2. **大图像块（Large Patch Size）**：为了处理高分辨率图像带来的序列长度爆炸，JiT 采用了非常大的 Patch Size（如 $16\times16$ 甚至 $32\times32$ 和 $64\times64$）。
3. **信息瓶颈（Bottleneck Design）**：实验发现，在 x-prediction 模式下，大幅压缩 Transformer 的线性嵌入维度（Embedding Dimension）不仅不会导致模型崩溃，反而能保持鲁棒性。这从侧面印证了流形假设：因为目标 $x$ 本质是低维的，所以低容量（“under-capacity”）的网络瓶颈足以捕获其特征；而预测高维噪声 $\epsilon$ 时，缩小网络容量则会导致灾难性失效。
4. **无预训练与无额外损失**：不需要任何形式的预训练，也不依赖感知损失（Perceptual Loss）或对抗损失（Adversarial Loss）。
唯一新增的模块是在Transformer后加的一个全连接层，把生成的低维嵌入向量映射为高维的图像。这样做有效的原因在于，真实世界的高维图像斑块并不是随机杂乱的，它们具有极强的空间连贯性和规律，因此它们被紧紧约束在一个极低维的“流形”上。Transformer内部的低维隐变量已经足以捕捉这些低维的结构信息，最后的那个全连接层，本质上只是把这个低维结构“旋转”并“映射”回高维空间中对应的流形位置而已。

时间步和Diffusion Transformer一样，通过自适应层归一化的方式注入。

1. **时间步嵌入（Time Embedding）**：

   首先，标量时间步 $t$ 会通过正弦位置编码（Sinusoidal Positional Encoding）映射为高维向量，然后再通过一个多层感知机（MLP）提取特征，生成全局的时间特征向量 $E_t$。

2. **生成调制参数（Modulation Parameters）**：

   每个 Transformer Block 外部设有一个简单的线性回归层（Linear Layer）。该层接收 $E_t$ 作为输入，并直接回归出该 Block 所需的几组调制参数（通常是缩放因子 $\gamma$、平移因子 $\beta$ 以及用于残差连接的门控因子 $\alpha$）。

3. **自适应调制（Adaptive Modulation）**：

   在输入的视觉 Token 序列进入多头自注意力层（MSA）或前馈神经网络（FFN）之前，先对 Token 进行标准的 Layer Normalization。随后，使用刚才回归出的 $\gamma$ 和 $\beta$ 对归一化后的特征进行逐元素的仿射变换：

$$
\mathrm{AdaLN}(x,t)=\gamma(t)\cdot\mathrm{LayerNorm}(x)+\beta(t)
$$

在这里，归一化的尺度和偏移完全由当前的时间步 $t$ 动态决定。
4. **Zero 初始化（Zero Initialization）**：
   这是 adaLN-Zero 的核心创新点。回归 $\gamma,\beta,\alpha$ 的线性层，其权重和偏置在网络初始化时会被严格设为 $0$。这意味着在训练之初，缩放因子不起作用，平移为零，且残差块的门控因子 $\alpha=0$。这使得每一个 Transformer Block 在初始化时等效于一个恒等映射（Identity Mapping）。这种设计极大地稳定了深层网络在训练早期的梯度流动，这对于在原始高维像素空间直接训练大规模 Transformer 尤为重要。

## 三、既然如此，为什么业界仍然使用原始扩散模型？

1.潜在空间已经避免了维度灾难

何恺明的论文主要针对的是**原始像素空间（Pixel Space）**的高维灾难，但当前工业界的世界模型几乎全部采用 Latent Diffusion 架构。

**潜在空间（Latent Space）已经规避了“高维诅咒”**。它们通过 VAE（变分自编码器）将极其高维的视觉/图像帧压缩到一个非常低维的潜在空间（Latent Space）$z\in\mathbb{R}^k$ 中。

由于 VAE 本身就是一个极其强大的流形学习器（Manifold Learner），潜在空间本身已经是一个被高度压缩的低维流形。在如此较低维的空间里，去预测噪声 $\epsilon$ 或速度 $v$，其难度和维度惩罚已经被大幅削减。

如果在原始像素（Pixel Space）上直接进行扩散，哪怕生成一段 $1$ 分钟的 $1080$P 视频，其维度也高达：

$$
1920\times1080\times3\times60\times60\times2.2\times10^{10}
$$

在如此惊人的高维空间中进行梯度计算和马尔可夫链采样，不仅计算成本无法承受，还会遭遇严重的“维度灾难”。

2.动作空间的多样性

为了解决上述问题，具身智能领域引入了 Diffusion Policy，扩散模型彻底放弃了直接输出动作值，而是去学习动作分布的能量场（Energy Field）或得分函数（Score Function）。

工作流与 Langevin Dynamics 机制：

1. **学习得分函数（Score Matching）**：扩散模型的核心训练是训练一个网络去拟合真实数据分布对数据本身的梯度，即 Score：$\nabla_a\log p(x)$。也可以把它想象成一个指向“最合理动作”的指南针。
2. **反向去噪采样（Langevin Dynamics）**：在推理时，模型从纯高斯随机噪声 $x_T\sim\mathcal{N}(0,I)$ 开始，通过如下方式分步更新状态：

$$
x_{t-\Delta t}=x_t+\frac{1}{2}\Delta t\nabla_x\log p(x_t)+\sqrt{\Delta t}z
$$

其中 $z\sim\mathcal{N}(0,I)$ 是注入的随机噪声。

为什么它不会落在沟壑（缝隙）？

- **根据上升（寻找 Mode）**：公式中的 $\nabla_x\log p(x_t)$ 会牵引样本朝概率高、即动作最优的区域移动，即从一些概率密度很低的地方移向概率密度高的地方。
- **噪声注入（打破对称性）**：公式末尾的 $\sqrt{\Delta t}z$ 是噪声之源。在向左和向右两个峰值之间的“均值点”（缝隙点）时，其实是一个概率上的鞍点（Saddle Point）或局部低谷。随机注入的噪声会打破平衡，将生成轨迹随机推向左边或右边的“引力盆地”，从而最终掉进其中一个确定的、安全的 Mode（动作 $A$ 或动作 $B$），完美实现了迭代求精与多模态决策。

注意：这里的p(x)不是训练数据的联合概率密度，而是对于新数据本身的概率分布。

3.高噪声条件下的稳定性

在扩散的最初阶段（$t\to T$ 时），图像几乎是纯高斯噪声。此时 $x_t$ 中属于 $x_0$ 的信息被严重掩没。在数学上，如果直接让模型从纯噪声中预测出一张极其清晰的 $x_0$，会因为方差过大而导致严重的数值不稳定，模型往往会输出一张极其模糊的平均图。而在这个阶段预测噪声 $\epsilon$ 或速度 $v$，在数值梯度和损失函数加权（SNR Weighting）上被证明更加稳定，这也是 Flow Matching（流匹配）能在工业界大行其道的原因。

$$
v=x_1-x_0
$$

其中 $x_1$ 是纯噪声，$x_0$ 是清晰图像。

你可以通过代数变换发现：预测 $v$，其实就是根据当前时间步的信噪比，动态地、自动地在“预测噪声”和“预测原图”之间进行插值切换。

它既规避了早期预测 $x_0$ 的方差爆炸，又规避了晚期预测 $\epsilon$ 的信噪比问题，而且由于轨迹是直接的（ODE），它大幅减少了推理步数，这才是世界模型（生成高帧率视频）真正渴求的特性。

## 参考文献

暂无已核验参考文献。
