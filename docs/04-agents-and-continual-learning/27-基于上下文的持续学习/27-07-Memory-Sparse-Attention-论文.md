---
title: "27.7 Memory Sparse Attention（论文）"
source_docx: "第4部分 大模型智能体与持续学习/27.基于上下文的持续学习/27.7 Memory Sparse Attention（论文）.docx"
status: "auto-converted"
ocr: "manual reconstruction completed"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 27.7 Memory Sparse Attention（论文）


> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

Memory Sparse Attention（MSA）是盛大集团研究团队提出的一种长上下文处理方法，将文档检索融入了注意力机制之中。

## 一、核心架构

### （一）基于文档检索的稀疏注意力

对于每个文档 $d_i$ 及其隐藏状态 $H_i$，除了生成标准的键值矩阵外，模型引入了一个路由器投影器（Router Projector）来生成专门的路由键矩阵 $K_i^{R}$：

$$
K_{i,h}=H_iW_K^h,\quad V_{i,h}=H_iW_V^h,\quad K_{i,h}^{R}=H_iW_{K^R}^h
$$

为了降低内存和检索复杂度，模型将文档分割为固定长度的块（Chunks），并使用均值池化（mean pooling，记为 $\phi$）进行压缩，得到 $\bar{K}_{i,h}$、$\bar{V}_{i,h}$ 和 $\bar{K}_{i,h}^{R}$。查询（Query）也通过类似方式生成路由查询 $Q_{q,h}^{R}$，通过余弦相似度计算查询与每个文档块的相关性得分 $S_{ij}$：

$$
S_{ij}=\max_{\text{token }t}\left(\mathrm{mean}_{\text{head }h}\big(\cos(Q_{q,h}^{R},\bar{K}_{ij,h}^{R})\big)\right)
$$

然后取文档中得分最高的块作为文档得分，并选取 Top-k 个文档的压缩 KV 矩阵，拼接在局部缓存之前供后续的自回归生成使用。

和 RAG 的不同点：RAG 基于模型无关的语义相似度（例如余弦相似度），这与模型内部进行下一 Token 预测的生成目标之间存在一条“优化鸿沟”；MSA 则内置于模型中，生成 Q、K、V 所需的 $W_Q$、$W_K$、$W_V$ 矩阵均为模型内置的矩阵，就可以将检索过程转变为可以端到端联合优化的注意力机制。

### （二）双层位置编码

长文本模型常面临“短文本训练、长文本推理（train-on-short, infer-on-long）”的位置编码偏移问题。

- **文档级 RoPE（Doc-wise RoPE）**：MSA 为记忆库中的每个文档分配独立的起始位置 ID（从 $0$ 开始），使位置语义与文档总数解耦，从而实现了极强的长度外推能力。
- **全局 RoPE（Global RoPE）**：针对活跃的上下文（用户查询和生成的回答），其位置 ID 顺延于被检索文档的数量（从 $k$ 开始），以保留连贯生成所需的因果依赖性。

## 二、工作流

### （一）端到端训练阶段

- **持续预训练（Continuous Pre-training）**：模型在 1589.5 亿 Tokens 的语料上进行训练，目标是生成式检索（Generative Retrieval）。为了指导稀疏路由，引入了基于监督对比学习的辅助损失：

$$
\mathcal{L}_{aux}=-\frac{1}{|\mathcal{P}|}\sum_{i=1}^{|\mathcal{P}|}
\log \frac{\exp(s_i^+/\tau)}
{\exp(s_i^+/\tau)+\sum_{j=1}^{|\mathcal{N}|}\exp(s_{i,j}^-/\tau)}
$$

- **后训练（Post-Training）**：采用两阶段课程学习策略，先在 8k 上下文进行指令微调（SFT），随后将上下文扩展至 64k 以增强外推鲁棒性。

### （二）推理阶段

在推理阶段，MSA 的工作流被设计为三个高效的阶段：

1. **阶段一：全局记忆编码（Global Memory Encoding - 离线计算）**
   - 模型遍历整个语料库中的所有文档，进行一次前向传播。
   - 生成标准的键值矩阵 $(K,V)$ 和专门的路由键矩阵 $K^R$。
   - 通过均值池化将其划分为块并压缩，将这些紧凑的表示 $(\bar{K},\bar{V},\bar{K}^R)$ 缓存在记忆库中。

2. **阶段二：路由与上下文组装（Routing and Context Assembly - 在线处理）**
   - 接收到用户的 Query 后，计算其隐藏状态并投影得到路由查询 $Q_q^R$。
   - 将 $Q_q^R$ 与全局缓存的路由键 $\bar{K}^R$ 进行匹配打分，找出 Top-k 的相关文档。
   - **仅加载**这 Top-k 文档的紧凑键值对 $(\bar{K},\bar{V})$，并与 Query 的局部 $K_q,V_q$ 拼接，形成最终的稀疏上下文。

3. **阶段三：稀疏生成（Sparse Generation - 在线处理）**
   - 模型在组装好的稀疏上下文上进行标准的自回归注意力计算，逐字生成最终答案。

由于处理需要多步推理（Multi-hop reasoning）的复杂问题，MSA 不采用单次检索，而是迭代执行上述工作流的阶段二与阶段三。

模型首先自回归地生成相关文档的 ID，系统拉取对应的原始文本附加到最初的 Query 后面，然后利用更新后的 Query 继续下一轮检索。当模型判定收集的信息已经足够时，自动切换到最终答案的生成。

## 三、内存并行与分层存储

在处理 1 亿 Tokens 时，哪怕是压缩后的 KV Cache 也会占据约 169GB 内存，单台标准的 2 × A800 节点（160GB 显存）根本无法装下。MSA 的解决方案是：

- **GPU 常驻路由键**：仅将用于低延迟检索的 $\bar{K}^R$ 分布式存储在多个 GPU 的显存中（约占 56GB）。
- **CPU 卸载内容 KV**：将庞大的内容 $(\bar{K},\bar{V})$ 存放在主机的 CPU 内存中。当 GPU 算出 Top-k 索引后，异步将命中的部分内容拉取到 GPU 参与生成计算。

## 参考文献

- Chen, Y., Chen, R., Yi, S., et al. (2026). [MSA: Memory Sparse Attention for Efficient End-to-End Memory Model Scaling to 100M Tokens](https://arxiv.org/abs/2603.23516). arXiv:2603.23516.
