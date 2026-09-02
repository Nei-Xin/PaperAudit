# PaperAudit 最终留出集典型案例

本文从冻结的最终独立留出集选择 5 个代表案例。论断和金标来自 `eval/final_holdout_resolved_samples.jsonl`，系统预测来自 `eval/results_final_holdout_actual/predictions.jsonl`；案例只做归因整理，不修改金标或冻结结果。

## Case 1：直接矛盾识别正确

- 样本：`np_final_003`
- 报告论断：Neural Processes 是确定性模型，不产生函数分布。
- 原文依据：第 1 页，`Like GPs, NPs define distributions over functions`。
- 金标：`CONTRADICTED / contradiction / high`
- 系统：`CONTRADICTED / contradiction / high`
- 归因：候选证据直接给出“函数上的分布”，与“确定性且不产生分布”形成明确反义关系。该类有直接否定证据的错误是当前系统最稳定的场景。

## Case 2：过度泛化被判成直接冲突

- 样本：`np_final_004`
- 报告论断：NP 的推理复杂度始终是常数，与上下文和目标点数量无关。
- 原文依据：第 1 页，`inference with a trained NP corresponds to a forward pass in a deep NN, which scales with O(n+m)`。
- 金标：`PARTIALLY_SUPPORTED / overgeneralization / medium`
- 系统：`CONTRADICTED / numeric_or_metric_mismatch / high`
- 归因：系统正确发现了 `O(n+m)` 与“常数复杂度”的冲突，但把复合论断中的错误部分提升为整条直接冲突，并错误归入数字/指标问题。该案例暴露的是标签粒度和错误类型优先级边界，而不是检索失败。

## Case 3：同一论断包含两个错误时优先级不稳

- 样本：`l2l_final_007`
- 报告论断：学习优化器在所有任务上提升 50% 的性能。
- 原文依据：第 1 页，`outperform generic, hand-designed competitors on the tasks for which they are trained`。
- 金标：`CONTRADICTED / numeric_or_metric_mismatch / high`
- 系统：`PARTIALLY_SUPPORTED / overgeneralization / medium`
- 归因：“所有任务”是范围扩大，“50%”是原文不存在的定量变更。系统抓住了前者但漏掉更高优先级的数字错误，导致标签和风险同时降级。后续应优先验证通用的多错误优先级规则，而不是添加论文特例。

## Case 4：外部幻觉与过度泛化边界混淆

- 样本：`nas_final_008`
- 报告论断：NAS 已证明能自动发现适用于所有领域的最优架构。
- 原文依据：第 1 页，`neural networks are still hard to design`。
- 金标：`NO_SUPPORT_FOUND / external_hallucination / high`
- 系统：`PARTIALLY_SUPPORTED / overgeneralization / medium`
- 归因：系统从论文在图像分类和语言建模中的结果推断“所有领域”是范围扩大，但金标认为“适用于所有领域的最优架构”引入了论文未提供的新事实。该边界在缺少同主体直接否定证据时仍不稳定。

## Case 5：证据漏召回引起支持样本误报

- 样本：`dip_final_006`
- 报告论断：DIP 通过在单个退化图像上拟合生成器网络来恢复图像。
- 原文依据：第 2 页，`we fit a generator network to a single degraded image`。
- 金标：`SUPPORTED / none`
- 系统：`PARTIALLY_SUPPORTED / missing_condition / medium`
- 检索命中：`false`
- 归因：系统候选中缺少包含“single degraded image”的金标块，因此把原本完整的论断误判为条件缺失。这是典型的检索错误向判断器传播，说明评测必须同时报告证据召回率和标签准确率。

## 模式总结

1. 有明确反义证据的直接矛盾最稳定。
2. 数字变更、范围扩大和外部幻觉同时出现时，单一主要错误类型的优先级仍会波动。
3. 检索没有命中金标证据时，即使语义判断合理，也可能产生支持样本误报。
4. 因此最终结果同时保留 `retrieval_hit_rate`、标签、错误类型和风险指标，不用单一总分掩盖失败来源。
