# code-investigation-dev-v1 · 39 observations

### Verdict matches reference (all observations in the denominator)

| | agent |
|---|---|
| all | 30/39 |

### By expected verdict

| | agent |
|---|---|
| CONSISTENT | 20/22 |
| INCONSISTENT | 10/13 |
| NOT_LOCATED | 0/4 |

### By construction

| | agent |
|---|---|
| edited | 10/12 |
| natural-consistent | 20/22 |
| natural-inconsistent | 0/1 |
| natural-not-located | 0/4 |

### By paper

| | agent |
|---|---|
| gcn | 9/10 |
| lora | 4/6 |
| mae | 9/11 |
| moco | 8/12 |

### Predictions

| mode | CONSISTENT | INCONSISTENT | NOT_LOCATED | PARTIAL | MIXED | ABSTAIN | ERROR |
|---|---|---|---|---|---|---|---|
| agent | 21 | 13 | 0 | 1 | 1 | 3 | 0 |

### Unsupported verdicts and cost

| mode | says consistent, reference inconsistent | says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |
|---|---|---|---|---|---|---|
| agent | 1 | 0 | 34/35 | 217 | 766732 | 1231 |

Agent stop reasons: {'answered': 37, 'citations_rejected': 1, 'provider_error+fallback': 1}; runs that needed the citation repair: 8/39; findings removed after repair: 1

### Observations that do not match

- `gcn-nell` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文给出的 NELL 参数组是 dropout=0.1、L2=1×10⁻⁵、隐藏单元=64；代码有对应参数项，但默认值是 0.5、5×10⁻⁴、16，而非 NELL 这组。因此可通过参数配置表达这些超参数，但检查到的代码默认配置没有设置成 NELL 的取值。'
- `lora-a-init` agent #0: expected INCONSISTENT, got CONSISTENT — '结论：不一致。论文描述 `A` 为随机高斯初始化；`loralib.Linear` 的 `lora_A` 使用 Kaiming uniform 初始化。'
- `lora-gpt3` agent #0: expected NOT_LOCATED, got PARTIAL — '论文确实报告了 GPT-3 175B 上的 LoRA 微调实验；但仓库未提供该实验的专用训练实现。仓库包含的是可集成到 PyTorch 模型中的 `loralib` 通用代码及 GPT-2 等示例，因此可作为构建模块，不等于复现 GPT-3 175B 实验的完整代码。'
- `mae-betasx` agent #0: expected INCONSISTENT, got MIXED — '论文预训练设置的 AdamW β1、β2 为 (0.9, 0.95)，而预训练代码 `main_pretrain.py` 指定为 (0.9, 0.999)。因此 β1 一致，β2 不一致。'
- `mae-blockmask` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文的消融实验确实比较了 block-wise 掩码（50% 时尚可、75% 时性能退化）；但该代码实现的是逐样本随机打乱 patch 的随机掩码，没有实现 block-wise 采样。'
- `moco-ig1b` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文为 IG-1B 指定的指数衰减学习率策略没有在该代码的学习率调度器中实现：代码提供的是余弦衰减或按里程碑阶梯衰减，而非每 62.5k 次迭代乘以 0.9。'
- `moco-k` agent #0: expected CONSISTENT, got ABSTAIN — '论文检索到的段落说明队列大小是可独立设置的超参数，但未给出实验所用的具体 K；代码默认 K 为 65536。因此无法确认二者是否一致。'
- `moco-kx` agent #0: expected INCONSISTENT, got ABSTAIN — '目前证据不足以判断是否一致：代码默认 K=4,096；本次检索到的论文段落只说明队列大小是可调超参数，没有给出实验使用的具体 K 值。'
- `moco-m` agent #0: expected CONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
