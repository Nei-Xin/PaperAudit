# 回归基线与规则冻结

当前版本冻结以下内容作为 release candidate：

- 检索和裁决逻辑不按论文 ID、样本 ID 或单篇论文术语分支；
- 固定论文版本、页数、SHA-256 和金标证据映射；
- 统一回归由 `run_regression.py` 执行，默认 `--dry-run`，只检查本地证据召回；
- 只有在多个论文/样本中重复出现同一类失败，并且回归结果低于门槛时，才评估通用机制改动；
- 不因单个样本的 API 随机波动调整提示词、权重或错误类型边界。
- `final_holdout` 为预注册的最终独立留出集（6 篇全新论文、48 条样本，Top-5 召回门槛 85%）；只报告泛化结果，不参与任何规则调优。运行前应先通过 `check_holdout_isolation.py`。
- 下一版错误类型边界与建议勘误分别记录在 `error_taxonomy_v2.md` 和 `error_type_annotation_review_v2.jsonl`；两者不改写 v1 冻结金标。
- 已审定的正式 v2 金标位于 `error_type_v2/`，生成清单见 `error_type_v2/manifest.json`；四数据集统一回归由 `run_error_type_v2_regression.py` 执行。

运行：

```powershell
$env:PYTHONPATH='src'
uv run python eval/run_regression.py
```

最终留出集隔离检查：

```powershell
uv run python eval/check_holdout_isolation.py
```

结果写入 `eval/results_regression_latest/summary.json` 和 `summary.md`。真实 API 回归需显式传入 `--actual`，并建议使用新的输出目录保存历史结果。

生成并验证正式 v2 金标：

```powershell
$env:PYTHONPATH='src'
uv run python eval/build_error_type_v2_dataset.py
```

运行 v2 四数据集本地检索回归：

```powershell
$env:PYTHONPATH='src'
uv run python eval/run_error_type_v2_regression.py --dry-run --output-dir eval/results_error_type_v2_regression_dry
```

运行 v2 四数据集真实 API 回归：

```powershell
$env:PYTHONPATH='src'
uv run python eval/run_error_type_v2_regression.py --output-dir eval/results_error_type_v2_regression_actual_20260904
```

2026-09-04 的真实 API 结果位于 `results_error_type_v2_regression_actual_20260904/summary.json`：四组检索门槛全部通过，106 条合并标签准确率 90.57%、Macro-F1 88.04%、错误类型准确率 84.51%、风险准确率 96.23%、证据召回率 95.10%，`ABSTAIN=0`。由于 v2 含重标和论断原子化，该结果不可与 v1 直接解释为纯模型增益。
