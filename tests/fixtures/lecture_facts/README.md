# 讲解事实清单固定验收集

本目录是离线规则验收集，不是全文质量认证。4 组材料、32 个固定正反例覆盖：

- `transformer.json`：现有 Transformer 论文的真实解析摘录。保存原始换行、表头、行数据和摘录来源，验证模型/数据集/数值对应、原文冲突、训练设置与歧义成本。不是完整论文评测。
- `scientific.json`：明确标注的合成材料，测试科学计数法、指数、百分数比例和单位。
- `theory.json`：明确标注的合成理论材料，测试假设条件和无实验边界。
- `survey.json`：明确标注的合成综述材料，测试分类依据和未运行统一实验的边界。

`facts` 是固定核对基准，不能从待测模型的输出生成。`examples` 的 `expected_codes` 由案例规定；正常例应为空，反例应出现对应错误。不得为了让新输出通过而删除原有反例。

运行离线检查：

```sh
uv run --locked python scripts/check_lecture_facts.py --output output/lecture-facts/verification.json
uv run --locked pytest tests/test_learning_facts.py tests/test_learning_generation.py -q
```

命令失败时退出码为 1。默认无模型调用、无业务库读写。输出同时注明 `semantic_quality_certified=false`。

检查一个遵循本基准规范的外部产物：

```sh
uv run --locked python scripts/check_lecture_facts.py \
  --case tests/fixtures/lecture_facts/scientific.json \
  --artifact /absolute/path/to/artifact.json \
  --output output/lecture-facts/model-check.json
```

产物形状为：

```json
{
  "facts": ["LessonFact 对象，保留基准 fact_id 和规范标签"],
  "mentions": [
    {
      "fact_id": "cost_exact",
      "explanation": "Atlas 在 Set-A 的训练成本为3.3e18 FLOPs。",
      "excerpt": "Atlas 在 Set-A 的训练成本为3.3e18 FLOPs。",
      "cited_chunk_ids": ["cost"]
    }
  ]
}
```

`facts` 的完整对象可参照对应案例 JSON。本接口比较固定 ID/规范标签，适合受控回归，不能直接将自由生成、自由命名的清单当作相同基准评分。独立基准会拒绝遗漏事实、改写绑定、重复映射和未知 ID；生成器内部的模型自报覆盖不等于基准评分。

原始 `source_value` 必须来自摘录，规范化 `value` 只接受无歧义等价数值。例：`3.3×10^18`、`3.3e18`、`3.3×10¹⁸` 可以等价；解析后的 `3.3 · 1018` 不能推断其指数。事实仍需保留歧义与可见的原始内容，不能因归属不明而丢弃整项成本。

这些检查能验证文字落点、规范标签、数值等价、条件、引用与边界说明，不能证明自然语言中的因果关系、否定、比较方向或整个事实清单完备。生成流程因此继续保留语义审核，复核时同时传入上轮问题。下一阶段应扩充真实理论/综述全文，并对独立生成的事实绑定和遗漏率进行人工标注评估。


`provider_snapshots/` 保存 2026-11-10 的三个真实模型提纲响应（输入分别为此处的真实论文摘录、合成理论材料、合成综述材料）。使用 configured-model 共 4 次请求、18,933 token；不是三个真实论文的全文评测。最初数值校验未处理赋值式与符号界而拦截前两项，修正规则后缓存回放通过；没有人工改写模型响应，也没有额外模型调用。回归测试会重放这些提纲并校验结构与原文。


`provider_snapshots/transformer-rejected-facts.json` 保存整篇 Transformer 试验 `full-v11-point-facts` 中 5 个未改写的失败事实及其实际来源块，作为负例回归。它不属于上面的 32 个固定正反例，也不是新的独立质量基准。覆盖补写除号、不连续引文、整段短语与规范数值不等价、合并指标缺少数值等真实失败。模型调用共 2 次/53,228 token，在提纲校验阶段终止；没有正文产物、没有业务库写入。根号/乘号原样符号表示的校验误拒另已修复，但不放行这些真实缺陷。


`provider_snapshots/transformer-fact-correction.json` 保存未改写的整篇失败提纲、`resume-v13-fact-contract` 最后一份原始纠错响应字符串及对应原文块。该响应唯一剩余格式问题是一条 330 字符的真实连续引文；应用验证整段存在后无损拆分，离线重放通过。5 个失败事实修正后，由 30 个事实变为 32 个（两个混合指标各拆成两项），其余 25 个事实逐对象保持一致。回归同时检查身份、未涉及事实保留和重新校验；不是完整讲解或事实语义认证。
