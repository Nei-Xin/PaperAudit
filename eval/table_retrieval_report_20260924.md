# 引用页表格召回开发验证（2026-09-24）

本轮修复引用页局部检索中，表格正文说明挤占表头和数值行候选的问题。
中文页码支持列表和有限范围；检索保留全局前五块，再用最多三个位置放入
命中表格的标题、表头和按论断检索的数据行。扫描在另一表标题、正文或页边界
停止，最多查看标题后的十二块。所有策略仍共享十块、18,000 字符预算，
保留原文、页码和 chunk ID，不拼接或截断证据。

## 结果与口径

- `evidence_gap_dev_samples_20260924.json` 中十四个自然案例，完整参考块覆盖
  从 5/14 增至 10/14。排除两个删除证据对照和四个完整证据探针。
- 新覆盖的案例为 SF01、SF02、SF03、SF05、SF06。SF04 已召回表头和数据行，
  仍缺参考集中的另一页实验设置；SQ03、SQ06 的完整表格上下文也仍有缺口。
- 九个历史非最终验收集的 plain/cited 离线对照均通过既有召回门槛：
  cited 新增七例至少一个参考块命中，没有丢失 plain 已命中的案例。
- 全量测试 313 项通过；最终留出集论文隔离检查通过。此次开发对照排除了
  `independent_final` 数据集，没有使用其结果选择实现。

上述指标只描述候选证据覆盖，不代表审计标签、引用完整性或端到端准确率。
表格识别仍使用文本结构启发式，碎片化列头、跨页表格和数字型表头需后续验证。

## 本地实验来源

- 改动前冻结协议：`tmp/experiments/evidence-gap-independent-v4-20260924/protocol.json`
- 改动后候选协议：`tmp/experiments/evidence-gap-table-structured-20260924/protocol.json`
- 历史开发回归：`tmp/experiments/cited-table-development-regression-20260924.json`

候选协议由 `eval.evidence_gap_experiment prepare` 生成；使用新建输出目录，
不覆盖冻结协议。历史对照调用 `eval.compare_cited_retrieval.compare()`，
调用前将其 `DATASETS` 过滤为 `not dataset.get('independent_final')`。

下一步使用新论文和新报告验证完整抽取、检索、初审、候选复审及引用复核链路；
同时记录复审触发率、额外请求数、token 用量及平均/P95 延迟。
