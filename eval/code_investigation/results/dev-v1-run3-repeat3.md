# code-investigation-dev-v1 · 234 observations

### Verdict matches reference (all observations in the denominator)

| | agent | fixed |
|---|---|---|
| all | 90/117 | 75/117 |

### By expected verdict

| | agent | fixed |
|---|---|---|
| CONSISTENT | 59/66 | 48/66 |
| INCONSISTENT | 29/39 | 21/39 |
| NOT_LOCATED | 2/12 | 6/12 |

### By construction

| | agent | fixed |
|---|---|---|
| edited | 27/36 | 21/36 |
| natural-consistent | 59/66 | 48/66 |
| natural-inconsistent | 2/3 | 0/3 |
| natural-not-located | 2/12 | 6/12 |

### By paper

| | agent | fixed |
|---|---|---|
| gcn | 25/30 | 23/30 |
| lora | 13/18 | 6/18 |
| mae | 27/33 | 26/33 |
| moco | 25/36 | 20/36 |

### Predictions

| mode | CONSISTENT | INCONSISTENT | NOT_LOCATED | PARTIAL | MIXED | ABSTAIN | ERROR |
|---|---|---|---|---|---|---|---|
| agent | 60 | 37 | 3 | 0 | 5 | 12 | 0 |
| fixed | 51 | 29 | 21 | 15 | 0 | 1 | 0 |

### Unsupported verdicts and cost

| mode | says consistent, reference inconsistent | says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |
|---|---|---|---|---|---|---|
| agent | 1 | 0 | 99/105 | 704 | 2644089 | 2636 |
| fixed | 3 | 2 | 103/105 | 234 | 915951 | 823 |

Agent stop reasons: {'answered': 108, 'citations_rejected': 7, 'invalid_model_response+fallback': 2}; runs that needed the citation repair: 35/117; findings removed after repair: 9

### Across repeats

| mode | per repeat | items always right | sometimes right | never right | items with one verdict in every repeat | majority verdict right |
|---|---|---|---|---|---|---|
| agent | 30/39, 31/39, 29/39 | 24 | 13 | 2 | 24/39 | 29/39 |
| fixed | 24/39, 25/39, 26/39 | 23 | 5 | 11 | 27/39 | 24/39 |

Items where one mode is right more often: {'tie': 17, 'fixed': 8, 'agent': 14}

### Observations that do not match

- `gcn-glorot` fixed #0: expected CONSISTENT, got PARTIAL — '论文描述：权重采用 Glorot & Bengio（2010）所述的初始化方式（并提到对输入特征向量按行归一化）。\n代码实现：`Dense` 和 `GraphConvolution` 层的权重都通过 `glorot` 初始化函数创建。\n差异判断：代码中的初始化名称与论文描述一致；但候选代码没有给出 `glorot` 函'
- `gcn-glorot` fixed #2: expected CONSISTENT, got PARTIAL — '论文描述：使用 Glorot & Bengio (2010) 所述方法初始化权重。\n代码实现：Dense 层通过 `glorot` 函数为权重创建变量；给出的代码片段未展示该函数的具体计算方式。\n比较：两者在“采用 Glorot 初始化”这一点上吻合，但仅凭当前代码证据无法核实 `glorot` 的具体实现是否与论文所'
- `gcn-hidden` agent #0: expected CONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `gcn-hiddenx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文证据未给出 Cora 等引文网络数据集的隐藏层单元数；32 个单元是论文针对随机图数据集的设置，不能据此认定为引文网络设置。代码中 `hidden1` 默认值为 32，且默认数据集为 Cora。由于缺少论文对引文网络隐藏层单元数的直接说明，无法判断两者是否一致。'
- `gcn-hiddenx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文提供的引文网络实验设置未说明隐藏层单元数；其中 32 个单元明确适用于随机图数据集，不能据此认定引文网络也使用 32 个。代码则将隐藏层单元数默认设为 32。因此，无法判断两者是否一致。'
- `gcn-nell` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文给出的 NELL 参数是 dropout `0.1`、L2 正则 `1·10⁻⁵`、隐藏单元 `64`。代码虽有对应参数入口，但默认值为 `0.5`、`5e-4`、`16`，没有看到按 NELL 自动切换的一组配置；因此要复现论文 NELL 设置需显式传入对应参数。'
- `gcn-nell` agent #1: expected NOT_LOCATED, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `gcn-nell` agent #2: expected NOT_LOCATED, got INCONSISTENT — '- **Dropout：**论文列出的 NELL 值为 `0.1`；代码中有通用 `dropout` 参数，但默认值为 `0.5`，当前证据未显示 NELL 专属配置。\n- **L2 正则：**论文值为 `1·10⁻⁵`；代码的通用默认 `weight_decay` 为 `5e-4`，并用于首层变量的 L2 loss，'
- `gcn-nell` fixed #0: expected NOT_LOCATED, got INCONSISTENT — '论文描述：NELL 使用 dropout 0.1、L2 正则系数 1×10⁻⁵、隐藏单元数 64。代码提供了对应参数项，但展示的默认配置是 dropout 0.5、L2 权重 5×10⁻⁴、隐藏单元数 16；未见 NELL 专用取值或按数据集切换这些参数的配置。因此参数可配置，但当前证据显示的默认值与论文报告的 NEL'
- `gcn-nell` fixed #1: expected NOT_LOCATED, got INCONSISTENT — '论文描述 NELL 使用 dropout 0.1、L2 正则系数 1×10⁻⁵、隐藏单元数 64。代码提供相应参数配置项，但当前默认值是 dropout 0.5、L2 权重 5×10⁻⁴、隐藏单元数 16；数据集默认设为 Cora。代码证据未显示针对 NELL 覆盖这些参数的配置，因此论文参数与代码所示默认配置不同，不'
- `gcn-nell` fixed #2: expected NOT_LOCATED, got INCONSISTENT — '论文描述：NELL 使用 dropout 0.1、L2 正则 1×10⁻⁵、隐藏单元数 64。代码中有对应参数项，但给出的默认配置是 dropout 0.5、L2 权重 5×10⁻⁴、隐藏单元数 16；dataset 默认值为 cora，且当前证据未显示针对 NELL 切换这些参数的配置。因此有配置入口，但所示默认值与'
- `gcn-wd` agent #2: expected CONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `lora-a-init` agent #0: expected INCONSISTENT, got MIXED — '论文与 `loralib.Linear` 的 A 初始化不一致：论文称 A 使用随机高斯初始化；代码使用 Kaiming uniform 初始化。两者都将 B 初始化为零，因此初始更新 BA 为零这一点一致。'
- `lora-a-init` fixed #0: expected INCONSISTENT, got PARTIAL — '论文所给片段只描述低秩分解 ΔW=BA，未说明矩阵 A 的初始化方式；因此无法仅凭这些证据判断论文中的 A 初始化是否与代码一致。代码中，Linear 层将 A 用 Kaiming uniform 初始化、将 B 初始化为零；代码注释称这与论文描述不同。'
- `lora-a-init` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本没有说明矩阵 A 的初始化方式，因此无法据此判断是否一致。代码中，loralib 的 Linear 层对 A 使用 kaiming_uniform_ 初始化，对 B 置零；故两者是否一致尚不能确认。'
- `lora-a-init` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文侧：当前提供的论文片段没有说明矩阵 A 的初始化方式，因此无法据此判断论文与代码是否一致。代码侧：`loralib` 的 `Linear` 层将 A（`lora_A`）用 Kaiming uniform 初始化、将 B（`lora_B`）置零；代码注释称此方式不同于论文描述。由于论文描述未出现在所给片段中，不能独立'
- `lora-b-init` agent #0: expected CONSISTENT, got MIXED — '不一致。论文规定 `A` 随机高斯初始化、`B` 初始化为零；`loralib.Linear` 则将 `A` 用 Kaiming uniform 初始化、`B` 置零。因此 `B` 的零初始化一致，但完整的初始化方式（尤其 `A`）不一致。'
- `lora-b-init` agent #1: expected CONSISTENT, got MIXED — '论文称 LoRA 用随机高斯初始化 A、将 B 初始化为零；但 `loralib.Linear` 将 A 用 Kaiming uniform 初始化、B 置零。因此 B 的初始化一致，A 的初始化不同。'
- `lora-b-init` fixed #0: expected CONSISTENT, got NOT_LOCATED — '**论文描述：**对低秩更新写作 ΔW = BA，其中 B ∈ R^{d×r}、A ∈ R^{r×k}；所给论文片段未说明 B 的初始化方式。**代码实现：**`loralib.Linear` 将 B 初始化为零，A 使用 Kaiming 均匀初始化。**比较：**无法据此判断 B 的初始化是否与论文一致；代码注释称该'
- `lora-b-init` fixed #1: expected CONSISTENT, got INCONSISTENT — '论文描述：现有论文候选没有说明矩阵 B 的初始化方式，因此无法据此确认论文中的初始化细节。代码实现：loralib 的 Linear 层将 B 初始化为零，A 使用 Kaiming 均匀初始化。差异：代码注释明确指出这与论文所述不同；但当前候选未包含论文相关初始化原文，无法独立核实具体差异。'
- `lora-b-init` fixed #2: expected CONSISTENT, got NOT_LOCATED — '**论文：**给出的论文候选只说明低秩更新写作 ΔW=BA，并未说明矩阵 B 的初始化方式。**代码：**`loralib.Linear` 将 B 初始化为零、A 用 Kaiming uniform 初始化。**比较：**现有论文证据不足以判断 B 的初始化是否与论文描述一致；代码注释称这种初始化不同于论文所述，但候选'
- `lora-gpt3` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文报告了 GPT-3 175B 上的 LoRA 实验（包括 WikiSQL、MNLI-matched 和 SAMSum），但代码仓库中没有对应的 GPT-3 175B 实验训练实现：仓库提供的 NLG 训练脚本是 GPT-2 脚本，模型选项也限定为 GPT-2 规格。因此，代码有 LoRA 组件和 GPT-2 示例，'
- `lora-gpt3` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文在 GPT-3 175B 上报告了 LoRA 微调结果；但仓库中所见可复现实验代码是针对 GPT-2，未找到 GPT-3 175B 实验实现。因此它不是论文 GPT-3 175B 实验的直接实现。'
- `lora-scaling` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文候选文本说明 ΔW=BA，但未提供其缩放系数，无法据此判断是否一致。代码中 `loralib.Linear` 将缩放设为 lora_alpha/r；因此目前只能确认代码的取值，论文侧证据不足。'
- `lora-scaling` fixed #1: expected CONSISTENT, got ABSTAIN — '论文片段描述 ΔW=BA，但未给出低秩更新的缩放系数；代码片段显示前向计算会将低秩分支乘以 self.scaling，但未展示该值如何定义。因此，依据当前证据无法判断两者的缩放系数是否一致。'
- `lora-scaling` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文候选文本说明 ΔW=BA，但未提供 ΔWx 的缩放系数公式；代码候选文本显示前向计算将低秩项乘以 `self.scaling`，但未说明该值如何定义。因此，依据当前证据无法判断两者是否一致。'
- `lora-scalingx` fixed #0: expected INCONSISTENT, got PARTIAL — '论文给出的 ΔW 定义为 BA，但所提供的论文片段没有说明其缩放系数，因此无法据此确认论文中的缩放公式。代码中 Linear 层在 r>0 时设 scaling = lora_alpha / √r。两者是否一致，证据不足。'
- `lora-scalingx` fixed #1: expected INCONSISTENT, got PARTIAL — '论文给出的低秩分解是 ΔW=BA，但当前提供的论文片段没有说明 ΔW 的缩放系数。代码中，Linear、Embedding、MergedLinear 和 ConvLoRA 在 r>0 时均设置 scaling=lora_alpha/√r。因此，现有证据不足以判断缩放系数是否与论文一致；不能据此认定二者相同或不同。'
- `lora-scalingx` fixed #2: expected INCONSISTENT, got PARTIAL — '论文描述低秩更新为 ΔW = BA，但当前提供的论文片段未给出 ΔW 的缩放系数，因此无法判断论文中的系数是否与实现一致。代码中，Linear 层在 r > 0 时设置 scaling = lora_alpha / √r；默认 lora_alpha = 1。'
- `mae-betas` agent #1: expected CONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `mae-betasx` agent #1: expected INCONSISTENT, got MIXED — '论文列出的 MAE 预训练 AdamW 动量参数为 β1=0.9、β2=0.95；预训练代码 `main_pretrain.py` 明确设置 `betas=(0.9, 0.999)`。β1 一致，β2 不一致。'
- `mae-betasx` agent #2: expected INCONSISTENT, got MIXED — '论文预训练设置为 AdamW 的 β1=0.9、β2=0.95；预训练代码固定使用 β1=0.9、β2=0.999。因此 β1 一致，β2 不一致。'
- `mae-blockmask` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文在消融实验中比较了 block-wise 掩码，并指出其移除大块随机区域，在 75% 掩码率下表现退化。代码实现的是逐样本随机打乱并按比例保留 patch 的随机掩码；没有实现论文所述的 block-wise 策略。因此，对“block-wise 策略是否实现”的回答是否定的。'
- `mae-blockmask` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文消融实验比较了 block-wise 掩码（移除较大的随机块）；代码所读到的掩码函数按样本对 patch 随机排序并采样，故此实现不是 block-wise，而是随机 patch 掩码。'
- `mae-linprobe` fixed #0: expected CONSISTENT, got PARTIAL — '论文描述：线性探测沿用文献中的分类器训练方案，并在编码器特征与线性分类器之间加入不带仿射变换的 BatchNorm（affine=False）。所给论文摘录未说明优化器类型或参数。\n代码实现：线性探测代码在分类头前加入 BatchNorm1d，设置 affine=False、eps=1e-6；优化器为 LARS，学习率'
- `mae-linprobe` fixed #1: expected CONSISTENT, got PARTIAL — '论文描述：线性探测分类器前添加无仿射变换的 BatchNorm（affine=False）；并指出线性探测训练设置见表10，但当前论文候选文本未提供优化器名称。\n代码实现：线性探测代码在分类头前加入 BatchNorm1d，设 affine=False、eps=1e-6；优化器使用 LARS。仓库说明的运行命令给出 b'
- `mae-warmup` fixed #0: expected CONSISTENT, got INCONSISTENT — '不一致：论文的预训练配置表列出 warmup 为 20 epoch；代码预训练参数的默认值是 40 epoch。另，仓库的预训练示例命令也显式设置为 40 epoch。'
- `mae-warmup` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文给出的默认预训练长度是 800 epoch，但没有提供 warmup epoch 数，因此无法确认论文 warmup 值与代码是否一致。代码预训练参数的默认 warmup 是 40 epoch；预训练说明文档也使用 40 epoch。'
- `mae-warmupx` fixed #0: expected INCONSISTENT, got CONSISTENT — '论文报告的预训练设置是 warmup 20 epoch；预训练代码的默认值也是 20。因此两者一致。'
- `mae-warmupx` fixed #1: expected INCONSISTENT, got CONSISTENT — '论文描述的预训练 warmup 为 20 个 epoch；预训练代码默认值也是 20，因此一致。'
- `mae-warmupx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文给出的预训练长度是 800 epoch，但提供的论文片段未说明 warmup epoch 数。代码的预训练默认 warmup 为 20 epoch，且预训练示例命令也设置为 20。因此无法判断是否与论文一致；现有证据只支持代码默认值为 20。'
- `mae-wdx` agent #2: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `moco-ig1b` agent #0: expected NOT_LOCATED, got INCONSISTENT — '结论：**未按论文 IG-1B 实验的指数衰减策略实现**。论文规定每 62.5k 次迭代将学习率乘以 0.9；`main_moco.py` 的调度器则按 epoch 使用余弦衰减或按里程碑每次乘以 0.1，没有实现所述的迭代级指数衰减。'
- `moco-ig1b` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文称 IG-1B 训练将学习率 0.12 每 62.5k 次迭代指数衰减为原来的 0.9 倍；检查的 `main_moco.py` 实现没有这一策略：默认按 epoch 阶梯衰减，另有可选余弦衰减。因此代码未实现论文所述的 IG-1B 指数衰减方式。'
- `moco-ig1b` agent #2: expected NOT_LOCATED, got ABSTAIN — '代码已核实：`main_moco.py` 的调度器使用余弦或按 epoch 里程碑乘以 0.1 的阶梯衰减。但目前可用的论文引文无法通过引用核验，因此不能可靠地完成与论文 IG-1B 策略的 finding 对照。'
- `moco-ig1b` fixed #0: expected NOT_LOCATED, got INCONSISTENT — '论文描述：IG-1B 训练采用初始学习率 0.12，每 62.5k 次迭代（64M 张图像）将学习率乘以 0.9，训练共 1.25M 次迭代（约 1.4 个 epoch）。\n代码实现：当前候选中的 MoCo 训练代码提供余弦衰减选项；未启用时则按 epoch 里程碑将学习率乘以 0.1。候选代码没有显示论文所述按迭代次'
- `moco-ig1b` fixed #1: expected NOT_LOCATED, got INCONSISTENT — '论文描述：IG-1B 训练时学习率每 62.5k 次迭代（即 64M 张图像）乘以 0.9，训练共 1.25M 次迭代。代码实现：学习率调整按 epoch 进行；默认在指定里程碑将学习率乘以 0.1，也可选择余弦衰减。给出的代码候选未显示论文所述按迭代每 62.5k 次乘以 0.9 的策略，因此两者不一致。'
- `moco-ig1b` fixed #2: expected NOT_LOCATED, got INCONSISTENT — '论文描述：IG-1B 训练使用初始学习率 0.12，每 62.5k 次迭代（64M 张图像）乘以 0.9 指数衰减。代码候选展示的 `main_moco.py` 学习率调整采用按 epoch 的余弦或里程碑阶梯衰减，没有展示上述按迭代次数衰减的策略；因此与论文所述 IG-1B 配置不一致。'
- `moco-k` agent #0: expected CONSISTENT, got ABSTAIN — '代码默认队列大小为 `65536`；但本次检索到的论文内容只说明队列大小可作为超参数灵活设置，未找到论文实验所用的具体 K，因此无法判断两者是否一致。'
- `moco-k` agent #2: expected CONSISTENT, got NOT_LOCATED — '代码默认队列大小为 `65536`。论文目前可核验的内容只说字典大小可独立设置为超参数，未说明实验采用的 K 数值，因此无法判断两者是否一致。'
- `moco-k` fixed #0: expected CONSISTENT, got PARTIAL — '论文提供的候选文本只说明队列大小可作为超参数灵活设定，未给出实验使用的 K 数值；代码的 MoCo 默认 K 为 65536。由于缺少论文实验数值，无法判断二者是否一致。'
- `moco-k` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文片段只说明字典大小可作为超参数灵活设置，未给出实验所用的 K 值；代码默认 K=65536。因此，依据现有证据无法判断实验值是否与代码默认值一致。'
- `moco-k` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文候选文本说明队列大小可作为超参数独立设定，但未给出实验所用的 K 数值。代码将 K 的默认值设为 65536。因此无法判断实验值与代码默认值是否一致；当前证据仅能确认代码默认值。'
- `moco-kx` agent #1: expected INCONSISTENT, got CONSISTENT — '**一致。** 论文实验说明采用 `K = 4096`，代码中 `--moco-k` 的默认值也是 `4096`。'
- `moco-kx` agent #2: expected INCONSISTENT, got ABSTAIN — '代码默认队列大小为 4096；当前已查到的论文证据仅说明字典大小是可调超参数，未核实论文实验所用 K 的具体值。因此不能判断二者是否一致。'
- `moco-kx` fixed #0: expected INCONSISTENT, got PARTIAL — '论文说明队列大小可独立设为超参数，但所给论文文本未给出实验使用的具体 K；代码默认 K=4096。因此无法判断论文实验的 K 是否与代码默认值一致。'
- `moco-kx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本只说明字典大小可作为超参数灵活设置，未给出实验使用的 K 数值，因此无法据此判断是否与代码默认值一致。代码中 MoCo 构造函数和命令行参数的默认 K 均为 4096；若运行时未覆盖该值，默认值就是 4096。'
- `moco-kx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文说明字典大小可作为超参数独立设置，但所给文本未给出实验使用的 K 数值；代码默认 K=4096。因此无法判断论文实验值是否与代码默认值一致。'
- `moco-mx` agent #0: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `moco-mx` agent #1: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `moco-schedulex` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本未说明 ImageNet-1M 预训练时在哪些 epoch 降低学习率，因此无法判断是否与代码默认调度一致。代码默认在 epoch 60 和 80 起将学习率各乘以 0.1；启用余弦调度时则按余弦公式变化。'
- `moco-t` fixed #0: expected CONSISTENT, got PARTIAL — '论文将 τ 定义为温度超参数，但所给论文文本未提供其数值；代码默认温度为 0.07。因此无法判断两者数值是否一致。'
- `moco-t` fixed #1: expected CONSISTENT, got PARTIAL — '论文说明 τ 是温度超参数，但所给论文片段未给出其具体数值。代码默认温度为 0.07。因此无法判断论文数值与代码默认值是否一致；当前证据不足以认定一致或不同。'
- `moco-t` fixed #2: expected CONSISTENT, got PARTIAL — '论文所给片段只说明 τ 是温度超参数，没有给出具体数值；代码默认温度为 0.07。因此无法根据现有证据判断两者数值是否一致。'
- `moco-tx` agent #0: expected INCONSISTENT, got ABSTAIN — '代码默认温度为 `0.2`；论文给出损失定义并说明 τ 是温度超参数，但目前检索到的论文证据没有明确其取值，因此无法判断两者是否一致。'
- `moco-tx` agent #2: expected INCONSISTENT, got ABSTAIN — '论文只将温度 τ 定义为超参数，没有在所引方法段落中给出具体数值；代码默认 `--moco-t=0.2`，并用 `self.T` 缩放 logits。因此无法据此判断论文数值与代码默认值是否一致。'
- `moco-tx` fixed #0: expected INCONSISTENT, got CONSISTENT — '论文说明对比损失含温度超参数 τ，但提供的论文片段未给出其数值。代码默认温度为 0.2，并将 logits 除以该温度。因此现有证据不足以判断默认值是否与论文一致。'
- `moco-tx` fixed #1: expected INCONSISTENT, got PARTIAL — '论文将 τ 描述为温度超参数，但所给论文片段未给出其数值。代码默认温度为 0.2（命令行参数 `--moco-t`，模型参数 `T` 也默认 0.2）。因此现有证据无法判断两者数值是否一致。'
- `moco-tx` fixed #2: expected INCONSISTENT, got PARTIAL — '论文候选文本只说明 τ 是温度超参数，未提供其数值，因此无法确认论文中的 τ 是否与代码默认值一致。代码的默认温度为 0.2；模型构造时也将该值设为温度参数。'
