---
title: "28.4 EvoTune：进化搜索与RL结合（论文）"
source_docx: "第4部分 大模型智能体与持续学习/28.持续强化学习/28.4 EvoTune：进化搜索与RL结合（论文）.docx"
status: "auto-converted"
ocr: "manual reconstruction completed"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 28.4 EvoTune：进化搜索与RL结合（论文）


> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

## 一、核心思想

EvoTune的核心思想是将进化搜索（作为探索策略）与强化学习（作为优化策略）紧密结合。

进化搜索（Search）：负责在程序空间中探索，生成新的训练数据。

强化学习（Learning）：利用搜索发现的高质量程序作为信号，更新LLM的权重，使其生成的分布π向高分区域通过。

这种设计符合Sutton的“Bitter Lesson”观点：搜索生成数据，学习从数据中提炼模式以指导未来的搜索。

需要注意的是，这不属于元强化学习，因为模型在预训练和后训练中都没有这样的学习。经过此方法在测试时学习的模型，通用性能会下降，也就意味着这种方法并不适用于通用大模型的训练。

## 二、算法架构

1.进化搜索

该阶段的目标是最大化奖励函数 $r(x,y)$，其中 $x$ 是提示词，$y$ 是生成的程序：

$$
y^* = \arg\max_y \mathbb{E}_{x \sim \mathcal{D}}\left[\mathbb{E}_{y \sim \pi_\theta(\cdot \mid x)}[r(x,y)]\right]
$$

- 程序数据库（Program Database）：维护一个“岛屿模型”（Island-based）的数据库 $\mathcal{D}^t$，存储生成的有效程序及其评分。
- 提示构建：从数据库中采样高分程序，利用少样本提示（Few-shot prompting）构造 $x^t$，引导 LLM 生成新的候选程序 $y^{t,k}$。
- 评估与存储：评估生成的程序，更新数据库 $\mathcal{D}^t \leftarrow \mathcal{D}^{t-1} \cup \{(x^t, y^{t,k}, r(y^{t,k}))\}$。

2.RL训练

每进行 $f_{RL}$ 次搜索迭代后，利用积累的数据对 LLM 进行微调。

- RL 目标：优化策略 $\pi_\theta$ 以最大化期望奖励，同时使用 KL 散度约束防止模型偏离参考模型（Reference Model，即初始模型 $\pi_{\mathrm{ref}}$）：

$$
\max_{\pi_\theta}\mathbb{E}_{x \sim \mathcal{D}, y \sim \pi_\theta}[r(x,y)] - \beta \mathbb{D}_f\left[\pi_{\mathrm{ref}}(\cdot \mid x) \| \pi_\theta(\cdot \mid x)\right]
$$

（1）基于DPO算法的损失函数

基于偏好数据的 DPO 损失函数为：

$$
\mathcal{L}(\pi_\theta; \pi_{\mathrm{ref}}) =
\mathbb{E}_{(x,y_+,y_-) \sim \mathcal{D}_{\mathrm{pref}}}
\left[
-\log \sigma\left(
\beta f'\left(\frac{\pi_\theta(y_+ \mid x)}{\pi_{\mathrm{ref}}(y_+ \mid x)}\right)
- \beta f'\left(\frac{\pi_\theta(y_- \mid x)}{\pi_{\mathrm{ref}}(y_- \mid x)}\right)
\right)
\right]
$$

其中：

- $\pi_\theta$ 是当前正在训练的 LLM 策略。
- $\pi_{\mathrm{ref}}$ 是参考策略，即初始的 Base LLM。
- $(x,y_+,y_-)$ 是偏好数据三元组，其中 $y_+$ 是评分较高的程序，$y_-$ 是评分较低的程序。
- $\sigma$ 是 Sigmoid 函数。
- $\beta$ 是控制正则化强度的超参数。
- $f'$ 是 f-divergence 中凸函数 $f$ 的导数，决定了 KL 散度的方向。

（2）Forward RL

这里尤其值得注意的是，它采用了Forward RL而非Reverse RL：

标准的 DPO 通常基于 Reverse KL（$\mathbb{D}_{KL}(\pi_\theta \| \pi_{\mathrm{ref}})$），这种方向倾向于通过集中概率质量到单一模式来“求模”（Mode-seeking），容易导致输出多样性下降（Mode Collapse）。

在进化搜索中，多样性（Diversity）至关重要。为了保持多样性，EvoTune 采用了基于 Forward KL 正则化的 DPO 目标形式，其损失函数为：

$$
\mathcal{L}(\pi_\theta; \pi_{\mathrm{ref}}) =
\mathbb{E}_{(x,y_+,y_-) \sim \mathcal{D}_{\mathrm{pref}}}
\left[
-\log \sigma\left(
\beta f'\left(\frac{\pi_\theta(y_+ \mid x)}{\pi_{\mathrm{ref}}(y_- \mid x)}\right)
- \beta f'\left(\frac{\pi_\theta(y_- \mid x)}{\pi_{\mathrm{ref}}(y_- \mid x)}\right)
\right)
\right]
$$

其中对于 Forward KL，函数 $f'(u) = -1/u$；而 Reverse KL 则是 $f'(u) = \log u + 1$。

实验证明：使用 Forward KL 的变体不仅发现了最高分的程序，而且生成的唯一解（Unique Scores）数量显著多于 Reverse KL 和基线，说明其在维持搜索多样性方面有效。

这背后的原理是：

- 多样性保护（Diversity Maintenance）：进化搜索非常依赖种群的多样性。标准 DPO（Reverse KL）有很强的 Mode-seeking 倾向，会使模型收敛到单一解，导致 Mode Collapse。
- Mass-covering 行为：Forward KL 具有 “Mass-covering” 的特性，它鼓励策略分布 $\pi_\theta$ 覆盖参考分布 $\pi_{\mathrm{ref}}$ 中的高概率区域，而不是仅仅集中在某一个峰值上。这使得模型能生成更多样化的解（Unique Solutions），从而更有利于后续的进化迭代。

## 参考文献

- Lange, R. T., et al. (2024). [Algorithm Discovery With LLMs: Evolutionary Search Meets Reinforcement Learning](https://arxiv.org/abs/2411.10125). arXiv:2411.10125.
