---
title: "1.5 交叉熵损失（CE）与Softmax回归"
source_docx: "第1部分 深度学习/1.深度学习基础理论/1.5 交叉熵损失（CE）与Softmax回归.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 1.5 交叉熵损失（CE）与Softmax回归


## 一、交叉熵损失函数（Cross Entropy,CE）

在分类任务中，例如要看一张图，判断它是“猫”、“狗”还是“鸟”。AI会给出一个“概率分布”，比如q=[猫: 0.7, 狗: 0.2, 鸟: 0.1]，标准答案： 真实答案也是一个概率分布，p=[猫: 1, 狗: 0, 鸟: 0]。这时用MSE来量q_i和p_i之间的“距离”就非常不合适了。下面我们引入信息论中的“信息熵”和“交叉熵”概念。

信息论认为，信息是用来消除随机不确定性的东西。信息量取决于不确定性，它可以被理解为一种“惊讶度”，或者说描述这个事件发生的所有可能性所需要的编码数：

如果一个事件必然发生（概率 P=1），它不需要任何编码信息，你已经知道了它必然发生，因此毫不惊讶，惊讶度为 -log₂(1) = 0比特。

如果一个事件有25%的概率发生（P=0.5），这个事件的可能性等同于在00、01、10、11四个2位数编码中随机选择一个，在事件最终发生的那一刻，你获得了2比特的信息，有一些惊讶，惊讶度是 -log₂(0.25) = 2比特。

如果一个事件非常罕见（概率 P -> 0），惊讶度趋近于无穷大。在事件最终发生的那一刻，你极度惊讶。

对于一个离散的概率分布P，假设共有n种可能发生的事件，概率分别为(i=1,...,n)，则信息量，或者说应该分配的编码数的期望为.

在机器学习中，我们有一个真实的分布 P（数据的真实标签），和一个模型预测的分布 Q。我们想知道这两个分布之间有多“不同”。KL散度，也称为相对熵，就是用来衡量用一个近似分布 Q去描述真实分布 P时，所产生的信息损耗。

从P到Q的KL散度定义为：

$$
D_{\mathrm{KL}}(P \parallel Q)=\sum_i p(i)\log\left(\frac{p(i)}{q(i)}\right)
$$

其中表示在真实概率为 p(i)的事件上，用 q(i)来描述它所产生的“信息差异”或“惊讶程度”。KL散度是将所有事件上的这种“信息差异”用真实概率p(i) 进行加权平均，是一个恒非负的函数，当且仅当P、Q两分布完全相同时值为0。

进一步地：

$$
\begin{aligned}
D_{\mathrm{KL}}(P \parallel Q)
&=\sum_i p(i)\log p(i)-\sum_i p(i)\log q(i)\\
&=H(P,Q)-H(P)
\end{aligned}
$$

H(P)是真实分布的信息熵，在分类任务中不变。H(P,Q)就是交叉熵，定义为：

$$
H(P,Q)=-\sum_i p(i)\log q(i)
$$

由于我们的目标是最小化 $D_{\mathrm{KL}}(P\parallel Q)$，而 $D_{\mathrm{KL}}(P\parallel Q)=H(P,Q)-\text{常数}$，那么：

$$
\min D_{\mathrm{KL}}(P\parallel Q)\Longleftrightarrow \min H(P,Q)
$$

在监督学习中，真实分布P是确定的值（有真实标签），与模型参数也无关。此时，用交叉熵来代替KL散度在代码上更简洁且不易出现log0错误。

从编码的角度，我们可以把交叉熵损失函数理解为是在用估计的概率分布进行编码，而事件服从真实分布，此时所需的平均编码数期望。

对于分类任务，为0或1（且只有一个值为1），且等于对应的标签值0或1，因此交叉熵损失可以写成为1时，若趋于0，快速增长，相当于只关心应该分入的那一类算出的概率值和1的接近程度（也就是那个，表示应该分入的那一类算出的概率值），不关心其他类。

对于一个批量的样本（如LLM一次性生成n个token），交叉熵损失函数取n个样本的均值.它可以被视为表达n个样本的“平均信息量”。进一步拓展：交叉熵损失函数取指数后，就可以视为整个序列的困惑度（“生成该序列时，每次平均从几个token里选一个”）。困惑度的n次方的倒数就是生成该序列的联合概率。

那么，为什么不使用均方损失呢？

1.理论不符： MSE 衡量的是两个数值向量之间的欧氏距离。而交叉熵衡量的是两个概率分布之间的信息论距离。分类任务的本质是拟合概率分布，而非拟合特定数值。

2.梯度消失：以二分类（Sigmoid）为例：当我们计算交叉熵损失函数对分类常用的 Sigmoid 激活函数输入z的梯度时，推导结果极其优美：

$$
\frac{\partial L_{\mathrm{BCE}}}{\partial z}=\hat{y}-y
$$

梯度大小正比于预测值与真实值之间的误差，误差越大，梯度更新越快，这是合理的。但如果使用MSE：

$$
\frac{\partial L_{\mathrm{MSE}}}{\partial z}=(\hat{y}-y)\cdot\sigma'(z)
$$

其中：

$$
\sigma'(z)=\sigma(z)(1-\sigma(z))=\hat{y}(1-\hat{y})
$$

梯度中多了一项 sigma'(z)。当 Sigmoid 函数的输出y_hat趋近于0或1时，sigma'(z)这一项会趋近于0。 灾难在于：当模型非常自信地预测错误时（例如y_hat=0.01），sigma'(z)几乎为0，模型明明错得离谱，却无法快速学习（梯度消失），导致训练极其缓慢或卡在局部最优。

## 二、Softmax回归

例如多分类问题，需要输出n个可能类别分别的概率，故要把原来该神经元输出的在实数范围内的logits值（如zi）变为e^zi/(e^z1+...+e^zn)才能作为概率。好处：突出最高值，符合分类问题特性；归一化为0到1之间概率。运用交叉熵损失时：

由于 softmax 和相关的损失函数很常见，因此我们需要更好地理解它的计算方式。将 $l(\mathbf{y},\hat{\mathbf{y}})$ 代入损失函数，利用 softmax 的定义，可以得到：

$$
\begin{aligned}
l(\mathbf{y},\hat{\mathbf{y}})
&=-\sum_{j=1}^{q}y_j\log\frac{\exp(o_j)}{\sum_{k=1}^{q}\exp(o_k)}\\
&=\sum_{j=1}^{q}y_j\log\sum_{k=1}^{q}\exp(o_k)-\sum_{j=1}^{q}y_jo_j\\
&=\log\sum_{k=1}^{q}\exp(o_k)-\sum_{j=1}^{q}y_jo_j
\end{aligned}
$$

考虑相对于任何未规范化预测 $o_j$ 的导数，可以得到：

$$
\partial_{o_j}l(\mathbf{y},\hat{\mathbf{y}})
=\frac{\exp(o_j)}{\sum_{k=1}^{q}\exp(o_k)}-y_j
=\mathrm{softmax}(\mathbf{o})_j-y_j
$$

换句话说，导数是 softmax 模型分配的概率与实际发生情况（由独热标签向量表示）之间的差异。

也就是说，在各个方向上的梯度（下降速率）的比值就是每个方向预测值和实际值之差的比值，如模型预测概率[0.1, 0.7, 0.2] ，真实标签[0, 1, 0] ，计算出的梯度就是[0.1-0, 0.7-1, 0.2-0]。均方损失（对应噪声满足高斯分布）也满足这一特点。

实际计算时：

回想一下，softmax 函数为：

$$
\hat{y}_j=\frac{\exp(o_j)}{\sum_k\exp(o_k)}
$$

其中 $\hat{y}_j$ 是预测的概率分布，$o_j$ 是未规范化预测 $\mathbf{o}$ 的第 $j$ 个元素。如果 $o_k$ 中的一些数值非常大，那么 $\exp(o_k)$ 可能大于数据类型允许的最大数字，即上溢（overflow）。为避免这个问题，可以在继续 softmax 计算之前，先从所有 $o_k$ 中减去 $\max(o_k)$。每个 $o_k$ 按常数移动不会改变 softmax 的返回值：

$$
\begin{aligned}
\hat{y}_j
&=\frac{\exp(o_j-\max(o_k))\exp(\max(o_k))}
{\sum_k\exp(o_k-\max(o_k))\exp(\max(o_k))}\\
&=\frac{\exp(o_j-\max(o_k))}
{\sum_k\exp(o_k-\max(o_k))}
\end{aligned}
$$

尽管我们要计算指数函数，但最终在计算交叉熵损失时会取它们的对数。通过将 softmax 和交叉熵结合在一起，可以直接使用 $o_j-\max(o_k)$，避免反向传播过程中可能困扰我们的数值稳定性问题：

$$
\begin{aligned}
\log(\hat{y}_j)
&=\log\left(\frac{\exp(o_j-\max(o_k))}
{\sum_k\exp(o_k-\max(o_k))}\right)\\
&=\log(\exp(o_j-\max(o_k)))
-\log\left(\sum_k\exp(o_k-\max(o_k))\right)\\
&=o_j-\max(o_k)-\log\left(\sum_k\exp(o_k-\max(o_k))\right)
\end{aligned}
$$

## 三、二元交叉熵损失（BCE）

1.二元交叉熵的数学表达

当分类问题只有两个类别（真或假）可以二选一时，假设为真的实际概率为p，预测为真的概率为q，实际数据标签（真为1，假为0）为y，则真实二元交叉熵的公式为-p*logq-(1-p)*log(1-q)，又y=p，也可写成-y*logq-(1-y)*log(1-q).

2.模型给出预测概率q的方式

当只有两个类别时，我们就不再需要输出多个logits值后用Softmax了，而是只需要一个logit，用sigmoid函数得到为其中某一类（如选择“是”）的概率，再用二元交叉熵。事实上可以证明这种操作就是Softmax的一种特殊情况：

对于两个类别，Softmax输出为：

$$
p_0=\frac{e^{z_0}}{e^{z_0}+e^{z_1}},\qquad
p_1=\frac{e^{z_1}}{e^{z_0}+e^{z_1}}
$$

只关心第二个类别的概率 $p_1$，并定义 $z=z_1-z_0$：

$$
p_1=\frac{e^{z_1}}{e^{z_0}+e^{z_1}}
=\frac{1}{1+e^{-(z_1-z_0)}}
=\sigma(z_1-z_0)
$$

所以二元Softmax可以简化为Sigmoid函数，其中输入是两类logits的差值。

3.BCE在多标签分类中的运用

由于Softmax函数只适用于“n选一”式的“单选”分类，如果我们需要同时将一个对象分到多个类别（如给蛋白质加各种功能标签），进行“多选”分类，Softmax就不适用了。这时我们可以把任务看成有很多（样本，类别）组合，对于每一个组合，都分别判断该对象是否分入该类别。此时，交叉熵损失先按所有（样本，类别）组合加起来，然后按组合总数取平均。

多标签交叉熵损失的代码实现：

```python
import torch

import torch.nn as nn

# 假设批次大小=2，类别数=3

logits = torch.tensor([[1.2, -0.5, 0.8],[-0.3, 1.5, -1.0]]) #模型输出的原始值（未经过激活函数）

targets = torch.tensor([[1, 0, 1], [0, 1, 0]], dtype=torch.float) #真实标签，这里用0和1表示每个样本是否属于某个类别

# 使用BCEWithLogitsLoss（默认reduction='mean'即取平均模式）

criterion = nn.BCEWithLogitsLoss()

loss = criterion(logits, targets)

print(f"损失值: {loss.item()}")

# 手动验证计算过程

sigmoid_outputs = torch.sigmoid(logits)

bce_per_element = - (targets * torch.log(sigmoid_outputs) +

(1 - targets) * torch.log(1 - sigmoid_outputs)) #相同形状的矩阵，Pytorch执行按元素乘法

print(f"每个(样本,类别)的损失:\n{bce_per_element}")

total_loss = bce_per_element.sum()

num_elements = bce_per_element.numel()  # N × C = 2 × 3 = 6

manual_loss = total_loss / num_elements

print(f"手动计算的平均损失: {manual_loss.item()}")

```

## 参考文献

- Aston Zhang, Zachary C. Lipton, Mu Li, Alexander J. Smola. (2023). [《动手学深度学习》](https://zh.d2l.ai/). Cambridge University Press.
