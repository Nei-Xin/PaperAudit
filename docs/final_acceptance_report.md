# PaperAudit 最终验收报告（评测体系）

## 验收范围

本验收覆盖开发集、摘要留出集、跨领域留出集和正文证据诊断集。评测规则不按论文 ID、样本 ID 或论文专属术语分支；所有 PDF 均校验页数与 SHA-256，金标证据通过本地 chunk 自动映射。

## 当前结果

| 数据集 | 样本数 | Top-5 召回 | 标签准确率 | 错误类型准确率 | 风险准确率 | ABSTAIN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 开发集（5 篇） | 40 | 100% | — | — | — | — |
| 原留出集（4 篇） | 32 | 100% | 90.62% | 82.61% | 90.62% | 0% |
| 扩展跨领域集（3 篇） | 24 | 87.5% | 95.83% | 93.75% | 95.83% | 0% |
| 第二批跨领域集（DQN/U-Net/Word2Vec，3 篇） | 24 | 91.67% | 87.5% | 71.43% | 100% | 0% |
| 外部应用诊断集（VAE/Neural ODE/SRCNN，3 篇） | 18 | 77.78% | 94.44% | 91.67% | 94.44% | 0% |
| 外部应用诊断集第二批（NTM/XGBoost/DeepSpeech，3 篇） | 18 | 94.44% | 94.44% | 91.67% | 94.44% | 0% |
| 正文证据集（3 篇） | 24 | 91.67% | 91.67% | 88.24% | 95.83% | 0% |
| 概念/应用诊断集 | 12 | 58.33% | 未跑 API | 未跑 API | 未跑 API | — |
| 最终独立留出集（6 篇全新论文） | 48 | 87.50%（离线） | 仅作最终泛化验收 | 仅作最终泛化验收 | 仅作最终泛化验收 | 100%（离线为 ABSTAIN） |

当前工作区完整自动化测试：`155 passed`。

方向一自动有效性实验已补齐一轮完整回放：固定测试集 40 条样本在相同配置下重复调用真实 API 3 次，标签两两一致率 98.33%，平均论文分标准差 0.5468，各次标签准确率为 95.00%/97.50%/97.50%，ABSTAIN 均为 0%。另在每篇论文 1 条支持样本和 1 条错误样本上构造 10 组成对端到端对抗样本（篇幅扩写、术语堆砌、伪造引用、重复段落、Prompt 注入），评分上升和风险降低均为 0，对抗攻击成功率 0%。详细结果见 [`eval/validation_report.md`](../eval/validation_report.md)、[`eval/validation_full/validation.json`](../eval/validation_full/validation.json) 和 [`eval/validation_adversarial/adversarial_summary.json`](../eval/validation_adversarial/adversarial_summary.json)。这些是自动化稳定性和鲁棒性证据，不能替代独立人工双评审一致性。

统一回归已固化为 [`eval/run_regression.py`](../eval/run_regression.py)，默认离线运行全部固定评测集并检查召回门槛；本次结果写入 [`results_regression_latest/summary.md`](../eval/results_regression_latest/summary.md)，总体为 `PASS`。规则冻结和变更准入条件见 [`REGRESSION_BASELINE.md`](../eval/REGRESSION_BASELINE.md)。

本次真实 API 统一验收使用相同的固定样本和 Top-5 配置，结果写入 [`results_regression_actual_latest/summary.md`](../eval/results_regression_actual_latest/summary.md)，总体召回门槛为 `PASS`。各集 `ABSTAIN` 均为 0%；标签准确率范围为 83.33%–95.83%，错误类型准确率范围为 64.29%–94.12%，风险准确率范围为 90.62%–100%。概念/应用和跨领域集的错误类型波动保留为诊断信息，不触发规则解冻。

第二批跨领域集覆盖强化学习、医学图像分割和词表示三个新领域；24 条样本全部完成 PDF 版本、SHA-256 和金标 chunk 映射，Top-5 离线召回率为 91.67%。真实 API 评测标签准确率 87.5%、错误类型准确率 71.43%、风险准确率 100%、`ABSTAIN` 0%。

将 Adam/Dropout/NMT、wav2vec 2.0/GCN/DDPM 和本批 DQN/U-Net/Word2Vec 三批跨领域真实 API 预测合并（72 条）后，标签准确率为 94.44%，宏平均 F1 为 0.9261，错误类型准确率为 89.36%，风险准确率为 98.61%，`ABSTAIN` 为 0%。这只是跨批次稳定性观察值，不替代按批次留出的验收结果。

新增的外部应用诊断集覆盖 VAE、Neural ODE 和 SRCNN，共 18 条样本。离线 Top-5 召回率为 77.78%，但真实 API 标签准确率为 94.44%、错误类型准确率为 91.67%、风险准确率为 94.44%、`ABSTAIN` 为 0%；其中 6 条 `external_hallucination` 的标签和错误类型均为 100%，说明主要剩余问题是外部应用证据召回，而不是判定边界。

合并四批跨领域真实 API 预测（90 条）后，标签准确率 94.44%，宏平均 F1 0.9367，错误类型准确率 89.83%，风险准确率 97.78%，`ABSTAIN` 0%。

外部应用诊断第二批覆盖 Neural Turing Machines、XGBoost 和 DeepSpeech，共 18 条样本。离线 Top-5 召回率 94.44%，真实 API 标签准确率 94.44%、错误类型准确率 91.67%、风险准确率 94.44%、`ABSTAIN` 0%；6 条外部幻觉样本的标签/错误类型准确率均为 100%，证据召回率 83.33%。

将已有三批跨领域和两批外部应用诊断的真实 API 预测合并（108 条）后，标签准确率 94.44%，宏平均 F1 0.9367，错误类型准确率 90.14%，风险准确率 97.22%，`ABSTAIN` 0%。

统一离线回归结果：开发集 100%、原留出集 100%、扩展集 100%、第三批跨领域集 87.5%、正文集 91.67%、概念/应用集 58.33%、外部应用第一批 77.78%、外部应用第二批 94.44%。现有核心集合均未出现回归。

最终独立留出集固定为 6 篇此前未出现在任何评测 split 的论文、48 条原子论断，论文级隔离检查结果为 `isolated=true`，所有 48 条样本均映射到本地真实 PDF chunk。离线 Top-5 召回率为 87.50%，达到预注册的 85% 门槛；该结果只作为最终泛化能力证据，不反向修改冻结规则。当前累计评测规模为 28 篇论文、264 条原子论断。

真实 API 最终验收（Top-5，`PAPERAUDIT_JUDGE_BATCH_SIZE=8`，无 oracle evidence）结果：标签准确率 83.33%，宏平均 F1 0.8005，错误类型准确率 78.79%，风险等级准确率 83.33%，`ABSTAIN` 0%，证据召回率 87.50%。按构造类型，直接矛盾标签/错误类型均为 100%，支持样本标签准确率 93.33%；数字变更和过度泛化仍是主要误差来源。该结果是冻结规则下的独立泛化测量，不触发规则调整。

评测输出现在同时提供 `by_category`（method / experiment / configuration / metric 等）和 `by_construction`（supported、数字变更、条件删减、外部应用等）分层指标，用于区分“检索漏召回”和“判断边界错误”。分层结果是诊断信息，不改变总体验收口径，也不引入论文专属规则。

最终留出集中的代表性成功、标签边界错误、错误类型优先级冲突和检索漏召回案例已整理到 [`docs/typical_cases.md`](typical_cases.md)，每个案例均保留论断、金标、系统预测、原文依据和归因。

## 已验收能力

- PDF 断词、连字、词形和复合词归一；
- 摘要、作者块和正文资源配置检索；
- 配置实体与资源数值联合匹配；
- 数字—指标上下文匹配；
- `missing_condition`、`overgeneralization`、`contradiction` 和 `external_hallucination` 边界提示；
- 有限二次/三次裁决与多数合并；
- 批量或单条 JSON 格式异常的自动降级；
- 无效证据编号的统一校验与 `ABSTAIN` 保护。

## 未通过项与限制

概念/应用诊断集的离线召回率只有 58.33%，说明外部应用类主张（例如把图模型说成视觉模型）在证据检索上仍然困难。这组样本应作为下一阶段专项诊断集，不能用当前摘要/正文结果代表整体概念核验能力。

本轮分层诊断进一步显示：概念/应用集的 `method` 召回为 100%，`dataset_setup` 仅 16.67%；按构造类型看，`supported` 为 83.33%、`contradiction` 为 66.67%，`external_hallucination` 为 0%。因此下一阶段应优先补充更多跨论文、跨领域的外部应用和数据集语境样本，先验证问题是否稳定，再决定是否需要新的通用召回机制。

正文集的真实指标达到当前门槛，但仍有少量硬件配置、概念应用和指标语义边界波动。验收结论为：核心审核流程可用，概念/应用深层检索仍需后续迭代；不建议在没有新增证据类型样本前继续增加启发式权重。

## 可复现结果

- [原留出集结果](../eval/results_holdout_actual_v5/metrics.json)
- [跨领域结果](../eval/results_broad_actual_v3/metrics.json)
- [正文结果](../eval/results_body_actual_v4/metrics.json)
- [概念/应用离线结果](../eval/results_concept_retrieval_v1/metrics.json)
- [正文分层诊断结果](../eval/results_body_retrieval_v9/metrics.json)
- [概念/应用分层诊断结果](../eval/results_concept_retrieval_v2/metrics.json)
- [第二批跨领域离线结果](../eval/results_cross_retrieval_v2/metrics.json)
- [第二批跨领域真实 API 结果](../eval/results_cross_actual_v2/metrics.json)
- [外部应用诊断集离线结果](../eval/results_external_retrieval_v1/metrics.json)
- [外部应用诊断集真实 API 结果](../eval/results_external_actual_v1/metrics.json)
- [外部应用诊断第二批离线结果](../eval/results_external_retrieval_v2/metrics.json)
- [外部应用诊断第二批真实 API 结果](../eval/results_external_actual_v2/metrics.json)
- [完整评测报告](../eval/retrieval_improvement_report.md)
- [最终独立留出集元数据](../eval/final_holdout_papers.json)
- [最终独立留出集样本](../eval/final_holdout_resolved_samples.jsonl)
- [最终留出集隔离检查脚本](../eval/check_holdout_isolation.py)
- [含最终留出集的离线统一回归摘要](../eval/results_regression_final_holdout/summary.md)
- [最终留出集真实 API 指标](../eval/results_final_holdout_actual/metrics.json)
