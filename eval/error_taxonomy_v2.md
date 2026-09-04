# PaperAudit 错误类型规范 v2

本规范用于下一版评测标注与通用裁决提示词，不覆盖或改写已经冻结的 v1 金标和历史结果。对应的逐样本审查记录见 `error_type_annotation_review_v2.jsonl`。

用于提示词定向验证的样本位于 `error_type_v2_diagnostic_samples.jsonl`，回归控制样本位于 `error_type_v2_control_samples.jsonl`，共用论文清单 `error_type_v2_diagnostic_papers.json`。这些样本来自既有诊断集，不再视为 v2 独立留出集，也不得用于声称新的泛化能力。

## 判定顺序

1. **先保证论断原子化**：一句话同时包含两个可独立真假的事实时，先拆分，再分别判断。
2. **先判断证据是否足够**：原文仅说明“在条件 X 下成立”，不能自动推出“X 是必要条件”；原文列出一个实验设置，也不能自动推出未列出的设置绝对没有发生。
3. **精确数值或指标冲突优先**：同一主体、设置和指标下，论断与证据给出不同的明确数值、数量、时间或资源量时，使用 `numeric_or_metric_mismatch`。
4. **直接命题冲突其次**：证据明确否定同一主体和设置下的核心命题，且不属于精确数值冲突时，使用 `contradiction`。
5. **核心事实部分成立时再区分边界错误**：
   - 遗漏论文明确要求的必要设置或适用条件，使用 `missing_condition`；
   - 把有限任务、数据集或设置扩展为“全部、所有、总是”，使用 `overgeneralization`。
6. **新增内容缺乏证据时使用外部臆测**：论断新增论文未讨论的主体、数据集、应用、机制或结果，且候选证据没有直接否定同一命题时，使用 `external_hallucination`。

## 标签和风险映射

| 错误类型 | 标签 | 风险 |
| --- | --- | --- |
| 无错误 | `SUPPORTED` | `none` |
| `missing_condition` | `PARTIALLY_SUPPORTED` | `medium` |
| `overgeneralization` | `PARTIALLY_SUPPORTED` | `medium` |
| `numeric_or_metric_mismatch` | `CONTRADICTED` | `high` |
| `contradiction` | `CONTRADICTED` | `high` |
| `wrong_attribution` | `CONTRADICTED` | `high` |
| `external_hallucination` | `NO_SUPPORT_FOUND` | `high` |
| 证据不足以可靠判定 | `ABSTAIN` | `none` |

## 边界示例

- “7 个任务全部超过基线”，证据为“6 个任务超过基线”：明确数量不同，优先使用 `numeric_or_metric_mismatch`，而不是 `overgeneralization`。
- “所有数据集都有效”，证据只覆盖若干数据集且核心结果在这些数据集成立：使用 `overgeneralization`。
- “不需要条件 X”，证据明确要求条件 X：使用 `contradiction`；证据仅展示在 X 下的结果但未声明必要性时，不得据此推断矛盾。
- “方法使用论文未讨论的数据集 Y”：没有直接排除 Y 的证据时，使用 `external_hallucination`；若论文明确声明只使用互斥的数据集集合，再使用 `contradiction`。
- “方法只适用于图像且不适用于语言”包含两个可独立判断的事实，应拆分后标注。

## 变更准入

- v2 勘误不得原地覆盖冻结 v1 文件；通过独立文件保留旧金标、建议值和理由。
- `manual_review` 与 `rewrite` 项不得用于计算新的准确率基线，直到复核完成。
- 通用提示词只根据跨论文重复出现、且在 v2 开发样本中确认的边界问题修改。
- `final_holdout` 继续只用于最终验收，不参与规范或提示词调优。

## 2026-09-04 定向验证

在 `gpt-5.6-luna`、`reasoning_effort=high`、批大小 6、Top-5 配置下：

- 6 条确认金标样本的标签、错误类型、风险和证据召回均为 100%，结果保存在 `results_error_type_v2_diagnostic_actual/`；
- 7 条既有正确控制样本的标签、错误类型、风险和证据召回均为 100%，结果保存在 `results_error_type_v2_control_actual/`；
- 另一次包含两条争议样本的探索结果保存在 `results_error_type_v2_prompt_actual/`，不作为通过指标。

该结果只证明本次最小提示词改动在既有诊断样本上有净收益且未发现直接控制回归，不构成独立泛化结论。

## 正式 v2 金标集

2026-09-04 完成人工复核后，正式金标集生成到 `error_type_v2/`，冻结的 v1 文件保持不变。生成器 `build_error_type_v2_dataset.py` 会校验标签映射、样本与论断 ID 唯一性、论文 PDF SHA-256，以及每条金标证据 chunk 是否存在。

| 数据集 | v1 来源样本数 | v2 样本数 | 说明 |
| --- | ---: | ---: | --- |
| `holdout` | 32 | 32 | 应用已确认重标 |
| `broad` | 24 | 24 | 应用已确认重标 |
| `body` | 24 | 24 | 应用已确认重标 |
| `cross_v2` | 24 | 26 | 2 条复合论断各拆为 2 条原子论断 |
| 合计 | 104 | 106 | 7 条重标，2 条复合论断替换为 4 条原子论断 |

审查清单最终状态为 `keep=8`、`relabel=7`、`rewrite=2`，不再包含 `manual_review` 项。

## 2026-09-04 完整真实 API 回归

统一回归使用 `gpt-5.6-luna`、`reasoning_effort=high`、批大小 6、Top-5；结果保存在 `results_error_type_v2_regression_actual_20260904/`。四组检索召回均达到各自门槛，且没有 `ABSTAIN`。

| 数据集 | 样本数 | 标签准确率 | 标签 Macro-F1 | 错误类型准确率 | 风险准确率 | 证据召回率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `holdout` | 32 | 93.75% | 90.75% | 91.30% | 93.75% | 100.00% |
| `broad` | 24 | 87.50% | 84.29% | 81.25% | 100.00% | 87.50% |
| `body` | 24 | 83.33% | 70.83% | 75.00% | 91.67% | 91.67% |
| `cross_v2` | 26 | 96.15% | 95.56% | 87.50% | 100.00% | 100.00% |
| 合并 | 106 | 90.57% | 88.04% | 84.51% | 96.23% | 95.10% |

错误类型仍有以下边界波动：`gan_005`、`unet_007`、`wav_006`、`gcn_003`、`ddpm_007`、`wav_body_003`、`wav_body_005`、`gcn_body_007`、`ddpm_body_004`、`dqn2_008a`、`unet2_005`。四条拆分样本中，`dqn2_008b`、`w2v2_006a`、`w2v2_006b` 全字段正确；`dqn2_008a` 被判为 `contradiction`，而金标为 `external_hallucination`。

与上一轮 104 条 v1 四集结果相比，部分指标明显变化，但 v2 已重标并把 2 条复合论断拆为 4 条，且真实 API 存在运行波动，因此这些差异不能解释为纯模型提升或新的独立泛化证据。当前不针对单条边界错例继续增加规则。
