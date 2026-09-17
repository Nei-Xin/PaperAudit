# PaperAudit：纯 BM25 与当前检索流程对照

运行日期：2026-09-17。离线运行，无模型 API 调用；未修改生产检索、规则权重、查询或参考证据。

## 结果

| 检索方案 | Top-5 命中数 | Top-5 证据命中率 |
| --- | ---: | ---: |
| 纯 FTS5/BM25 | 23/48 | 47.92% |
| 当前流程：候选补充 + 规则重排 | 42/48 | 87.50% |

绝对提高 **39.58 个百分点**。逐样本对照：21 条由未命中变为命中，2 条由命中变为未命中，21 条均命中，4 条均未命中。退化样本为 `dip_final_006`、`dip_final_007`，本轮保留原结果，不进行针对性调参。

| 论文 | 纯 BM25 | 当前流程 |
| --- | ---: | ---: |
| Neural Processes | 2/8 | 7/8 |
| Learning to learn by gradient descent by gradient descent | 5/8 | 8/8 |
| Deep Learning with Differential Privacy | 5/8 | 8/8 |
| Neural Architecture Search with Reinforcement Learning | 5/8 | 8/8 |
| DeepFM | 3/8 | 7/8 |
| Deep Image Prior | 3/8 | 4/8 |

## 对照设置与统计口径

- 重用已有最终留出集：6 篇论文、48 条固定原子论断。论文 ID 与原有八组 split 的隔离检查通过；它是历史留出集的回放，不是本轮新收集的盲测数据。
- 两组使用同一 PDF、解析切块、FTS5 索引及文本预处理、`build_claim_query` 与 `_query_terms`，Top-K 均为 5。PDF SHA-256 均与清单一致，所有参考 chunk ID 均存在。
- 基线直接按生产索引上的 SQLite `bm25(chunks)` 排序取前五项。当前组直接调用未经修改的 `EvidenceRetriever.search`。
- 当前组含作者块/摘要等候选补充和规则加权排序。因此比较的是完整检索增强流程与纯 BM25，不能把全部收益归因于重排这一单独模块。
- 命中定义沿用既有评测：前五个候选至少包含一个参考证据 chunk 即为命中。48 条均有参考证据，分母为 48。这是 hit rate@5，不是全部相关证据块的 recall@5。
- 查询使用已有样本的固定英文 query 及字段，不测自动查询生成、论断抽取、标签判断或完整报告端到端效果。参考证据只在检索完成后用于计分。
- 本轮是固定快照的事后对照，未据此调整系统。6 篇论文、48 条论断的结果不代表跨领域普遍收益，不报告统计显著性。
- 历史论断标签准确率 83.33% 未重跑，不与本轮检索增益合并为模型判断提升。

## 验证与复现

原有 `run_eval.py --dry-run` 独立执行后，48 条样本的当前组命中标志与本次逐条完全一致，均为 42/48。离线 dry-run 的标签字段是占位结果，不用于评价模型准确率。

在 PaperAudit 根目录执行（输出目录须为新目录）：

```powershell
.\.venv\Scripts\python.exe eval\compare_retrieval_baseline.py --output-dir eval\results_bm25_comparison_replay
```

原有脚本核对命令：

```powershell
.\.venv\Scripts\python.exe eval\run_eval.py --samples eval\final_holdout_resolved_samples.jsonl --papers eval\final_holdout_papers.json --top-k 5 --dry-run --output-dir eval\results_bm25_comparison_replay\production_check
```

`summary.json` 保存源代码、样本与 PDF 哈希、Git HEAD、运行环境、总体与分论文结果；`predictions.jsonl` 保存每条查询、两组候选 ID、参考 ID 和命中情况。生产代码没有修改，脚本哈希记录本轮新增评测程序。
