# 方向一基准样本集

## 数据来源

`papers.json` 收录 5 篇公开 arXiv 论文及固定版本链接：Transformer、BERT、ResNet、LoRA、CLIP。样本证据主要来自每篇论文首页摘要，`source_page` 固定为 PDF 第 1 页，`source_quote` 保留用于人工复核。

## 构造方式

每篇论文 8 条论断，共 40 条：

- 4 条原文支持的事实或方法论断；
- 数字/指标变更；
- 结果归属或方法含义相反；
- 删除实验条件或扩大适用范围；
- 论文外事实、无支持论断和对抗性表述。

`construction` 字段记录样本生成方式，`gold_*` 字段是人工金标。当前集是 P1 的第一版基准，正式实验前应由两名评审者独立复核，并把分歧记录在单独的标注文件中。

## 使用方式

1. 从 `papers.json` 的 `pdf_url` 下载对应固定版本 PDF；
2. 使用 PaperAudit 的 PDF 解析器生成本地 chunk 索引；
3. 以 `samples.jsonl` 的 `report_text` 作为输入运行审计；
4. 用 `gold_label`、`gold_error_type` 和 `gold_severity` 对比预测结果。

首轮基线结果见 `baseline_report.md`；批量输出位于 `results/`，包括逐条预测、JSON 指标和标签混淆矩阵。

每次运行的 `metrics.json` 还包含 `by_category` 与 `by_construction` 分层指标。分层统计用于定位哪类证据或论断构造导致漏召回，不改变总体评分，也不应被用来为单篇论文添加特判。

第二批跨领域样本位于 `cross_papers_v2.json`、`cross_samples_v2.jsonl` 和 `cross_resolved_samples_v2.jsonl`，覆盖 DQN（强化学习）、U-Net（医学图像）与 Word2Vec（词表示）各 8 条样本。离线评测命令示例：

```powershell
$env:PYTHONPATH='src'
uv run python eval/run_eval.py `
  --samples eval/cross_resolved_samples_v2.jsonl `
  --papers eval/cross_papers_v2.json `
  --output-dir eval/results_cross_retrieval_v2 `
  --dry-run --top-k 5
```

外部应用诊断集位于 `external_papers_v1.json`、`external_samples_v1.jsonl` 和 `external_resolved_samples_v1.jsonl`，覆盖 VAE、Neural ODE 与 SRCNN 各 6 条样本。该集重点观察 `external_hallucination` 的证据召回，不应据此为单篇论文增加检索特判。

外部应用诊断第二批位于 `external_papers_v2.json`、`external_samples_v2.jsonl` 和 `external_resolved_samples_v2.jsonl`，覆盖 Neural Turing Machines、XGBoost 与 DeepSpeech 各 6 条样本。统一回归输出位于 `results_regression_20260829/`。

## 最终独立留出集

`final_holdout_papers.json` 与 `final_holdout_resolved_samples.jsonl` 是规则冻结后建立的最终验收集，包含 6 篇此前未出现在任何评测 split 的论文、48 条原子论断（每篇 8 条），覆盖 Neural Processes、学习型优化器、差分隐私、NAS、DeepFM 和 Deep Image Prior。PDF 版本、页数、SHA-256 及证据 chunk 均已固定；运行 `uv run python eval/check_holdout_isolation.py` 可自动验证论文级隔离。该集只用于最终泛化报告，不用于调参或解冻规则。

v2 的 `missing_condition` 独立诊断集位于 `v2_diagnostics/`，包含 8 篇未进入任何 v1 split 或生产观测的论文、32 条边界样本。它只用于分析条件遗漏与上下文省略的边界，不参与 v1 发布门禁；隔离检查使用 `uv run python eval/check_v2_diagnostic_isolation.py`。

统一回归已将其作为 `final_holdout` 单独列出，预注册 Top-5 证据召回门槛为 85%。

无需人工参与的自动有效性验证可运行：

```powershell
uv run python eval/run_validation.py --consistency --repeats 3 --count 5
uv run python eval/run_eval.py --oracle-evidence --output-dir eval/validation/oracle
```

自动验证结论见 `validation_report.md`。自动自洽性不能替代与独立人工标注的一致性验证。

样本中的论文链接、页码和摘录用于可追溯性；批量运行时仍必须以本地解析出的真实 chunk 为证据，不得只根据 `source_quote` 直接给分。

## 实验产物与提交边界

源码、固定样本、论文清单和已跟踪的冻结结果继续进入 Git。历史冻结快照只记录
对应实验的结果，不被新的验证命令覆盖；同模型参考一致性、独立人工标签、离线
检索指标仍按各自实验口径分别报告。

| 产物 | 保存位置与提交方式 |
| --- | --- |
| 评测脚本、固定样本、协议 | `eval/` 下按文件审阅后提交 |
| 已封版的指标、报告、必要预测 | 保留现有 tracked 文件；增加快照前明确实验目录、模型、数据集及统计口径 |
| 新的试验、原始响应、checkpoint、恢复记录 | 默认写到 `tmp/experiments/<实验名>/`，不提交 |
| 论文 PDF、页面图、运行日志 | 保留本地，遵循 `.gitignore`，不加入普通源码提交 |

历史 `hy3_*_20*`、`luna_*_20*` 目录的未跟踪内容已加入忽略规则，磁盘文件仍然
保留。目录内此前已提交的紧凑报告和指标仍由 Git 管理。忽略文件不等于删除，
也不等于脱敏；分享原始实验包前需单独检查内容。新的发布快照应显式添加必要
文件并记录来源，不对整个实验目录执行强制添加。

推荐当前验证输出目录：

```shell
.venv/bin/python eval/run_regression.py --output-dir tmp/regression-local --top-k 5
.venv/bin/python eval/release_gate.py --output tmp/release-gate-local.json
```

仓库通过 `.gitattributes` 将文本统一为 LF，PDF、图片和视频按二进制处理。
迁移平台时应使用新建的虚拟环境，避免复制 `.venv`。
