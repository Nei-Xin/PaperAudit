# code-investigation-dev-v1 · 78 observations

### Verdict matches reference (all observations in the denominator)

| | agent | fixed |
|---|---|---|
| all | 32/39 | 25/39 |

### By expected verdict

| | agent | fixed |
|---|---|---|
| CONSISTENT | 20/22 | 16/22 |
| INCONSISTENT | 10/13 | 8/13 |
| NOT_LOCATED | 2/4 | 1/4 |

### By construction

| | agent | fixed |
|---|---|---|
| edited | 9/12 | 8/12 |
| natural-consistent | 20/22 | 16/22 |
| natural-inconsistent | 1/1 | 0/1 |
| natural-not-located | 2/4 | 1/4 |

### By paper

| | agent | fixed |
|---|---|---|
| gcn | 8/10 | 8/10 |
| lora | 5/6 | 2/6 |
| mae | 10/11 | 7/11 |
| moco | 9/12 | 8/12 |

### Predictions

| mode | CONSISTENT | INCONSISTENT | NOT_LOCATED | PARTIAL | MIXED | ABSTAIN | ERROR |
|---|---|---|---|---|---|---|---|
| agent | 20 | 12 | 2 | 0 | 2 | 3 | 0 |
| fixed | 17 | 11 | 5 | 6 | 0 | 0 | 0 |

### Unsupported verdicts and cost

| mode | says consistent, reference inconsistent | says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |
|---|---|---|---|---|---|---|
| agent | 0 | 0 | 33/35 | 232 | 825379 | 1347 |
| fixed | 1 | 2 | 34/35 | 78 | 311610 | 408 |

Agent stop reasons: {'answered': 36, 'citations_rejected': 2, 'provider_error+fallback': 1}; runs that needed the citation repair: 15/39; findings removed after repair: 3

### Observations that do not match

- `gcn-glorot` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文描述：权重采用 Glorot & Bengio（2010）所述的初始化方式。代码：当前候选代码未定位到权重变量的初始化实现或初始化器设置。差异：证据不足以判断代码是否按论文所述方式初始化；这不表示仓库中不存在该实现。'
- `gcn-hiddenx` agent #0: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `gcn-nell` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文给 NELL 的设置是 dropout `0.1`、L2 正则 `1×10⁻⁵`、隐藏单元 `64`。代码中有可调的通用参数，但默认值是 `0.5`、`5e-4`、`16`，没有看到针对 NELL 的专门配置；因此配置项对应得上，默认数值不匹配论文的 NELL 组。'
- `gcn-nell` fixed #0: expected NOT_LOCATED, got PARTIAL — '论文描述：NELL 使用 dropout 0.1、L2 正则系数 1×10⁻⁵、隐藏单元数 64。\n代码实现：训练脚本提供全局默认值 dropout 0.5、weight_decay 5×10⁻⁴、hidden1 16；当前代码候选未显示按 NELL 切换为论文所列数值的配置。因此不能确认代码中存在对应的 NELL 专'
- `lora-a-init` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文所述初始化方式的具体细节在当前候选文本中未定位，无法确认矩阵 A 是否初始化为零。代码中的 loralib Linear 层则将 A 用 Kaiming uniform 初始化、将 B 初始化为零。因此，现有证据不足以判断两者是否一致；代码注释称其初始化方式与论文描述不同。'
- `lora-b-init` agent #0: expected CONSISTENT, got MIXED — '结论：不完全一致。论文称矩阵 B 零初始化，这一点 `loralib.Linear` 一致；但论文称 A 用随机高斯初始化，而该层实际用 Kaiming uniform 初始化 A，因此整体初始化方案不同。'
- `lora-b-init` fixed #0: expected CONSISTENT, got INCONSISTENT — '论文描述将更新写为 ΔW=BA，但所给论文片段没有说明 A、B 各自的初始化方式。代码中的 loralib Linear 将 A 用 kaiming_uniform_ 初始化、将 B 初始化为零；代码注释称这与论文描述不同。因此，现有证据不足以确认初始化方式一致；代码明确指出其实现与论文描述不同，但论文候选片段未给出可'
- `lora-scaling` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文片段说明低秩更新为 ΔW=BA，但未给出其缩放系数，无法据此比较论文与代码的系数是否一致。代码中 Linear 初始化时设置 scaling = lora_alpha / r；因此只能确认 loralib 使用该缩放方式，不能判断它是否与论文一致。'
- `lora-scalingx` fixed #0: expected INCONSISTENT, got PARTIAL — '论文证据仅描述 ΔW = BA，未给出其缩放系数，因此无法据此判断论文与实现的缩放是否一致。代码候选显示，Embedding 的缩放系数为 lora_alpha / sqrt(r)；但没有提供 Linear 的系数定义，故不能据此确认问题所指实现整体与论文一致或不一致。'
- `mae-betasx` agent #0: expected INCONSISTENT, got MIXED — '论文的 ImageNet 预训练设置使用 AdamW，β₁=0.9、β₂=0.95；`main_pretrain.py` 实际显式设置 β₁=0.9、β₂=0.999。因此 β₁一致，β₂不一致。'
- `mae-blockmask` fixed #0: expected NOT_LOCATED, got PARTIAL — '论文图示/消融涉及 block-wise 掩码采样：移除较大的随机块。代码候选实现的是逐样本随机掩码，通过随机噪声排序并保留部分 patch；没有找到 block-wise 采样的实现证据。因此，两者策略不同，当前候选代码只显示随机采样，不能据此断定仓库其他位置也没有实现。'
- `mae-linprobe` fixed #0: expected CONSISTENT, got PARTIAL — '论文描述：线性探测分类器前加入无仿射变换的 BatchNorm 层（affine=False），置于编码器特征与线性分类器之间。论文候选文本没有给出该设置所用优化器。\n\n代码实现：分类头被改为 BatchNorm1d（affine=False，eps=1e-6）后接原分类层；优化器使用 LARS，优化分类头参数。代码默'
- `mae-warmup` fixed #0: expected CONSISTENT, got INCONSISTENT — '不一致。论文给出的预训练 warmup 为 20 epoch；预训练代码的默认值为 40 epoch。'
- `mae-warmupx` fixed #0: expected INCONSISTENT, got CONSISTENT — '论文列出的预训练配置为 warmup 20 个 epoch；代码中预训练参数默认值也是 20。因此两者一致（代码默认值可被运行时参数覆盖）。'
- `moco-ig1b` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文报告 IG-1B 学习率每 62.5k 次迭代乘以 0.9 的指数衰减；代码实现的是余弦衰减或按 epoch 里程碑每次乘以 0.1 的阶梯衰减，因此未实现论文所述的 IG-1B 策略。'
- `moco-ig1b` fixed #0: expected NOT_LOCATED, got INCONSISTENT — '论文描述：IG-1B 训练使用初始学习率 0.12，每 62.5k 次迭代（64M 张图像）按 0.9 倍指数衰减。代码候选中，MoCo 学习率调度器实现的是余弦衰减，或按 epoch 里程碑每次乘以 0.1；没有找到论文所述按迭代次数每 62.5k 次乘以 0.9 的策略。因此，当前证据不支持代码实现了该 IG-1B'
- `moco-kx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文仅说明队列大小可独立设为超参数，未给出实验使用的具体 K；代码默认 K=4096。因此无法判断两者是否一致。'
- `moco-mx` agent #0: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `moco-t` agent #0: expected CONSISTENT, got ABSTAIN — '论文给出 InfoNCE 损失中温度参数 τ 的定义，但检索到的论文段落没有提供其数值；代码 `moco/builder.py` 将 `T` 默认设为 `0.07`。因此无法据现有证据判断数值是否一致。'
- `moco-t` fixed #0: expected CONSISTENT, got PARTIAL — '论文说明对比损失使用温度超参数 τ，但当前论文候选未给出其具体数值（p2_b19）。代码默认温度为 0.07（`--moco-t`；模型构造参数 T 也默认为 0.07）。因此，依据当前证据无法判断两者数值是否一致。'
- `moco-tx` fixed #0: expected INCONSISTENT, got PARTIAL — '论文摘录说明 τ 是温度超参数，但未给出具体数值。代码的默认温度为 0.2。因此，现有证据不足以判断二者是否一致。'
