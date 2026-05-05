---
title: "29.5 OpenClaw-RL：个人Agent的持续学习（论文）"
source_docx: "第4部分 大模型智能体与持续学习/29.基于梯度与超网络的持续学习/29.5 OpenClaw-RL：个人Agent的持续学习（论文）.docx"
status: "auto-converted"
ocr: "manual reconstruction completed"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 29.5 OpenClaw-RL：个人Agent的持续学习（论文）


> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

## 一、核心思想

现有的智能体 RL 系统通常忽略了交互后产生的**下一状态信号（next-state signals）**，例如用户的回复、工具输出、环境的状态变化等，仅将其作为生成下一步动作的上下文。这种做法无法有效了解和利用有价值的在线反馈信息被浪费：

- **评估性信号（Evaluative signals）**：下一状态隐式地对前一个动作进行了质量打分。例如，用户对智能体重新提问代表不满意，测试用例通过代表成功，而代码报错代表失败。
- **指导性信号（Directive signals）**：除了单纯的打分，下一状态通常还会具体指出修改建议。例如，详细的错误日志、或者用户直接指出“你应该先检查文件再修改”，这些 token 级别提供了明确的定向优化信号。

## 二、系统架构

为了实现在线、实时的训练并避免单点阻塞，OpenClaw-RL 基于异步框架构建了**完全解耦（fully decoupled）**的系统架构。它包含四个独立运行的异步循环：

1. **策略服务（Policy Serving）**：由 SGLang 驱动，负责不同场景、不同用户请求或环境交互的在线推理服务。
2. **环境服务器（Environment Servers）**：对于个人智能体，环境即用户的本地设备，通过加密 API 与 RL 服务器通信；对于通用智能体，环境部署在云服务上以支持大规模并行计算。
3. **奖励裁判（Reward Judging）**：利用 SGLang 或 API 部署过程奖励模型（PRM），对收集到的历史交互进行分步或整段文本提示。
4. **策略训练（Policy Training）**：由 Megatron 引擎负责，在后台处理样本队列并进行模型权重的平滑更新（graceful weight update），全程不会中断前端的推理服务。

## 三、核心算法

### （一）针对评估性信号的二进制强化学习

该方法将评估信号转化为二值奖励，并用强化学习更新策略：

1. **工作流**：
   - 智能体在状态 $s_t$ 下生成响应动作 $a_t$。
   - 环境或用户反馈产生下一状态 $s_{t+1}$。
   - 系统调用 PRM 模型，依据 $s_t+1$ 到 $a_t$ 的质量进行评估，输出初步分数 $r_t$。
   - 通过多数投票（majority vote）或规则化的最终判断，把反馈转化为 $0/1$ 奖励。
   - 直接把最终奖励作为该步的优势函数 $A_t=r_{\mathrm{final}}$，并将其送入训练队列。
2. **数学公式**：
   该方法采用标准的带有非对称裁剪的 PPO 代理目标函数：

$$
L_{\mathrm{PPO}} =
-\mathbb{E}_t
\left[
\min\left(
\rho_t A_t,
\mathrm{clip}(\rho_t,1-\epsilon,1+\epsilon_{\mathrm{high}})A_t
\right)
\right]
$$

其中，$\rho_t=\frac{\pi_\theta(a_t\mid s_t)}{\pi_{\mathrm{old}}(a_t\mid s_t)}$ 是新旧策略的概率比率。

### （二）针对引导性信号的蒸馏

该方法将包含丰富纠错信息的指导性信号，转化为 token 级别的定向监督信号。

1. **工作流**：
   - **提取提示（Hindsight Hint Extraction）**：教师模型对 $s_t$ 和 $s_{t+1}$ 进行分析，如果观察到动作的优化建议，即提取为一个提示 $h$，如果没有则返回 $h=\varnothing$。
   - **过滤与选择（Quality Filtering）**：为了保证训练信号的纯度，系统会过滤掉无效样本；在多个有效 hint 中，选择长度最长、信息量最大的一个。
   - **构建增强上下文（Enhanced Teacher Construction）**：将提取出的 hint 以特定格式（如 `[User's hint / instruction]\n[hint]`）附加到上一步的系统上下文中，构造出一个包含了“事后诸葛亮”信息的增强状态 $s_{\mathrm{enhanced}}$。
   - **计算 token 级别优势**：让策略模型在原始状态 $s_t$ 和增强状态 $s_{\mathrm{enhanced}}$ 下分别计算原动作 $a_t$ 中每个 token 的对数概率，并求差值。
2. **数学公式**：
   token 级别的优势计算公式为：

$$
A_t =
\log \pi_{\mathrm{teacher}}(a_t\mid s_{\mathrm{enhanced}})
-
\log \pi_\theta(a_t\mid s_t)
$$

这里是在比较学生上下文和教师上下文下生成学生动作的概率，只是评价学生模型生成的token的好坏，并没有让教师生成新token并进行KL散度损失计算。这和在线自蒸馏并不一样。

为什么A_t取这个值：

在深度学习中，让学生模型 $\pi_\theta$ 去学习教师模型 $\pi_{\mathrm{teacher}}$ 的行为，最标准的方法是最小化它们分布之间的 KL 散度：

如果我们对 KL 散度求梯度，即我们要更新学生模型参数 $\theta$ 的方向，其核心可以近似推导为：

$$
\nabla_\theta D_{\mathrm{KL}}(\pi_\theta\|\pi)
\approx
-
\left(
\log \pi_{\mathrm{teacher}}(a_t)
-
\log \pi_\theta(a_t)
\right)
\nabla_\theta \log \pi_\theta(a_t)
$$

现在再看强化学习。标准的策略梯度（Policy Gradient）算法更新参数 $\theta$ 的基本公式是：

$$
\nabla_\theta L_{\mathrm{PG}}
= -A_t \cdot \nabla_\theta \log \pi_\theta(a_t)
$$

两式对应即得。值得注意的是，真实的KL散度梯度含有期望项，但是在实际的大模型工程中，对每个步骤都计算全词表的期望会导致计算量爆炸。考虑到a_t就是我们在这一步由学生模型策略真实采样生成的 Token，所以a_t本身就可以作为这个期望的一个无偏估计量。

大语言模型的最后一层是没有被归一化的分数，即 logits。当我们使用 Softmax 函数把 logits 转化为概率时：

$$
P(z_i)=\frac{e^{\mathrm{logit}_i}}{\sum_j e^{\mathrm{logit}_j}}
$$

对其取对数：

$$
\log P(z_i)=\mathrm{logit}_i-\log\left(\sum_j e^{\mathrm{logit}_j}\right)
$$

可以看到，对数概率本质上就是模型输出的 logit 值减去一个常数归一项。因此，logit 越高，模型生成该 token 的倾向越强；反向传播会把优势 $A_t$ 作用到对应 token 的 logit 上。

### （三）联合优化

Binary RL 能够覆盖所有带有评分的交互轮次，而 OPD 能够在用户或环境给出明确指导时提供高分辨率的逐 token 纠正。由于两者共享相同的 PPO 损失函数架构，论文提出通过直接加权两者的优势函数来进行联合优化：

$$
A_t =
\omega_{\mathrm{binary}} r_{\mathrm{final}}
+
\omega_{\mathrm{opd}}
\left(
\log \pi_{\mathrm{teacher}}(a_t\mid s_{\mathrm{enhanced}})
-
\log \pi_\theta(a_t\mid s_t)
\right)
$$

其中，$\omega_{\mathrm{binary}}$ 与 $\omega_{\mathrm{opd}}$ 用于控制终局评分与指导性蒸馏信号的相对权重。

## 参考文献

- OpenClaw. (2026). [OpenClaw-RL project](https://github.com/openclaw/openclaw).
