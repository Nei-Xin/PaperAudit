# PaperAudit v1 最终提交清单

> 用途：发布前一次性核对代码、评测产物、部署说明和运行结果。只有文件已进入准备发布的 Git commit 且复现命令重新通过后，才勾选对应提交项。当前不要求 push。

## 1. 提交范围

- [x] 应用代码：`app.py`、`src/paperaudit/`
- [ ] 测试：`tests/`
- [ ] 评测脚本与固定样本：`eval/*.py`、各 `*_samples.jsonl`、论文清单与证据映射
- [ ] 评测基线：`eval/REGRESSION_BASELINE.md`
- [ ] 方向一报告：`docs/direction_one_final_report.md`
- [ ] 最终验收报告：`docs/final_acceptance_report.md`
- [ ] 典型案例：`docs/typical_cases.md`
- [ ] 部署说明：`docs/deployment.md`
- [ ] v1 发布说明：`docs/release_v1.md`
- [ ] 本清单：`docs/final_submission_checklist.md`
- [ ] 冻结结果：`eval/release_gate_v1.json`、`eval/validation_full/`、`eval/validation_adversarial/`
- [ ] 最终留出集快照：`eval/results_final_holdout_actual/metrics.json`
- [ ] 时长 2 分钟以内的 Demo 视频或 GIF；录制脚本见 `docs/demo_script.md`

## 2. 不得提交

- [x] `.env`、真实 API Key、个人路径或运行日志中的密钥（`.env` 已被 `.gitignore` 忽略）
- [x] 临时截图、浏览器缓存和无关实验输出已标记为不纳入提交
- [x] 未经完整门禁验证的规则、提示词或检索权重改动不纳入 v1

## 3. 发布前复现命令

```powershell
$env:PYTHONPATH='src'
uv sync --dev
uv run python -m pytest -q
uv run python eval/check_holdout_isolation.py
uv run python eval/run_regression.py --output-dir eval/results_regression_v1_release --top-k 5
uv run python eval/release_gate.py --output eval/release_gate_v1.json
uv run python eval/e2e_smoke.py --pdf tmp/release_smoke/mamba.pdf
```

## 4. v1 发布门槛

- [x] 自动化测试全部通过（当前工作区 155 passed）
- [x] 最终留出集保持论文级隔离，样本数 48
- [x] 最终留出集 Top-5 证据召回率不低于 85%（87.50%）
- [x] 最终留出集标签准确率不低于 80%（83.33%）
- [x] 错误类型准确率不低于 75%（78.79%）
- [x] 风险等级准确率不低于 80%（83.33%）
- [x] `ABSTAIN` 为 0%
- [x] 离线回归与应用编译检查通过
- [x] 后端/浏览器端冒烟通过，持久化前后结果一致

## 5. 已知边界（随 v1 一并发布）

- v1 已完成自动化稳定性和受控对抗鲁棒性验收，但未完成独立人工双评审，因此不报告 Cohen’s κ 或人工 Macro-F1。
- `missing_condition` 的跨论文诊断仍为 diagnostic-only，不接入主裁决流程。
- 扫描件 OCR、复杂表格可靠解析、图片理解、跨论文事实核验等能力不在 v1 范围内。
- 模拟投稿评审 Stage 9 冻结结果对应 commit `e1c0339fd153f6b4481aebb6558808af04bf69b7`。当前代码含后续修复；真实 API 留出集未重跑前，不声称旧结果完全代表当前版本。

## 6. 封版记录

- 发布版本：`PaperAudit v1`
- 封版依据：`eval/release_gate_v1.json` 为 `passed=true`
- 封版策略：后续任何规则/提示词/检索改动必须新建 v2 留出集并重新运行完整门禁；不得针对单篇论文调参。
- 复现日期：2026-08-30（Asia/Shanghai）
- 发布前复现结论：`PASS`
- 生产观察入口：`eval/production_observations_v1/runtime_20260830_release/summary.json`
- 首轮发布后观察：31 篇论文、32 次审计、251 条论断，`ABSTAIN=0`
