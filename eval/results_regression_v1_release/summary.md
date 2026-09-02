# PaperAudit 统一回归结果

模式：`dry-run`；Top-K：`5`。

| 数据集 | 样本数 | Top-5 召回 | 最低门槛 | 结果 |
| --- | ---: | ---: | ---: | --- |
| dev | 40 | 100.00% | 100.00% | PASS |
| holdout | 32 | 100.00% | 100.00% | PASS |
| extended | 24 | 100.00% | 95.00% | PASS |
| broad | 24 | 87.50% | 85.00% | PASS |
| body | 24 | 91.67% | 90.00% | PASS |
| concept | 12 | 58.33% | 55.00% | PASS |
| cross_v2 | 24 | 91.67% | 90.00% | PASS |
| external_v1 | 18 | 77.78% | 75.00% | PASS |
| external_v2 | 18 | 94.44% | 90.00% | PASS |
| final_holdout | 48 | 87.50% | 85.00% | PASS |

总体结果：**PASS**。

分层指标保留在各数据集目录的 `metrics.json`，仅用于诊断，不参与规则分支。
