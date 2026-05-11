---
title: "13.3 PPO算法与GAE"
source_docx: "第2部分 强化学习/13.综合价值与策略的算法/13.3 PPO算法与GAE.docx"
status: "auto-converted"
ocr: "no pending image placeholders in public Markdown"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 13.3 PPO算法与GAE


PPO由TRPO衍生而来。TRPO提出了运用重要性采样、限制更新范围等，但它作为一个带约束的优化问题，求解十分复杂，是一个“精确但昂贵”的算法，在大模型中并不实用。我们想到，可以将约束条件直接写入目标函数。具体而言，有两种方法，也因此产生了PPO的两种变体。

## 一、PPO-Penalty

目标函数如下：

$$
\begin{aligned}
J^{\mathrm{PEN}}(\theta)
&=
\mathbb{E}_t\left[
\frac{\pi_\theta(a_t\mid s_t)}
{\pi_{\theta_{\mathrm{old}}}(a_t\mid s_t)}
A_t
-
\beta\cdot
D_{\mathrm{KL}}\left(
\pi_{\theta_{\mathrm{old}}}(\cdot\mid s_t)
\Vert
\pi_\theta(\cdot\mid s_t)
\right)
\right]
\end{aligned}
$$

* 第一项：TRPO 中的代理目标，即 Ratio $\times$ Advantage，负责让策略变好。
* 第二项：KL 散度惩罚项，$D_{\mathrm{KL}}$ 衡量新旧策略分布的差异。
* $\beta$：惩罚系数。$\beta$ 越大，越不允许策略剧烈变化。

这里第一项同TRPO，即找到一个新策略，让获得奖励在新策略下的期望最大；第二项的前向KL散度主要意在确保旧策略 $\pi_{\mathrm{old}}$ 概率高的区域，如预训练中学习到的常见的人类语言模式和世界基础知识，新策略 $\pi_{\mathrm{new}}$ 概率也高，避免模型为了获取更高的 Reward 而丢弃预训练中学习到的知识而发生“模式崩塌”；而对于一些旧策略概率较低的高难度问题解法，新策略在提高概率的同时不会受到过度的惩罚。这样可以保证每次更新都在一个可信的“信任区域”内进行。

PPO-Penalty 的精髓在于它不是使用固定的 $\beta$，而是根据每一轮更新后的实际 KL 散度值动态调整。设：

$$
d = D_{\mathrm{KL}}(\pi_{\mathrm{old}},\pi_{\mathrm{new}})
$$

设定一个目标 KL 值 $d_{\mathrm{targ}}$，例如 $0.01$：

1. 如果 $d < d_{\mathrm{targ}}/1.5$，说明策略变动太小、过于保守，于是减小 $\beta$，例如：

$$
\beta \leftarrow \beta/2
$$

让下一轮步子迈大一点。

2. 如果 $d > d_{\mathrm{targ}}\times 1.5$，说明策略变动太大、过于激进，于是增大 $\beta$，例如：

$$
\beta \leftarrow 2\beta
$$

让下一轮受到的惩罚更重。

## 二、PPO-Clip（主流）

$$
r_t(\theta)=\frac{\pi_\theta(a_t\mid s_t)}{\pi_{\theta_{\mathrm{old}}}(a_t\mid s_t)}
$$

$$
\begin{aligned}
J^{\mathrm{CLIP}}(\theta)
&=
\mathbb{E}_t\left[
\min\left(
r_t(\theta)A_t,\,
\mathrm{clip}(r_t(\theta),1-\epsilon,1+\epsilon)A_t
\right)
\right]
\end{aligned}
$$

上式中 $A_t$ 表示动作的相对价值（下面会讲），我们希望新策略能让价值在该策略下的期望最大，经重要性采样可得上式，$J$ 对 $\theta$ 的导数即为此时参数网络更新的梯度。$A_t$ 大于 $0$ 时，我们会希望 $\pi_\theta$ 更大，这等价于让 $r_t$ 更大。$E_t$ 是按旧策略采样获得的数据。

在工程中，我们先按照 $\pi_{\mathrm{old}}$ 走若干步，然后开始若干次更新。在每一轮策略更新中固定 $\pi_{\mathrm{old}}$ 仍为采集数据时用的策略（在代码实现里就是对过去的样本直接算术平均），重复若干次下述操作：

当 $A_t>0$，即动作是好的：

* 原本希望 $r_t$ 越大越好，也就是增加该动作概率。
* Clip 限制：一旦 $r_t>1+\epsilon$，公式这一项变成 $(1+\epsilon)A_t$，这是一个常数，导数为 $0$。
* 结果：策略更新停止，防止因为某个动作偶然得到高分，就把它的概率无限提高。

当 $A_t<0$，即动作是不好的：

* 原本希望 $r_t$ 越小越好，也就是降低该动作概率。
* Clip 限制：一旦 $r_t<1-\epsilon$，公式这一项变成 $(1-\epsilon)A_t$，导数为 $0$。
* 结果：策略更新停止，防止因为某个动作导致负分，就过度破坏策略结构。

一旦超出范围，目标函数 $J$ 直接被“抹平”，以最大化目标函数为目的的本轮策略更新“失去动力”，自然就停止了。

## 三、为什么PPO-Clip效果更优？

1. 稳定性：PPO-Penalty 的 $\beta$ 调整虽然也是动态的，但有时候调整滞后，或者震荡，导致训练不稳定。而 PPO-Clip 的截断是硬性的、逐个样本生效的，极其稳健。

2. 计算量：PPO-Penalty 需要计算 $\pi_{\mathrm{new}}$ 和 $\pi_{\mathrm{old}}$ 间的 KL 散度（虽然比 TRPO 的二阶导简单，但也需要算 log 概率的差值），而且两个概率都在变化，故计算开销大。PPO-Clip 只需要做简单的乘法和比大小（min, clamp），计算开销低。

3. 超参数：PPO-Clip 的 $\epsilon$ 通常固定 $0.2$ 就能适配大多数环境（Atari, MuJoCo,机器人）。PPO-Penalty 的 $d_{\mathrm{targ}}$ 和 $\beta$ 初始值则比较敏感。

## 四、损失函数

$$
L_{\mathrm{total}}=-\underbrace{L^{\mathrm{CLIP}}}_{\text{Actor loss}}+c_1\underbrace{L^{\mathrm{VF}}}_{\text{Critic loss}}-c_2\underbrace{S}_{\text{Entropy}}
$$

注意符号的微妙之处：这里假设优化器执行的是梯度下降，即最小化（minimize）。

* $L^{\mathrm{CLIP}}$：我们希望最大化奖励。为了用梯度下降优化，需要加负号，写成 $-L^{\mathrm{CLIP}}$。
* $L^{\mathrm{VF}}$：我们希望最小化预测误差（MSE），所以直接是 $+L^{\mathrm{VF}}$。
* $S$：我们希望最大化熵（鼓励探索）。为了用梯度下降优化，需要加负号，写成 $-S$。

把它们加在一起，PyTorch/TensorFlow 的优化器就可以一键优化所有目标。

反向传播时，Loss的不同项就会将各个梯度分别传给不同模块的对应变量：

```text
输入图像 --> [共享 CNN 层] --> 提取出的特征向量
                         |
                         +-----------------------------+
                         |                             |
                    [Actor 头]                    [Critic 头]
                    输出动作概率                  输出价值 V
```

## 五、优势函数 $A_t$：GAE（Generalized Advantage Estimation）

Advantage $A_t$ 衡量动作 $a_t$ 比该状态下“平均表现”好多少。理论定义为：

$$
A_t=Q(s_t,a_t)-V(s_t)
$$

但在实际计算中，我们无法直接得知 $Q$，只能通过采样估计。

情况一：单步估计（1-step estimation）

如果我们只看一步未来，那么动作 $a_t$ 的 $Q$ 值可以被估计为：

$$
r_t+\gamma V(s_{t+1})
$$

此时 $A_t$ 的估计值直接等于 TD Error：

$$
\hat{A}_t^{(1)}=\underbrace{r_t+\gamma V(s_{t+1})}_{\approx Q(s_t,a_t)}-V(s_t)=\delta_t
$$

PPO 默认使用 GAE 来计算优势函数。这是一个非常精妙的设计，它将 TD Error 做了指数加权移动平均：

$$
\hat{A}_t^{\mathrm{GAE}}
=
\delta_t+(\gamma\lambda)\delta_{t+1}+(\gamma\lambda)^{2}\delta_{t+2}+\cdots
$$

其中 $\lambda$ 是一个范围在 $[0,1]$ 之间的超参数。

通过 $\lambda$ 可以调节 TD Error 的作用：

当 $\lambda=0$ 时，属于高偏差、低方差：

$$
\hat{A}_t=\delta_t=r_t+\gamma V(s_{t+1})-V(s_t)
$$

此时 $A_t$ 完全等于当前的单步 TD Error。

* 优点：方差小，只依赖一步随机奖励 $r_t$。
* 缺点：偏差大，严重依赖 Critic 网络 $V(s_{t+1})$ 的准确性。如果 Critic 没训练好，估计就是错的。

当 $\lambda=1$ 时，属于无偏差、高方差：

$$
\hat{A}_t=\sum_{l=0}^{\infty}\gamma^{l}\delta_{t+l}=\left(\sum_{l=0}^{\infty}\gamma^{l}r_{t+l}\right)-V(s_t)
$$

此时公式展开后，中间的 $V$ 项会相互抵消，最终变成 Monte Carlo Returns（真实回报）减去 Baseline。

* 优点：偏差小，真实回报是最准确的“事实”。
* 缺点：方差极大，因为累加了每一步环境的随机性。

那这里 $A_t$ 是用什么动作计算得到的呢？后面会提到，PPO实际运行时先用老策略走一定步数，再统一计算途中各个 $t$ 时刻的优势函数，再更新。因此 $A_t$ 就是用这些步数的实际动作算出来的。

## 六、在工程中的运行流程（如OpenAI Baselines或Stable Baselines3）

在工程中，走一步更新一次意味着串行计算，GPU利用率极低。基于我们已经通过重要性采样保证了数据的可复用性，我们往往以一个“大循环”为单位：每一次都一次性走若干步（如2048步），收集一批数据，运用这批数据训练更新策略，再扔掉这批数据。

初始化：初始化 Actor 网络 $\pi_\theta$ 和 Critic 网络 $V_\phi$。

大循环（For each iteration）包括四个阶段：

**1. 数据收集阶段（Interaction）**

* 使用当前策略 $\pi_{\theta_{\mathrm{old}}}$ 在环境中运行 $T$ 步，例如 2048 步。
* 收集轨迹数据：

$$
\{s_t,a_t,r_t,s_{t+1},\log\pi_{\mathrm{old}}(a_t\mid s_t)\}
$$

* 利用 Critic 网络计算状态价值 $V(s_t)$。

**2. 优势计算阶段（Advantage）**

* 计算 TD Error：

$$
\delta_t=r_t+\gamma V(s_{t+1})-V(s_t)
$$

* 计算 GAE（Generalized Advantage Estimation）$\hat{A}_t$。这是一个递归公式，用来在偏差和方差之间做平衡。

注：在收集数据的过程中，一般我们会顺便把 $V(s_t)$ 算出来，这是因为在 PPO 的工程实现中，Actor 和 Critic 通常共享部分底层网络（CNN/MLP）。当让 Actor 选择动作 $a_t$ 时，必须把 $s_t$ 喂进网络。既然数据已经流过网络了，顺便让 Critic 输出一下 $V(s_t)$，几乎不增加额外的计算成本。如果不存下来，等到训练阶段，还得把 $s_t$ 重新喂一遍网络来得到 $V(s_t)$ 用于计算优势，重复计算，浪费 GPU。

注：优势是在走完动作步后、更新策略梯度前统一计算的，GAE是TD Error加权后，再一直从t累加到2048得到的。

**3. 优化更新阶段（Optimization）**

* 重要：此时 $\pi_{\theta_{\mathrm{old}}}$ 固定不动，作为分母；优化的是新的 $\pi_\theta$，作为分子。
* 将收集到的 $T$ 个数据打乱，分成多个 mini-batch，例如每个 batch 64 个数据。
* Epoch 循环，例如重复 10 次。

对每个 mini-batch：

* 计算新概率比率：

$$
r_t(\theta)=\frac{\pi_\theta(a\mid s)}{\pi_{\mathrm{old}}(a\mid s)}
$$

* 计算 Clip 损失 $L^{\mathrm{CLIP}}$。
* 计算 Critic 的价值损失：

$$
L^{\mathrm{VF}}=\left(V_\phi(s_t)-V_{\mathrm{target}}\right)^{2}
$$

* 计算熵正则项 $S$，用于鼓励探索。
* 计算总损失：

$$
L=-L^{\mathrm{CLIP}}+c_1L^{\mathrm{VF}}-c_2S
$$

* 反向传播，更新 $\theta$ 和 $\phi$。

**4. 同步策略**

* 本轮更新结束后，令：

$$
\pi_{\theta_{\mathrm{old}}}\leftarrow\pi_\theta
$$

* 清空数据缓冲区，进入下一次大循环。

假设参数设置如下：

* `n_steps`，缓冲区大小：$2048$。
* `batch_size`，小批次大小：$64$。
* `n_epochs`，复用次数：$10$。

在一个“大循环”里，反向传播发生的次数是：

1. 数据分批：2048 个数据被分成：

$$
2048/64=32
$$

个 mini-batch。

2. 一轮遍历：这 32 个 mini-batch 会被依次喂给 GPU，产生 32 次反向传播。
3. 多轮复用：重复跑 10 个 epoch。
4. 总次数：

$$
32\times 10=320
$$

因此，一个大循环中一共产生 320 次反向传播。

## 参考文献

- Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). [Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347). arXiv:1707.06347.
