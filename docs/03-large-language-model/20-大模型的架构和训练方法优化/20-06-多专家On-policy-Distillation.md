---
title: "20.6 多专家On-policy Distillation"
source_docx: "第3部分 大语言模型/20.大模型的架构和训练方法优化/20.6 多专家On-policy Distillation.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 20.6 多专家On-policy Distillation

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

DeepSeek-V4采用了多专家On-policy Distillation的方法，先基于预训练模型，用SFT和RL训练多个领域专家，再将其知识蒸馏到统一的学生模型中。

## 一、领域专家模型训练

基于预训练模型，用SFT和GRPO训练一批领域专家模型，领域包括数学、代码、Agent、指令跟随等。业界一般还会给每个领域训练多种推理强度的子版本，分别对应Non-think、Think、Think Max，三种模式在RL时用不同的length penalty和context window。

做Agent类专家时还引入了 Quick Instruction 机制，聊天产品里有很多附加任务，比如判断是否触发搜索、识别意图。传统做法是另一个小模型做这些，导致每次上下文变化，要重新进行预填充。V4 的做法是给输入序列直接附一组special token，每个token对应一个附加任务，复用现成的KV cache，降低首字延迟。

## 二、On-Policy Distillation

运用On-Policy蒸馏方法，把所有专家的知识融合到统一的学生模型里。相比于Off-policy方法而言，On-policy更能避免灾难性遗忘。具体而言，即让学生在自己生成的轨迹上学习多个专家模型的输出概率分布。

## 参考文献

暂无已核验参考文献。
