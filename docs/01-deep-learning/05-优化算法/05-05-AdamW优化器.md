---
title: "5.5 AdamW优化器"
source_docx: "第1部分 深度学习/5.优化算法/5.5 AdamW优化器.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 5.5 AdamW优化器


AdamW优化器（Adam with Decoupled Weight Decay）是对Adam优化器的一种改进。

## 一、提出背景：Adam自适应学习率对正则化项的错误缩放

在传统 Adam 中，我们向损失函数添加 $L_2$ 范数惩罚：

$$
\mathcal{L}_{total}(\theta) = f(\theta) + \frac{\lambda}{2}\lVert\theta\rVert^2
$$

此时，传入优化器的梯度 $\hat{g}_t$ 变为：

$$
\hat{g}_t = \nabla f(\theta_{t-1}) + \lambda\theta_{t-1}
$$

Adam 算法将这个包含正则项的梯度 $\hat{g}_t$ 用于计算动量 $m_t$ 和 $v_t$：

$$
m_t = \beta_1m_{t-1} + (1-\beta_1)\hat{g}_t
$$

$$
v_t = \beta_2v_{t-1} + (1-\beta_2)\hat{g}_t^2
$$

参数更新公式为：

$$
\theta_t = \theta_{t-1} - \eta\frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon}
$$

问题所在：正则化项 $\lambda\theta$ 被混入了 $m_t$ 和 $v_t$ 中。由于 Adam 会除以 $\sqrt{v_t}$ 来进行自适应缩放，这意味着正则化项也被自适应缩放了。

对于梯度变化幅度很大的参数（$v_t$ 大），正则化力度被削弱了。对于梯度变化平缓的参数（$v_t$ 小），正则化力度被放大了。这导致不同参数受到的衰减力度不均匀，且 $\lambda$ 的最佳取值与学习率 $\eta$ 产生了强耦合，难以调参。

我们需要的是Loss对参数的梯度太大时减小学习率，Loss对参数的梯度太小时增大学习率，而不应该影响正则化项。故需要把正则化项解耦出来。

## 二、AdamW的解决方案

AdamW 将权重衰减项从梯度 $\hat{g}_t$ 中移除。梯度仅基于原始损失函数：

$$
g_t = \nabla f(\theta_{t-1})
$$

动量计算仅涉及原始梯度：

$$
m_t = \beta_1m_{t-1} + (1-\beta_1)g_t
$$

$$
v_t = \beta_2v_{t-1} + (1-\beta_2)g_t^2
$$

参数更新公式分为两部分，分别为Adam更新方向和独立权重衰减：

$$
\theta_t = \theta_{t-1} - \eta\frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon} - \eta\lambda\theta_{t-1}
$$

其中，第一项是标准 Adam 更新步，第二项是解耦的权重衰减。

权重衰减项直接作用于参数，不再受到学习率的缩放影响。这恢复了SGD中权重衰减的原始物理意义（即每次迭代让权重按比例收缩），使得模型的泛化能力通常优于Adam。

## 参考文献

暂无已核验参考文献。
