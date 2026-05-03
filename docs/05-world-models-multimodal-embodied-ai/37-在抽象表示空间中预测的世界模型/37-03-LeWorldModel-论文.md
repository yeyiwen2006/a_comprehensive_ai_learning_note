---
title: "37.3 LeWorldModel（论文）"
source_docx: "第5部分 世界模型、多模态生成与具身智能/37.在抽象表示空间中预测的世界模型/37.3 LeWorldModel（论文）.docx"
status: "auto-converted"
ocr: "disabled; image content awaits manual reconstruction"
license: "CC BY-NC-SA 4.0"
local_only: false
---

# 37.3 LeWorldModel（论文）

> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。

> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。

## 一、问题背景

> [图片内容待重建：img-db14c4adf18e-0001] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
Yann LeCun等提出了LeWorldModel，通过极为简洁的方法有效解决了表征坍塌问题，并在小参数模型上获得了较好的效果。

## 二、模型架构

> [图片内容待重建：img-db14c4adf18e-0002] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 三、损失函数

> [图片内容待重建：img-db14c4adf18e-0003] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-db14c4adf18e-0004] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
SIGReg正则化的原理：

> [图片内容待重建：img-db14c4adf18e-0005] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-db14c4adf18e-0006] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-db14c4adf18e-0007] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-db14c4adf18e-0008] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
> [图片内容待重建：img-db14c4adf18e-0009] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
SIGReg不会成为计算瓶颈的原因：

> [图片内容待重建：img-db14c4adf18e-0010] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 四、工作流

### （一）训练阶段

> [图片内容待重建：img-db14c4adf18e-0011] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
### （二）推理阶段用于模型预测控制时

> [图片内容待重建：img-db14c4adf18e-0012] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
## 五、工作亮点

> [图片内容待重建：img-db14c4adf18e-0013] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
此外，在不引入隐空间直道化损失的情况下，直道化程度较以前的V-JEPA显著提升。

值得注意的是，论文在消融实验中发现，引入重建损失反而引起了性能的下降。

## 六、仍存在的局限性

1.依赖动作数据

LeWM的预测器不是只看视频帧，而是显式建模：

> [图片内容待重建：img-db14c4adf18e-0014] 原 Word 此处有图片。为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。
所以它不是一个纯粹从无动作视频中学习的video prediction model。论文最后的局限性也明确提到：当前end-to-end latent world models依赖action labels来预测未来状态，未来方向可以用inverse dynamics学习未来动作表征，减少对显式动作标注的依赖。但要注意，“action labels”不一定是人工标注。机器人或仿真控制任务里，动作通常来自控制器日志，比如关节速度、末端执行器控制量、环境action command，这比人工标注便宜得多。

2.难以捕捉细粒度旋转与姿态信息

LeWM的紧凑latent能捕捉主要动力学和位置结构，但对3D场景中的细粒度旋转、姿态、末端执行器朝向等变量编码不足；这在OGBench-Cube的rollout和probing中体现明显。

3.规划视野受限

随着自回归预测步数增加，预测误差逐渐累积，长程规划质量下降。论文也因此采用MPC：不是一次性规划很长时间，而是只执行前几个动作，然后根据新观测重新规划。

4.高度依赖数据覆盖率

LeWM是offline、reward-free的方法，训练依赖固定数据集中的 observation-action trajectories。论文提到，这些轨迹不要求是最优策略产生的，但需要充分覆盖环境动力学。局限性部分也说，它仍依赖具有sufficient interaction coverage的离线数据，而这种数据在实际应用中可能昂贵或难收集。

这点尤其重要：LeWM 的 planning 成功并不意味着它可以在训练分布外任意泛化。如果离线数据没有覆盖某些状态、接触模式、物体姿态、动作后果，世界模型就很难可靠预测，规划也容易失败。

5.SIGReg在极简环境中的正则化匹配挑战

LeWM在Push-T和Reacher上表现很好，但在简单的Two-Room环境中不如PLDM和DINO-WM。论文给出的可能解释是：Two-Room数据多样性低、内在维度低，而SIGReg会鼓励embedding匹配高维各向同性高斯分布，这可能让表示结构变差，进而影响规划。

不过，论文附录又补充了一个nuance。简单环境Two-Room中，LeWM虽然下游规划差一些，但probing指标上并不一定差，这说明简单环境的planning gap不一定完全来自“潜在表征信息不足”，也可能与动力学建模或规划过程有关。

## 参考文献与引用线索

> 本节由脚本自动检索正文中的引用线索，可能不完整；未能确定来源的位置会在下方标为待补引用。

### 待补引用或版权检查

- [待补引用] 本文标题标记为论文笔记，但未自动发现原论文链接、arXiv/DOI、作者或年份，建议人工补充。
- [待补引用] 本文含 Word 内嵌图片；开源版未上传图片。若图片来自教材、论文或技术报告，建议人工确认授权、补充来源或重画。
- [待补引用] 未自动检索到明确参考文献线索，建议人工补充可追溯来源。
