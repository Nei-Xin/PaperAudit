# 方向一自动化有效性最终报告

## 结论

PaperAudit 已完成方向一所需的自动化评测闭环：可执行 Rubric、固定论文级数据划分、独立最终留出集、真实 API 一致性实验、受控端到端对抗实验、发布门禁和可复现产物均已建立。当前证据支持“核心审核流程可用且自动运行稳定”，但不支持“已经完成人工双评审一致性”这一表述。

## 核心结果

| 验证项 | 数据规模 | 结果 | 状态 |
| --- | ---: | ---: | --- |
| 六维评分判别力探针 | 好/中/差三档 | 100.0 > 85.0 > 40.0 | 通过（评分器层） |
| 完整一致性实验 | 40 条 × 3 次真实 API | 标签两两一致率 98.33%；论文分标准差 0.5468 | 通过 |
| 端到端对抗实验 | 10 组成对样本 | 攻击成功率 0%；标签变化 0/10 | 通过（受控因素） |
| 最终独立留出集 | 6 篇、48 条 | Top-5 召回 87.50%；标签 83.33%；错误类型 78.79%；风险 83.33%；ABSTAIN 0% | 通过 v1 门槛 |
| 当前自动化测试 | 全量 | 155 passed | 通过 |
| v2 `missing_condition` 协议 | 两批独立留出集 | 50.0%/25.0%、37.5%/25.0%（召回/误报） | 未通过 70%/20% |

## 自动一致性

固定测试集全部 40 条样本在完全相同的模型、提示词和运行配置下重复 3 次：

- 标签准确率：95.00%、97.50%、97.50%；
- 标签宏平均 F1：0.9504、0.9740、0.9740；
- 错误类型准确率：三次均为 95.45%；
- 风险准确率：95.00%、97.50%、97.50%；
- ABSTAIN：三次均为 0%；
- 标签两两一致率：98.33%；
- 平均论文分标准差：0.5468。

结果冻结在 `eval/validation_full/validation.json` 和 `eval/validation_full/run_*/`。该结果不用于反向修改规则。

## 端到端对抗性

从每篇固定测试论文选取 1 条支持样本和 1 条错误样本，共 10 组。每组只改变一种表面因素，PDF、查询、金标和证据保持不变，覆盖：

- 篇幅扩写；
- 术语堆砌；
- 伪造页码/表格/引用；
- 重复段落；
- Prompt 注入。

10 条对抗版本标签均未变化，没有论文分数上升，也没有风险等级降低；按预定义口径，对抗攻击成功率为 0%。结果冻结在 `eval/validation_adversarial/adversarial_summary.json`。

## 能力边界

1. 上述判别力三档是评分汇总层探针，不是多篇自然完整报告的人工质量排序。
2. 10 组对抗样本证明当前受控因素未造成抬分，不能外推为任意攻击下的安全保证。
3. 当前金标和自动结果没有形成两名独立人工评审者的 Cohen's kappa 或人工分歧记录，因此不能声称人工一致性已完成。
4. `missing_condition` 坐标表格表示改善了 DS2/GIN 的表头—数值绑定，但没有改善跨论文召回/误报指标，保持 diagnostic-only。
5. v1 规则、提示词、最终留出集和发布门禁继续冻结；不因单样本或单次 API 波动调参。
6. 模拟投稿评审的 Stage 9 结果冻结于 commit `e1c0339fd153f6b4481aebb6558808af04bf69b7`；当前 `hy3_client.py` 和 `service.py` 已包含后续修复。未重新运行真实 API 留出集前，不把旧 Stage 9 结果表述为当前代码的完全复现结果。

## 可复现入口

```powershell
uv run python eval/run_validation.py `
  --samples eval/resolved_samples.jsonl `
  --output-dir eval/validation_full `
  --consistency --repeats 3 --count 40

uv run python eval/run_adversarial_validation.py `
  --samples eval/resolved_samples.jsonl `
  --output-dir eval/validation_adversarial

uv run python eval/release_gate.py
```

正式提交时应同时附带 `docs/final_acceptance_report.md`、`docs/typical_cases.md`、`docs/deployment.md` 和本报告。若不增加独立人工评审，本版本应以“自动化有效性验收完成，人工一致性未验证”作为准确结论。
