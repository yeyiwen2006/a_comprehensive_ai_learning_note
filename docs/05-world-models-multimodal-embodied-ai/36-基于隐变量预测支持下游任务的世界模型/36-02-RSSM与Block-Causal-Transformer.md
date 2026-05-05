---
title: "36.2 RSSM与Block-Causal Transformer"
source_docx: "第5部分 世界模型、多模态生成与具身智能/36.基于隐变量预测支持下游任务的世界模型/36.2 RSSM与Block-Causal Transformer.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 36.2 RSSM与Block-Causal Transformer


## 一、RSSM

### （一）模型架构

在构建环境动力学模型时，通常有两种极端：

1. **纯确定性模型（如标准 RNN）**：状态转移是完全确定的。这种模型容易出现的一个致命缺陷是，它无法捕捉环境动力学中固有的不确定性和多种可能的未来（Multiple futures）。如果用于规划，规划器（Planner）会很容易利用这种确定性模型的不准确性（即过拟合到单一的错误未来）。

2. **纯随机性模型（如传统 SSM）**：每一次状态转移都包含从概率分布中采样。虽然这能建模不确定性，但纯粹的随机转换使得模型极难在跨越多个时间步的情况下可靠地记忆信息。

而且，如果环境存在随机性，确定性网络往往会输出所有可能未来的“模糊平均值”。

RSSM采用了类似LSTM的方法，将隐状态（历史记忆）和反映当前状态的潜变量分开，从而结合了二者的优点。在POMDP（部分可观测马尔可夫决策过程）中：

历史记忆h_t作为隐状态，其转移用确定性规则：由对t-2时刻及以前的记忆h_t-1、t-1时刻的状态潜变量s_t和t-1时刻的动作a_t-1经过函数得到。

1. **确定性状态模型（Deterministic state model）**

$$
h_t = f(h_{t-1}, s_{t-1}, a_{t-1})
$$

- **物理意义**：用于汇总历史信息并维持跨越多个时间步的确定性记忆。
- **拟合方式**：通常由一个循环神经网络（RNN，如 GRU）拟合。

利用包含了t-1时刻及以前状态和动作的历史记忆h_t预测世界状态潜变量s_t则随机采样：

2. **随机状态模型 / 先验分布（Stochastic state model / Prior）**

$$
s_t \sim p(s_t \mid h_t)
$$

- **物理意义**：在不观察当前真实图像的情况下，仅凭过去的记忆预测当前可能的状态分布。它为模型引入了不确定性，以刻画多种可能的未来。
- **拟合方式**：由一个多层感知机（MLP）拟合，输出对角高斯分布的均值和方差。

而实际上世界状态的潜变量s_t（也就是获得当前真实观测o_t后的“预测正确答案”）：（注：理论上可用贝叶斯计算，但涉及不可求的积分，故直接用神经网络拟合）

3. **近似后验模型 / 变分编码器（Approximate posterior / Variational Encoder）**

$$
q(s_t \mid h_t, o_t)
$$

- **物理意义**：结合过去的确定性记忆 $h_t$ 和当前的真实高维像素观测 $o_t$，推断出当前最准确的潜在状态分布。
- **拟合方式**：由卷积神经网络（CNN）提取图像特征后，接多层感知机（MLP）输出对角高斯分布的均值和方差。

当我们预测出s_t后，可基于h_t和s_t生成像素图像o_t：

4. **观测重构模型（Observation model / Decoder）**

$$
o_t \sim p(o_t \mid h_t, s_t)
$$

- **物理意义**：验证潜在状态是否包含了足够的环境信息，通过潜在状态还原出高维的像素图像。
- **拟合方式**：由反卷积神经网络（Deconvolutional Neural Network）拟合。

以及预测奖励：

5. **奖励预测模型（Reward model）**

$$
r_t \sim p(r_t \mid h_t, s_t)
$$

- **物理意义**：预测在当前潜在状态下能获得的标量奖励，这是规划器（Planner）在潜在空间中评估动作好坏的唯一依据。
- **拟合方式**：由多层感知机（MLP）拟合。

### （二）工作流

- **步骤 1：数据采样**

从经验回放池 $\mathcal{D}$ 中均匀随机抽取批量大小为 $B$、长度为 $L$ 的序列片段 $\{(o_t, a_t, r_t)_{t=k}^{L+k}\}_{i=1}^{B}$。

- **步骤 2：状态展开与分布计算（Forward Pass）**

对于序列中的每一个时间步 $t = 1 \ldots L$：

1. 执行确定性状态转移：将上一步的 $h_{t-1}$、$s_{t-1}$（通过重参数化采样得到）和动作 $a_{t-1}$ 输入 RNN $f$，得到当前的确定性状态 $h_t$。
2. 计算先验分布 $p$：将 $h_t$ 输入 MLP，输出当前先验高斯的均值和方差 $\mu_{prior}$、$\sigma_{prior}$。
3. 计算后验分布 $q$：将当前的图像 $o_t$ 通过 CNN 提取特征，结合 $h_t$ 输入到另一个 MLP，输出后验高斯的均值和方差 $\mu_{post}$、$\sigma_{post}$。
4. 重参数化采样：从后验分布 $\mathcal{N}(\mu_{post}, \sigma_{post}^2)$ 中采样出潜在向量 $s_t$。

- **步骤 3：计算重构与预测**

将 $h_t$ 和采样得到的 $s_t$ 输入反卷积解码器预测重构图像 $\hat{o}_t$，并输入奖励模型预测标量奖励 $\hat{r}_t$。

- **步骤 4：损失计算（Loss Computation）**

1. 计算重构图像 $\hat{o}_t$ 与真实图像 $o_t$ 的 MSE（重构损失）。
2. 计算预测奖励 $\hat{r}_t$ 与真实奖励 $r_t$ 的 MSE。
3. 计算先验分布 $p$ 与后验分布 $q$ 之间的 KL 散度（如果使用 Latent Overshooting，还需要并行计算并累加跨越多步的先验与当前后验的 KL 散度）。

- **步骤 5：参数更新（Backpropagation）**

将所有时间步的损失累加求平均得到总损失 $\mathcal{L}(\theta)$，使用优化器（如 Adam）计算梯度，更新构成这 5 个函数的所有神经网络参数 $\theta \leftarrow \theta - \alpha \nabla_{\theta}\mathcal{L}(\theta)$。

### （三）损失函数

损失分为三部分：仅有过去记忆时对现在潜变量的预测p和包含过去记忆与现在观测时的真实现在潜变量q之间的KL散度，体现的是预测下一时刻的潜变量和真实下一时刻的潜变量的差距，反映预测下一时刻状态的能力；图像重构损失反映由潜变量重构像素的能力；奖励损失反映由潜变量预测奖励的能力。表达式如下：

$$
\mathcal{L}
=
\sum_{t=1}^{T}
\left(
-\mathbb{E}_{q(s_t \mid o_{\le t}, a_{<t})}
\left[\ln p(o_t \mid s_t) + \ln p(r_t \mid s_t)\right]
+
\mathbb{E}
\left[
D_{KL}\left(
q(s_t \mid o_{\le t}, a_{<t})
\parallel
p(s_t \mid s_{t-1}, a_{t-1})
\right)
\right]
\right)
$$

这里o_t和r_t均满足高斯分布，故这两项等价于MSE Loss。

由于标准目标只通过一步 KL 散度训练随机路径，模型在多步预测时容易发散。Latent Overshooting 将约束扩展到距离为 $d$ 的所有未来时间步：

$$
\mathcal{L}_{overshooting}(\theta)
=
\sum_{t=1}^{T}
\left(
-\mathbb{E}_{q}\left[\ln p(o_t \mid s_t)\right]
+
\frac{1}{D}
\sum_{d=1}^{D}
\beta_d
\mathbb{E}
\left[
D_{KL}\left(
q(s_t \mid o_{\le t})
\parallel
p(s_t \mid s_{t-d})
\right)
\right]
\right)
$$

- **物理意义**：它不仅要求“由 $t - 1$ 步预测的 $t$ 步先验”要与后验对齐，还要求“由 $t - 2$ 步、$t - d$ 步连续多步推演得出的 $t$ 步先验”也要与当前后验对齐。这种潜在空间中的一致性正则化，增强了模型在不依赖真实观测时的长期演化能力。

## 二、基于RSSM的应用

### （一）PlaNet：基于世界模型的搜索规划

1. **外层循环：模型训练与数据收集（Algorithm 1）**

- **初始化**：使用随机动作收集少量初始种子回合（Seed episodes），存入经验回放池 $\mathcal{D}$。
- **模型拟合**：从 $\mathcal{D}$ 中随机抽取数据块，利用上述变分下界公式计算损失，并通过梯度上升更新 RSSM 的参数 $\theta$。
- **环境交互**：使用更新后的模型，通过规划算法（见下文 CEM）选择动作 $a_t$，在动作上加入高斯探索噪声，与环境交互并将新经验存入 $\mathcal{D}$。

2. **内层循环：基于 CEM 的动作规划（Algorithm 2）**

在每一个时间步，智能体不使用策略网络（Policy Network）输出动作，而是通过交叉熵方法（Cross Entropy Method, CEM）和模型预测控制（MPC）实时搜索最优动作序列：

- **初始化信念**：构建一个随时间变化的正态分布信念 $q(a_{t:t+H}) \sim Normal(\mu, \sigma^2 I)$，用于表示规划视界 $H$ 内的最佳动作序列。
- **迭代优化**：
  1. 从当前信念中采样 $J$ 个候选动作序列。
  2. 将这些序列输入到学习好的 RSSM 模型中，仅在潜在空间中推演未来状态，并计算预期奖励总和 $R^{(j)}$。
  3. 挑选出奖励最高的 $K$ 个动作序列。
  4. 使用这 $K$ 个优秀序列的均值和方差重新拟合动作信念分布。
- **执行与重规划**：经过 $I$ 次迭代后，提取最终信念均值的第一个动作去执行。由于采用 MPC 机制，接收到新观测后，动作序列的信念会重置为零均值和单位方差，以避免陷入局部最优。

### （二）Dreamer 3：利用世界模型进行RL训练

1.世界模型

- 世界模型通过自动编码技术，将复杂的感知输入（如图像）压缩成紧凑的潜在表示。
- 它被实现为一个循环状态空间模型（RSSM）。
- 首先，编码器将感知输入 $x_t$ 映射为随机表示 $z_t \sim q_{\phi}(z_t \mid h_t, x_t)$。
- 然后，动力学预测器根据之前的状态 $h_t$ 预测未来的表示 $\hat{z}_t \approx p_{\phi}(\hat{z}_t \mid h_t)$。
- 通过这种方式，世界模型学会了理解环境的内在结构，并能在隐空间中“想象”未来的状态演变。

在数学上，RSSM 是一种结合了确定性循环神经网络（RNN）和随机状态变量的生成式模型。在时间步 $t$，它定义动作 $a_t$、观测输入 $x_t$、奖励 $r_t$ 以及回合继续标志 $c_t \in \{0, 1\}$。

2.Critic

**Step 2：评论家学习（Critic Learning）**

- 评论家和演员完全在世界模型“想象”出的抽象轨迹中进行学习，而无需直接与真实环境交互。
- 评论家接收模型状态 $s_t = [h_t, z_t]$，并学习评估该状态的价值。
- 为了考虑长期收益，评论家预测的是回报分布的期望值，并使用自举（bootstrapped）的 $\lambda$-回报来整合预测的奖励和价值。

3.Actor

**Step 3：演员学习（Actor Learning）**

- 演员的目标是选择能够最大化回报的动作，同时通过熵正则化（entropy regularizer）来鼓励探索。
- 它通过策略梯度方法（Reinforce estimator）在想象的轨迹上进行优化。

4.损失函数

（1）预测损失

$$
\mathcal{L}_{pred}(\phi)
\doteq
-\ln p_{\phi}(x_t \mid z_t, h_t)
-\ln p_{\phi}(r_t \mid z_t, h_t)
-\ln p_{\phi}(c_t \mid z_t, h_t)
$$

这部分通过负对数似然，迫使模型准确地重构观测输入、奖励和回合标志。

（2）动力学损失

$$
\mathcal{L}_{dyn}(\phi)
\doteq
\max\left(
1,
D_{KL}\left[
sg(q_{\phi}(z_t \mid h_t, x_t))
\parallel
p_{\phi}(\hat{z}_t \mid h_t)
\right]
\right)
$$

其核心目的是让动力学预测器 $p_{\phi}$ 逼近编码器给出的后验分布 $q_{\phi}$。这里使用 $sg()$（stop-gradient，停止梯度）操作，表示在拉近两个分布距离时，只更新动力学预测器的参数，而不影响编码器提取特征的方式。

同时，公式外围包裹的 $\max(1, \cdot)$ 引入了空闲位（Free bits）技术：当 KL 散度下降到 1 nat $\approx 1.44$ bits 以下时，模型会停止在这项损失上的惩罚，避免学到过于退化的平凡动力学，从而将学习重点转移回预测损失上。

（3）表示损失

$$
\mathcal{L}_{rep}(\phi)
\doteq
\max\left(
1,
D_{KL}\left[
q_{\phi}(z_t \mid h_t, x_t)
\parallel
sg(p_{\phi}(\hat{z}_t \mid h_t))
\right]
\right)
$$

与上一个损失相反，表示损失的梯度方向被限制在编码器 $q_{\phi}$ 上。它的目的是反向规范编码器的行为，促使它提取出来的隐状态更加“有规律”、更容易被动力学模型预测。

通过巧妙运用停止梯度操作和不同的损失缩放（在论文中设定为 $\beta_{pred} = 1$、$\beta_{dyn} = 1$、$\beta_{rep} = 0.1$），RSSM 解决了以往“强正则化在简单图像有效，但在复杂 3D 环境会抹杀关键细节”的进退两难问题，实现了跨领域的鲁棒性。

## 三、结合并行扫描的状态空间模型

### （一）核心算法

RSSM的问题在于，当前时刻的隐状态依赖于上一时刻的输出，且时间步传递中存在非线性激活函数，必须先算t=1，再算t=2，以此类推，时间复杂度为O(L)，成为长轨迹计算的瓶颈。

而S5WM采取如下工作流：

**步骤 1：收集与采样数据（Data Sampling）**

- 从重放缓冲区（Replay Buffer）中均匀采样一批历史序列数据，包含观测 $o_t$、动作 $a_t$、奖励 $r_t$ 和连续性标志 $c_t$。

**步骤 2：训练状态空间世界模型（World Model Training）**

- **编码**：编码器（Encoder）将观测图像或状态 $o_t$ 映射为后验随机表示 $z_t \sim q_{\phi}(\cdot \mid o_t)$。
- **特征融合**：将 $z_t$ 与上一动作 $a_t$ 通过多层感知机（MLP）融合为一个输入向量 $u_t$。
- **并行序列建模**：将整个序列的 $u_{1:L}$ 输入到 S5 块中，利用并行扫描技术一次性并行计算出整个序列的隐藏状态 $x_{1:L}$ 和确定性表示 $y_{1:L}$。
- **解码与损失计算**：模型使用预测头来预测先验随机状态 $\hat{z}_t$、观测 $\hat{o}_t$、奖励 $\hat{r}_t$ 和连续性 $\hat{c}_t$。最后通过最小化包含预测损失、动态损失（KL 散度）和表示损失的联合损失函数 $\mathcal{L}(\phi)$ 来更新世界模型权重。

**步骤 3：训练 Actor-Critic（Actor-Critic Training in Imagination）**

- **潜在空间想象**：从真实数据中采样初始状态，然后在没有任何环境交互的情况下，利用训练好的世界模型在潜在空间中“想象”出未来视野长度为 $H$（如 10 步）的轨迹。
- **策略更新**：Actor 根据确定性状态 $y_t$ 和随机状态 $\hat{z}_t$ 输出动作；Critic 预测引导的 $\lambda$-回报（Bootstrapped $\lambda$-returns）。利用世界模型的完全可微性，将一阶梯度反向传播给策略网络，从而优化 Actor 和 Critic 的参数。

传统的 RSSM 中，后验随机变量 $z_t$ 的推断不仅依赖于观测 $o_t$，还依赖于具有时序依赖的确定性状态 $y_t$，即 $z_t \sim q_{\phi}(\cdot \mid y_t, o_t)$。这在架构上锁死了并行性。S5WM 的设计中，将后验推断前置解耦：先完全只以当前时刻的观测 $o_t$ 推断得出，即 $z_t \sim q_{\phi}(\cdot \mid o_t)$。这样，所有的 $z_{1:L}$ 都可以用编码器（CNN）一口气并行计算完毕，随后再送入 S5 序列层进行并行扫描。

线性状态空间模型可写作：

$$
x_t = \bar{A}x_{t-1} + \bar{B}u_t
$$

$$
y_t = Cx_t + Du_t
$$

这里能实现并行的核心在于：

假设将初始元素定义为一个二元组：

$$
e_k = (e_{k,a}, e_{k,b}) := (\bar{A}, \bar{B}u_k)
$$

通过数学推导，序列状态可以展开为一系列二元操作符 $\bullet$ 的连续运算。这个操作符定义为：

$$
a_i \bullet a_j
=
\left(
a_{j,a} \odot a_{i,a},
a_{j,a} \otimes a_{i,b} + a_{j,b}
\right)
$$

这里 $\odot$ 代表矩阵乘法，$\otimes$ 代表矩阵向量乘法。

对于一个长序列的计算，我们不需要像 RNN 那样串行计算：

$$
e_1 \rightarrow (e_1 \bullet e_2) \rightarrow ((e_1 \bullet e_2) \bullet e_3) \cdots
$$

因为满足结合律，可以将其构建成一棵二叉树来并行计算：

$$
(e_1 \bullet e_2) \bullet (e_3 \bullet e_4)
$$

在有足够并行处理器（如 GPU）的情况下，原本 $O(L)$ 的串行时间复杂度被直接对数化，降维打击至 $O(\log L)$。

### （二）并行状态重置

RL中，数据往往由多个回合拼接而成。在不断往回递归的过程中，如果已经到了序列最开始，就需要立即截断，防止上一回合状态污染本回合。

如果在并行计算中遇到截断信号，普通的 SSM 算法会崩溃，因为它不知道如何在并行的树状结构中“清零”。作者扩展了前面的二元操作符，引入连续性预测变量 $c_k \in \{0, 1\}$，并将初始元素扩展为三元组：

$$
e_k = (e_{k,a}, e_{k,b}, e_{k,c}) := (\bar{A}, \bar{B}u_k, 1 - c_k)
$$

并设计了带有条件分支的新并行操作符：

$$
a_j \bullet a_i
=
\begin{cases}
(a_{j,a} \odot a_{i,a}, a_{j,a} \otimes a_{i,b} + a_{j,b}, a_{i,c}), & \text{if } a_{j,c} = 0 \\
(a_{j,a}, a_{j,b}, a_{j,c}), & \text{if } a_{j,c} = 1
\end{cases}
$$

这个分段函数的设计非常关键。当 $a_{j,c} = 1$ 时（代表回合结束），操作符会直接丢弃来自左侧子树（历史数据）的 $a_i$ 信息，只保留当前的 $a_j$ 信息。这就使得模型在执行 $O(\log L)$ 的大规模并行计算时，能够自动且并行地处理序列中任意位置的“重置”信号。

## 四、Block-Causal Transformer

RSSM作为RNN，在长程规划上存在劣势。Block-Causal Transformer是Transformer在世界模型中的一种应用范式，在Dreamer 4中就用了这种架构。

**经典因果 Transformer（Standard Causal Transformer）**

它采用严格的 Token 级下三角掩码。对于任意两个 Token 索引 $i, j \in \{1, 2, \ldots, N\}$，掩码定义为：

$$
M^{causal}_{i,j}
=
\begin{cases}
0, & \text{if } i \ge j \\
-\infty, & \text{if } i < j
\end{cases}
$$

这意味着，即使 Token $i$ 和 Token $j$ 属于同一帧视频，在序列中排在后面的 Token 也只能单向观测排在前面的 Token。这在自然语言中是合理的，但在图像中会迫使模型采用从左上角到右下角的逐块阅读顺序，破坏同一时刻空间的整体连贯性。

**Block-Causal Transformer**

它采用块级因果掩码（Block-lower-triangular Mask）。定义映射函数 $t(i)$ 为 Token $i$ 所在的时间步（帧序号），其掩码定义为：

$$
M^{block}_{i,j}
=
\begin{cases}
0, & \text{if } t(i) \ge t(j) \\
-\infty, & \text{if } t(i) < t(j)
\end{cases}
$$

在这个矩阵中，主对角线上是大小为 $S \times S$ 的全零矩阵块，允许同一时间帧内双向注意力；主对角线右上方则是 $-\infty$。当 $t(i) = t(j)$ 时，也就是两个 Token 在同一时间帧内，$M^{block}_{i,j} = 0$。

当用于诸如 Dreamer 4 的交互式动力学建模或物理 PDE 预测时，BCT 的工作流如下：

1. **数据分块与编码（Tokenization & Patching）**：将输入的连续视频帧序列离散化，每一帧被切割为 $S$ 个 Patch，并映射为特征向量序列。
2. **复合位置编码注入（Spatiotemporal Positional Encoding）**：为每个 Token 注入两个维度的位置信息：一个是它在当前帧内的二维空间坐标 $(x, y)$，另一个是它所在的时间步 $t$。
3. **块因果注意力计算（Block-Causal Attention Calculation）**：同帧并行计算时，在第 $t$ 个 Block 内部，执行 $S$ 个 Token 的全连接自注意力计算，提取当前帧的高分辨率空间语义和物体关系。历史特征提取时，同帧这 $S$ 个 Token 共同作为 Query，去 attend 过去所有帧（1 到 $t - 1$）生成的 Key 和 Value，捕获时序上的物理动力学。
4. **下一帧块级自回归预测（Block-wise Autoregressive Generation）**：不同于经典 GPT 必须逐个 Token 吐出，BCT 在完成前 $t$ 帧的上下文建模后，可以直接将其作为上下文先验，向第 $t + 1$ 帧的完整空间块注入，并行且高效地生成第 $t + 1$ 帧的完整空间表征。

也就是说，在生成第t+1帧时，它刚开始是噪声向量的组合，前t帧的信息在Attention模块中作为上下文不断与之融合。

## 参考文献

暂无已核验参考文献。
