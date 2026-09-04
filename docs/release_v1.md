# PaperAudit v1 发布清单

## 发布状态

**已封版（2026-08-30，Asia/Shanghai）**。v1 以冻结审核规则、独立最终留出集和可重复发布门禁为发布条件。最终留出集包含 6 篇新论文、48 条样本；真实 API 结果保存在 `eval/results_final_holdout_actual/metrics.json`。

本文件记录 2026-08-30 的历史冻结快照。机器可读门禁 `eval/release_gate_v1.json` 保存的是当时的 `119 passed`；当前工作区测试数量已增加到 164，当前复现状态以 `docs/final_submission_checklist.md` 为准。

## 已完成检查

- 冻结门禁自动化测试：119 passed；
- 最终留出集论文隔离：`isolated=true`；
- 最终留出集证据映射：48/48；
- 固定评测集离线回归：10/10 PASS；
- 最终留出集真实 API：标签 83.33%、错误类型 78.79%、风险 83.33%、ABSTAIN 0%、证据召回 87.50%；
- 入口文件编译检查通过；
- 端到端冒烟覆盖：新论文解析、真实 API 审计、本地持久化和结果读取。

本次冒烟结果已保存至 `tmp/release_smoke/smoke_result.json`：Mamba 论文 36 页、680 个 chunk，生成 2 条审计论断，持久化后读取条数一致，结果为 `passed=true`。

## v1 生产观测批次

在不修改规则的前提下，已新增 8 篇未进入评测集的真实论文（BART、T5、DINO、MAE、PPO、SAC、Deep Graph Infomax、TabNet），并完成真实 API 审计。连同此前运行记录，当前生产观测覆盖 10 篇不同论文、11 次审计、150 条自动审核论断，`ABSTAIN=0`。自动汇总见 `eval/production_observations_v1/runtime_20260830_batch2/summary.json`。

当前 `overgeneralization`、`missing_condition` 和 `external_hallucination` 虽有较多发生次数，但各自只覆盖 2 篇论文，尚未达到“至少 5 次且跨至少 3 篇论文”的 v2 诊断条件，因此不触发规则修改。

随后又完成第二批 8 篇论文（Network In Network、Seq2Seq、DeepLab、RetinaNet、DDPG、A3C、GraphSAGE、PointNet）。当前生产观测累计 18 篇不同论文、19 次审计、174 条自动审核论断，`ABSTAIN=0`。第二批结果见 `eval/production_batch_v2_result.json`，汇总见 `eval/production_observations_v1/runtime_20260830_batch3/summary.json`。

第三批补充 HuBERT（语音）和 TimesNet（时间序列）后，生产观测达到 20 篇不同论文、21 次审计、180 条自动审核论断，`ABSTAIN=0`。最新汇总见 `eval/production_observations_v1/runtime_20260830_batch4/summary.json`。当前没有错误类型同时满足至少 5 次且跨至少 3 篇论文，规则继续冻结。

第四批再补充 10 篇跨领域论文（Whisper、CLAP、Informer、PatchTST、Perceiver、Flamingo、BLIP、MoCo、SimCLR、AST），未加入固定评测集或 v1 最终留出集。生产观测现达到 30 篇不同论文、31 次审计、210 条自动审核论断，`ABSTAIN=0`。结果见 `eval/production_batch_v4_result.json`，统一汇总见 `eval/production_observations_v1/runtime_20260830_batch5/summary.json`。本批次仅用于生产稳定性观察，不作为金标准确率，也不据此修改冻结规则。`missing_condition` 累计 11 次、覆盖 4 篇论文，达到 v2 诊断触发条件；按冻结策略仅登记为待诊断项，不在 v1 中自动调参。

本轮统一验收：`eval/release_gate_v1.json` 发布门禁通过（119 passed、留出集隔离和快照均通过），Streamlit `http://127.0.0.1:8501/` 返回 HTTP 200。2026-08-30 发布前复现再次通过：依赖同步、119 项测试、留出集隔离、离线回归、编译检查和 `eval/e2e_smoke.py` 均为 `PASS`；最新冒烟结果写入 `tmp/release_smoke/smoke_result.json`。

发布后生产观察入口已建立。基于当前项目存储重新聚合得到 31 篇论文、32 次审计、251 条自动审核论断，`ABSTAIN=0`。标签汇总为 `SUPPORTED=201`、`PARTIALLY_SUPPORTED=35`、`NO_SUPPORT_FOUND=13`、`CONTRADICTED=2`；重复诊断信号为 `external_hallucination`（9 次/3 篇）和 `missing_condition`（11 次/4 篇）。该批次仅用于运行监测，不作为金标准，也不触发 v1 规则调整。结果见 `eval/production_observations_v1/runtime_20260830_release/summary.json`。

## 发布前命令

```powershell
$env:PYTHONPATH='src'
uv sync --dev
uv run python eval/release_gate.py
uv run python eval/e2e_smoke.py --pdf tmp/release_smoke/mamba.pdf
```

启动：

```powershell
uv run streamlit run app.py --server.headless true --server.port 8501
```

## 运行时配置

必须配置 `HY3_API_BASE`、`HY3_API_KEY`、`HY3_MODEL`。推荐使用 `.env`，不得提交真实 Key。发布基线使用 `gpt-5.6-luna`、`HY3_REASONING_EFFORT=no_think`、Top-K 5、评测批大小 8。

## 封版边界

v1 发布后不再根据最终留出集错误添加论文专属规则。任何审核规则、提示词或检索权重变更都必须重新跑完整门禁；若要声称新版本具有独立泛化能力，必须建立新的 v2 最终留出集。
