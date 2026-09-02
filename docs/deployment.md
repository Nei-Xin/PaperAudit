# PaperAudit 部署与运行说明

## 环境

- Python 3.11+
- 推荐使用项目自带 `.venv` 或 `uv`
- 可用的 Hy3 OpenAI-compatible API
- 本地可读写项目数据目录

## 配置

在项目根目录 `.env` 中设置：

```env
HY3_API_BASE=https://your-hy3-api.example/v1
HY3_API_KEY=your-local-key
HY3_MODEL=your-model-name
```

API Key 不会写入任务、审计历史或评测产物。

## 启动

```powershell
uv run streamlit run app.py
```

默认访问地址：`http://127.0.0.1:8501/`。

当前实例已在该地址运行时，不要重复启动第二个 Streamlit 进程；可先检查 8501 端口。

## 测试

```powershell
uv run python -m pytest -q
```

当前工作区基线为 155 个测试通过。

## 方向一自动有效性复现

完整固定集一致性实验会真实调用 API 3 次，共评测 40 条固定论断：

```powershell
uv run python eval/run_validation.py `
  --samples eval/resolved_samples.jsonl `
  --output-dir eval/validation_full `
  --consistency --repeats 3 --count 40
```

端到端对抗实验先生成 10 组成对样本，再分别运行 `eval/run_eval.py`，最后由 `eval/run_adversarial_validation.py --summarize` 汇总。冻结结果见 `eval/validation_adversarial/adversarial_summary.json`，完整结论见 `docs/direction_one_final_report.md`。这些实验不修改 v1 规则或最终留出集。

## v1 发布门禁

发布前执行：

```powershell
$env:PYTHONPATH='src'
uv run python eval/release_gate.py
```

门禁检查完整测试、最终留出集论文隔离、全部固定评测集离线回归、`app.py` 编译和最终留出集真实 API 快照。快照门槛为 48 条样本、Top-5 证据召回率至少 85%、标签准确率至少 80%、错误类型准确率至少 75%、风险准确率至少 80%、`ABSTAIN=0%`。门禁不调用 API，也不修改规则。

真实使用期间可自动聚合项目历史中的非敏感运行指标：

```powershell
$env:PYTHONPATH='src'
uv run python eval/aggregate_production_diagnostics.py `
  --storage-root 'D:\PaperAuditData' `
  --output-dir eval/production_observations_v1
```

聚合结果只用于发现跨论文的重复问题，不会自动修改规则。

部署冒烟测试使用不属于任何评测集的新论文，验证 PDF 解析、真实 API 审计、本地项目保存和结果读取：

```powershell
$env:PYTHONPATH='src'
uv run python eval/e2e_smoke.py --pdf tmp/release_smoke/mamba.pdf
```

## 启动与 HTTP 检查

```powershell
uv run streamlit run app.py --server.headless true --server.port 8501
```

另开终端检查 `http://127.0.0.1:8501/` 应返回 HTTP `200`。若 8501 已有本项目实例，直接复用，不重复启动。

## 评测

先校验 PDF 并生成金标证据：

```powershell
$env:PYTHONPATH='src'
uv run python eval/prepare_evidence.py `
  --samples eval/body_samples.jsonl `
  --papers eval/broad_papers.json `
  --output eval/body_resolved_samples.jsonl
```

离线检索评测：

```powershell
uv run python eval/run_eval.py `
  --samples eval/body_resolved_samples.jsonl `
  --papers eval/broad_papers.json `
  --output-dir eval/results_body_retrieval_latest `
  --dry-run --top-k 5
```

真实 API 评测：去掉 `--dry-run`，并确保 `.env` 配置可用。评测输出包含 `metrics.json` 和 `predictions.jsonl`，不要覆盖历史结果目录。

`metrics.json` 除总体指标外，还会写入 `by_category` 和 `by_construction` 两组分层统计。它们只用于定位证据类型或样本构造的薄弱环节，不参与评分阈值、裁决或线上审核逻辑；新增规则前应先确认问题在多个论文/样本中稳定复现。

统一离线回归：

```powershell
$env:PYTHONPATH='src'
uv run python eval/run_regression.py
```

该命令固定运行全部评测集，并在 `eval/results_regression_latest/summary.md` 与 `summary.json` 输出门槛判定。需要调用真实 API 时显式增加 `--actual`，并指定新的 `--output-dir` 保存历史结果。规则冻结约束见 [`eval/REGRESSION_BASELINE.md`](../eval/REGRESSION_BASELINE.md)。

本轮真实 API 验收结果见 [`eval/results_regression_actual_latest/summary.md`](../eval/results_regression_actual_latest/summary.md)，总体召回门槛通过；各数据集的完整标签、错误类型和风险指标保存在对应子目录的 `metrics.json`。

## 运行注意事项

- 审计任务只在当前 Streamlit Python 进程存活期间执行；关闭应用后不会继续。
- API 批量或单条 JSON 异常会自动降级；无法获得有效结构化判断时返回 `ABSTAIN`。
- 不要把论文 ID、样本 ID 或单篇论文术语写入检索分支。
- 新增评测论文时必须记录版本、页数、SHA-256、来源 URL 和金标证据映射。
- 任何检索规则改动都必须同时跑开发集、原留出集、正文集和完整测试。
