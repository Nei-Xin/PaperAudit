# code-investigation-dev-v1 · 117 observations

### Verdict matches reference (all observations in the denominator)

| | agent |
|---|---|
| all | 99/117 |

### By expected verdict

| | agent |
|---|---|
| CONSISTENT | 65/66 |
| INCONSISTENT | 34/39 |
| NOT_LOCATED | 0/12 |

### By construction

| | agent |
|---|---|
| edited | 31/36 |
| natural-consistent | 65/66 |
| natural-inconsistent | 3/3 |
| natural-not-located | 0/12 |

### By paper

| | agent |
|---|---|
| gcn | 27/30 |
| lora | 13/18 |
| mae | 26/33 |
| moco | 33/36 |

### Predictions

| mode | CONSISTENT | INCONSISTENT | NOT_LOCATED | PARTIAL | MIXED | ABSTAIN | ERROR |
|---|---|---|---|---|---|---|---|
| agent | 67 | 45 | 0 | 0 | 3 | 2 | 0 |

### Unsupported verdicts and cost

| mode | says consistent, reference inconsistent | says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |
|---|---|---|---|---|---|---|
| agent | 2 | 0 | 103/105 | 695 | 2425604 | 2362 |

Agent stop reasons: {'answered': 113, 'provider_error+fallback': 1, 'invalid_model_response+fallback': 1, 'citations_rejected': 2}; runs that needed the citation repair: 9/117; findings removed after repair: 2

### Across repeats

| mode | per repeat | items always right | sometimes right | never right | items with one verdict in every repeat | majority verdict right |
|---|---|---|---|---|---|---|
| agent | 34/39, 33/39, 32/39 | 31 | 4 | 4 | 34/39 | 33/39 |

### Observations that do not match

- `gcn-nell` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文给出 NELL 的超参数为 dropout `0.1`、L2 正则 `1·10⁻⁵`、隐藏单元数 `64`。代码中有相应参数入口，但默认值仍为通用配置 `0.5`、`5e-4`、`16`，且未见 NELL 专用配置；因此只有参数项对应，数值并未对应。'
- `gcn-nell` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文给出的 NELL 超参数是 dropout=0.1、L2 正则=1·10⁻⁵、隐藏单元数=64。代码有对应的可调参数，但默认值分别为 0.5、5e-4、16；未见 NELL 专属配置，因此默认运行值与论文 NELL 设置不一致。'
- `gcn-nell` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文给出的 NELL 组合（dropout=0.1、L2=1×10⁻⁵、隐藏单元=64）在代码中没有作为 NELL 专用配置出现。`train.py` 的通用默认值是 dropout=0.5、`weight_decay`=5e-4、`hidden1`=16；数据集参数默认是 `cora`，且没看到按数据集自动切换这些超'
- `lora-b-init` agent #1: expected CONSISTENT, got MIXED — '不一致：论文将 `A` 随机高斯初始化、`B` 初始化为零；`loralib.Linear` 则将 `A` 用 Kaiming uniform 初始化、`B` 置零。因此 `B` 的零初始化一致，但整体的矩阵初始化方式不同。'
- `lora-gpt3` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文确实报告了 GPT-3 175B 上的 LoRA 微调实验（如 WikiSQL、MultiNLI 和 SAMSum），但该仓库没有对应的 GPT-3 175B 实验实现；仓库提供的是通用 LoRA 库及 GPT-2、RoBERTa/DeBERTa 示例。因此只能说其 LoRA 方法可供集成，不能认为代码复现了 GP'
- `lora-gpt3` agent #1: expected NOT_LOCATED, got INCONSISTENT — '结论：**没有看到 GPT-3 175B 实验的对应实现；仓库可核实的示例是 GPT-2。** 论文报告了 GPT-3 175B 上的实验，但此代码库 README 明确将示例说明为 GPT-2 实现及 GPT-2 实验复现。'
- `lora-gpt3` agent #2: expected NOT_LOCATED, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `lora-scalingx` agent #2: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `mae-betasx` agent #1: expected INCONSISTENT, got MIXED — '论文的预训练设置与代码不完全一致：β1 都是 0.9，但 β2 分别为 0.95（论文）和 0.999（代码）。'
- `mae-betasx` agent #2: expected INCONSISTENT, got MIXED — '论文预训练设置的 AdamW β1、β2 为 0.9、0.95；预训练代码显式设置为 0.9、0.999。因此 β1 一致，β2 不一致。'
- `mae-blockmask` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文消融实验比较了 block-wise 掩码（移除大型随机块）；代码中的掩码函数实现的是逐样本随机打乱 patch 并按比例保留，没有看到 block-wise 采样实现。因此，就该策略而言，论文与代码不一致。'
- `mae-blockmask` agent #1: expected NOT_LOCATED, got INCONSISTENT — '结论：论文消融中提到的 block-wise 掩码策略没有在此代码实现中体现；代码实现的是逐样本随机打乱 patch 的随机掩码。'
- `mae-blockmask` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文消融中确实比较了 block-wise 掩码，但代码实现的是逐样本随机打乱 patch 的随机采样；因此没有实现论文所述的 block-wise 策略。'
- `mae-warmupx` agent #0: expected INCONSISTENT, got CONSISTENT — '结论：一致。论文主 MAE 预训练设置的 warmup 为 20 个 epoch，预训练代码 `main_pretrain.py` 的默认值也是 20。'
- `mae-warmupx` agent #2: expected INCONSISTENT, got CONSISTENT — '**一致。** 论文预训练配置的 warmup 为 20 epochs，预训练脚本 `main_pretrain.py` 的默认值也是 20。'
- `moco-ig1b` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文为 IG-1B 规定了每 62.5k 次迭代将学习率乘以 0.9；该代码库的训练脚本没有实现这项按迭代次数进行的指数衰减策略。`main_moco.py` 使用余弦衰减，或按 epoch 里程碑将学习率乘以 0.1。'
- `moco-ig1b` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文对 IG-1B 的学习率明确规定为每 62.5k 次迭代乘以 0.9；检查的 `main_moco.py` 学习率调度不是该策略，因此代码未按此方式实现。'
- `moco-ig1b` agent #2: expected NOT_LOCATED, got INCONSISTENT — '结论：未实现论文 IG-1B 所述的指数衰减策略。论文规定每 62.5k 次迭代将学习率乘以 0.9；`main_moco.py` 的学习率更新仅提供按 epoch 的阶梯衰减，或可选的余弦调度，没有按迭代每 62.5k 次乘 0.9 的逻辑。'
