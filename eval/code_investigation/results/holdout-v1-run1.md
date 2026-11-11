# code-investigation-holdout-v1 · 306 observations

### Verdict matches reference (all observations in the denominator)

| | agent | fixed |
|---|---|---|
| all | 139/153 | 88/153 |

### By expected verdict

| | agent | fixed |
|---|---|---|
| CONSISTENT | 80/84 | 41/84 |
| INCONSISTENT | 53/57 | 37/57 |
| NOT_LOCATED | 6/12 | 10/12 |

### By construction

| | agent | fixed |
|---|---|---|
| edited | 50/54 | 34/54 |
| natural-consistent | 80/84 | 41/84 |
| natural-inconsistent | 3/3 | 3/3 |
| natural-not-located | 6/12 | 10/12 |

### By paper

| | agent | fixed |
|---|---|---|
| ddpm | 36/36 | 10/36 |
| dino | 37/42 | 21/42 |
| gat | 33/39 | 27/39 |
| simsiam | 33/36 | 30/36 |

### Predictions

| mode | CONSISTENT | INCONSISTENT | NOT_LOCATED | PARTIAL | MIXED | ABSTAIN | ERROR |
|---|---|---|---|---|---|---|---|
| agent | 80 | 58 | 6 | 0 | 5 | 4 | 0 |
| fixed | 41 | 40 | 53 | 8 | 0 | 11 | 0 |

### Unsupported verdicts and cost

| mode | says consistent, reference inconsistent | says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |
|---|---|---|---|---|---|---|
| agent | 0 | 0 | 139/141 | 946 | 3475114 | 2987 |
| fixed | 0 | 3 | 109/141 | 307 | 1268738 | 1070 |

Agent stop reasons: {'answered': 148, 'provider_error+fallback': 1, 'citations_rejected': 2, 'invalid_model_response+fallback': 2}; runs that needed the citation repair: 11/153; findings removed after repair: 2

### Across repeats

| mode | per repeat | items always right | sometimes right | never right | items with one verdict in every repeat | majority verdict right |
|---|---|---|---|---|---|---|
| agent | 46/51, 47/51, 46/51 | 41 | 9 | 1 | 41/51 | 48/51 |
| fixed | 29/51, 27/51, 32/51 | 24 | 10 | 17 | 36/51 | 30/51 |

Items where one mode is right more often: {'tie': 21, 'agent': 25, 'fixed': 5}

### Observations that do not match

- `ddpm-batch` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文说明 CIFAR10 的 batch size 为 128。当前代码候选没有定位到 CIFAR10 训练脚本的默认值，因此无法判断两者是否一致。'
- `ddpm-batch` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 batch size 设为 128。当前代码候选中没有 CIFAR10 训练脚本的默认 batch size，无法判断两者是否一致。'
- `ddpm-batch` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文说明 CIFAR10 的 batch size 为 128（p15_b1）。当前代码候选未提供 CIFAR10 训练脚本的默认 batch size，因此无法判断两者是否一致。'
- `ddpm-dropout` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 dropout 率设为 0.1，该值由 {0.1, 0.2, 0.3, 0.4} 中搜索得到。代码候选显示训练函数将实例参数 self.dropout 传入去噪网络，但未提供 CIFAR10 训练脚本中该参数的默认值。因此，现有证据无法判断两者是否一致。'
- `ddpm-dropout` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 dropout 率设为 0.1。代码证据仅显示 CIFAR10 脚本接收并传递 dropout 参数，没有给出训练脚本的默认值，因此无法判断两者是否一致。'
- `ddpm-dropout` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 dropout 率设为 0.1。代码证据只显示 CIFAR10 脚本将传入的 dropout 参数交给模型，没有提供训练脚本默认值，因此无法判断是否一致。'
- `ddpm-dropoutx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文称 CIFAR10 的 dropout 率设为 0.1（在 0.1、0.2、0.3、0.4 中 sweep 选择）。当前代码候选只显示 CIFAR10 模型接收并传递 `dropout` 参数，没有给出训练脚本默认值，因此无法判断是否一致。'
- `ddpm-dropoutx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 dropout 率设为 0.1（从 0.1、0.2、0.3、0.4 中 sweep 选择）。代码证据：CIFAR 脚本的模型初始化接收 dropout 参数，但当前候选未显示 CIFAR10 训练脚本默认值；U-Net 函数的 dropout 默认值为 0.0，不能据此认定它就是训练脚本默'
- `ddpm-dropoutx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的 dropout 率设为 0.1。代码证据显示 CIFAR10 模型接收 `dropout` 参数并将其传给网络，但候选代码未显示训练脚本的默认值。因此无法判断两者是否一致。'
- `ddpm-ema` fixed #0: expected CONSISTENT, got INCONSISTENT — '论文描述：模型参数的 EMA 衰减系数为 0.9999。代码默认值：所示 EMA 创建函数接收 `ema_decay` 参数；评估相关代码调用时传入 1e-10（步数小于 1 时还使用 1e-10）。因此，论文所述系数与这些代码调用中的值不一致；现有代码证据未显示训练时传入的默认值，不能据此判断训练配置是否一致。'
- `ddpm-ema` fixed #1: expected CONSISTENT, got INCONSISTENT — '论文描述：模型参数 EMA 衰减系数为 0.9999。代码：评估 worker 中创建 EMA 时传入 1e-10；但所给代码未展示训练时使用的默认衰减系数。因此，无法据此确认代码默认值是否与论文一致；所见评估代码的取值与论文不同。'
- `ddpm-lr` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的学习率设为 2×10⁻⁴（未进行扫描）。代码方面，当前候选片段未提供 CIFAR10 训练脚本的默认学习率，因此无法比较是否一致；这不表示仓库中没有相关设置。'
- `ddpm-lr` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文说明 CIFAR10 学习率设为 2×10⁻⁴，且未进行搜索；但当前代码候选未提供 CIFAR10 训练脚本的默认学习率，无法判断两者是否一致。'
- `ddpm-lr` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 的学习率设为 2×10⁻⁴，未进行扫参。代码侧：当前候选未定位到 CIFAR10 训练脚本的默认学习率，因此无法判断两者是否一致。'
- `ddpm-lr-256` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文称，256×256 图像的学习率降至 2×10⁻⁵（较大学习率训练不稳定）。代码候选仅显示 CelebA-HQ 数据分辨率为 256，未提供训练脚本的学习率默认值；因此无法判断二者是否一致，当前候选未定位到该默认值。'
- `ddpm-lr-256` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文描述：对 256×256 图像将学习率降至 2×10⁻⁵；较大学习率训练不稳定。代码证据：当前候选未定位到 CelebA-HQ 训练脚本的默认学习率，因此无法判断两者是否一致。'
- `ddpm-lr-256` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文说明：256×256 图像的学习率降至 2×10⁻⁵；较大图像学习率下训练似乎不稳定。代码候选未提供 CelebA-HQ 训练脚本或其默认学习率，因此无法比较是否一致。'
- `ddpm-lrx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 学习率设为 2×10⁻⁴（未进行搜索）。代码方面：当前候选未定位到 CIFAR10 训练脚本的默认学习率；通用训练函数接收 `lr` 参数，但没有给出其默认值。因此无法判断两者是否一致。'
- `ddpm-lrx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 学习率设为 2×10⁻⁴，且未进行学习率扫参（256×256 图像则降为 2×10⁻⁵）。代码候选仅显示通用训练函数接收学习率参数 `lr`，未提供 CIFAR10 训练脚本的默认值。因此，依据当前证据无法判断两者是否一致。'
- `ddpm-lrx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文描述：CIFAR10 学习率设为 2×10⁻⁴，且未进行 sweep。代码候选中未找到 CIFAR10 训练脚本的默认学习率，因此无法判断两者是否一致；这不代表仓库中没有该实现。'
- `ddpm-steps` fixed #0: expected CONSISTENT, got ABSTAIN — '论文候选文本没有给出扩散步数 T 的具体值；训练脚本候选代码也未显示默认步数的定义或取值。因此无法判断两者是否一致。'
- `ddpm-steps` fixed #1: expected CONSISTENT, got ABSTAIN — '论文候选文本未给出扩散步数 T 的具体值；训练脚本候选内容也未显示默认 T 值。因此无法判断两者是否一致。'
- `ddpm-steps` fixed #2: expected CONSISTENT, got ABSTAIN — '论文候选文本提到扩散过程有 T 步，但没有给出 T 的具体数值。当前代码候选也未显示训练脚本的默认扩散步数，因此无法判断两者是否一致。'
- `ddpm-stepsx` fixed #0: expected INCONSISTENT, got ABSTAIN — '论文候选文本未给出扩散步数 T 的具体值；代码候选只说明步数由 betas 数组长度决定，没有提供训练脚本默认值或该数组长度。因此无法判断是否一致。'
- `ddpm-stepsx` fixed #1: expected INCONSISTENT, got ABSTAIN — '论文候选文本未给出扩散步数 T 的具体值；代码候选也未显示训练脚本默认值或扩散步数配置。因此无法判断两者是否一致。'
- `ddpm-stepsx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文提到插值在扩散 1000 步后源图像信息会丢失，但这段文字没有明确说明训练设置的 T。代码候选显示采样过程使用 `self.num_timesteps`，但未提供该值或训练脚本默认值。因此，依据当前证据无法判断二者是否一致；默认值目前未定位。'
- `dino-knn-temp` agent #2: expected CONSISTENT, got ABSTAIN — '论文说明采用加权 k-NN，但没有给出投票温度 τ 的数值；代码中 `eval_knn.py` 的 `--temperature` 默认值是 `0.07`。因此，现有证据不足以判断两者是否一致。'
- `dino-knn-temp` fixed #0: expected CONSISTENT, got ABSTAIN — '论文说明 k-NN 加权投票使用温度 τ，但提供的论文片段没有给出 τ 的具体数值；代码候选中也没有显示 k-NN 评估温度参数或其默认值。因此无法判断二者是否一致。'
- `dino-knn-temp` fixed #1: expected CONSISTENT, got ABSTAIN — '论文说明 k-NN 使用加权投票，但所给片段未显示温度 τ 的数值；所给代码候选也未定位到 k-NN 评估中 τ 的默认值。因此无法判断二者是否一致。'
- `dino-knn-temp` fixed #2: expected CONSISTENT, got ABSTAIN — '论文说明 k-NN 使用加权投票，但所给论文摘录没有给出温度 τ 的取值。所给代码候选也未定位到 k-NN 评估的温度参数或其默认值；训练代码中的温度参数不能据此视为 k-NN 投票温度。因此无法判断两者是否一致。'
- `dino-knn-tempx` fixed #0: expected INCONSISTENT, got ABSTAIN — '论文说明 k-NN 使用加权投票，但所给段落未显示温度 τ 的数值；代码候选仅给出评估命令，未显示 k-NN 评估代码的 τ 默认值。因此无法判断二者是否一致。'
- `dino-knn-tempx` fixed #1: expected INCONSISTENT, got ABSTAIN — '无法确认是否一致：论文说明 k-NN 使用加权投票，但当前论文摘录未显示温度 τ 的具体值；代码候选也未提供 k-NN 实现中的 τ 默认值。README 仅给出运行评估脚本的命令，不能据此比较两者。'
- `dino-knn-tempx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文：说明 k-NN 使用加权分类器，但所给文本未给出加权投票温度 τ 的数值（p5_b3、p13_b12）。\n代码：所给候选包含 k-NN 评估运行说明，但未定位到评估代码的温度参数或默认值（c00015）。\n因此无法比较二者是否一致；目前证据不足，不能据此判定一致或不一致。'
- `dino-linear-layers` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文说明对 ViT-S 线性评估时拼接最后 l 层的 [CLS] token，但所给论文片段未给出 l 的具体数值（p19_b2）。代码候选仅显示 ViT-S 评估命令未显式指定层数；没有提供线性评估脚本中该参数的默认值。因此无法判断是否一致。'
- `dino-linear-layers` fixed #1: expected CONSISTENT, got ABSTAIN — '论文说明 ViT-S 线性评估会拼接最后 l 层的 [CLS] token，但所给片段没有给出 l 的具体值。代码候选仅显示 README 中 ViT-S 的评估命令未显式传入层数，以及 ViT-B 示例显式设为 1；没有展示线性评估代码的默认值。因此现有证据不足以判断两者是否一致。'
- `dino-linear-layers` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文描述：ViT-S 线性评估时拼接最后 l 层的 [CLS] token，但所给片段未说明 l 的具体值。代码候选未提供线性评估脚本中该参数的默认值；README 仅给出 ViT-S 的评估命令，未显式指定层数。因此无法判断是否一致。'
- `dino-momentum` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未提供教师网络动量更新系数的初始值，无法判断是否一致。代码将其默认值设为 0.996，并在训练中按余弦调度增加至 1。'
- `dino-optimizer` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文候选文本没有说明预训练所用优化器，无法据此确认论文设置。代码中优化器默认值为 AdamW（`adamw`）。因此无法判断两者是否一致。'
- `dino-optimizer` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未说明预训练所用优化器，因此无法判断是否与代码默认值一致。代码将默认优化器设为 AdamW；ViT 推荐使用 AdamW，但这不能代替论文对实际预训练设置的说明。'
- `dino-optimizer` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未说明预训练使用的优化器，因此无法核实论文设定。代码默认优化器为 AdamW；README 的 ViT-small 训练命令未指定优化器，会采用该默认值。故代码默认配置明确，但与论文设定是否一致，现有证据不足。'
- `dino-sinkhorn` agent #0: expected NOT_LOCATED, got INCONSISTENT — '论文消融中确实把 Sinkhorn–Knopp 作为教师输出处理方式之一进行比较；所查代码实现的是中心化与温度缩放后的 softmax，没有找到 Sinkhorn–Knopp 变体。因此该消融变体在这份代码中未见实现。'
- `dino-sinkhorn` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文在表15比较教师输出的 centering、batch softmax 与 Sinkhorn-Knopp；代码的 `DINOLoss` 实现 centering/sharpening 路径，没有找到 Sinkhorn-Knopp 的实现。因此就论文消融中该变体而言，未在此代码中实现。'
- `dino-sinkhorn` fixed #1: expected NOT_LOCATED, got PARTIAL — '论文描述了消融中比较教师输出的三种操作：centering、Sinkhorn-Knopp 和沿 batch 轴的 Softmax（J_e2）。代码中的 DINOLoss.forward 对教师输出执行减中心、按温度缩放后沿最后一维 Softmax；所示实现没有 Sinkhorn-Knopp 变体（c00083）。因此，'
- `dino-student-temp` agent #1: expected CONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `dino-student-temp` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文侧：当前提供的论文候选未定位到学生网络温度 τs 的数值。代码侧：DINOLoss 的 student_temp 默认值为 0.1。由于缺少论文数值，无法判断两者是否一致。'
- `dino-student-temp` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文材料未提供学生网络温度 τs 的取值，无法据此与代码默认值比较。代码中学生温度默认值为 0.1；因此是否一致无法判断。'
- `dino-student-temp` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文候选文本只给出教师温度 τt 的设置，未提供学生温度 τs 的数值，因此无法据此判断两者是否一致。代码中学生温度默认值为 0.1。'
- `dino-student-tempx` agent #0: expected INCONSISTENT, got ABSTAIN — '调查结论缺少可在本地论文与代码中核验的引用，本次回答已转为证据不足。'
- `dino-student-tempx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本未给出学生网络温度 τs 的数值，无法判断是否与代码默认值一致。代码中学生温度默认值为 0.2。'
- `dino-student-tempx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本未给出学生网络温度 τs 的取值，无法判断是否与代码一致。代码中 DINOLoss 的 student_temp 默认值为 0.2。因此，目前证据不足以比较两者。'
- `dino-student-tempx` fixed #2: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本仅给出教师温度 τt 的设置（0.04 到 0.07），未找到学生温度 τs 的值；代码中学生温度默认值为 0.2。因此，依据当前证据无法判断二者是否一致。'
- `dino-warmup` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未提供学习率线性 warmup 的 epoch 数；代码默认值为 10 个 epoch。因此根据现有证据无法判断两者是否一致。'
- `gat-const` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文明确报告了使用常数注意力的 Const-GAT；本代码实现的是学习注意力系数的 GAT 注意力头，没有找到常数注意力这一实现，因此论文描述与此代码库的实现不一致。'
- `gat-dropout` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文描述直推式任务中 dropout 概率 p=0.6，应用于两层的输入和归一化注意力系数。代码中对应的 dropout 值由 attn_drop 和 ffd_drop 输入；所给代码片段没有显示这两个值被设为多少，因此无法判断是否一致。关系：NOT_LOCATED（代码候选未定位到概率取值，并非证明仓库中没有设置）。'
- `gat-dropout` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文描述：直推式任务中 dropout 概率 p=0.6，应用于两层输入和归一化注意力系数。代码片段仅展示 dropout 参数默认值为 0.0，并按传入的 in_drop、coef_drop 执行 dropout；当前候选未给出直推式任务的实际参数传值。因此无法判断代码设置是否一致。'
- `gat-dropoutx` agent #1: expected INCONSISTENT, got MIXED — '- 论文规定直推任务的 dropout 概率为 `p=0.6`，用于两层的输入及归一化注意力系数。\n- 代码在 Cora 训练时为两者都传入 `0.5`，因此概率设置不一致；验证时则关闭 dropout（`0.0`）。'
- `gat-dropoutx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文描述：直推式任务中，dropout 概率 p=0.6，应用于两层输入及归一化注意力系数（Pubmed 的其他调整不改变此设置）。代码实现：注意力头分别用 ffd_drop 对输入特征做 dropout、用 attn_drop 对注意力系数做 dropout；当前候选代码未显示这两个参数实际传入的数值。因此无法确认概'
- `gat-dropoutx` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文描述：直推式任务中 dropout 概率 p=0.6，应用于两层的输入及归一化注意力系数。代码片段：注意力层接收输入 dropout（in_drop）和系数 dropout（coef_drop）参数，并在非零时执行 dropout，但未给出直推式任务实际传入的概率值。因此无法判断代码设置是否与论文一致。'
- `gat-dropoutx` fixed #2: expected INCONSISTENT, got PARTIAL — '论文描述：直推式任务中 dropout 概率为 p=0.6，施加于两层输入及归一化注意力系数。\n代码实现：候选代码仅显示 dropout 参数由调用方传入，并用于输入特征和注意力系数；未提供直推式任务实际传入的概率值。\n因此无法判断代码设置是否与论文一致；现有证据不足以认定数值相同或不同。'
- `gat-hiddenx` agent #0: expected INCONSISTENT, got MIXED — '论文与代码的每头输出特征数不一致：论文在 Cora 上第一层每个注意力头计算 8 个特征，代码配置为每头 16 个特征。第一层头数则一致，均为 8。'
- `gat-l2` agent #0: expected CONSISTENT, got MIXED — 'Cora/Citeseer 直推式任务的 L2 系数在论文与代码中一致，都是 `0.0005`。代码将该参数传入训练函数并用于 L2 正则项。论文还指出 Pubmed 使用 `0.001`；本仓库所查的 Cora 脚本不代表 Pubmed 配置。'
- `gat-l2` agent #2: expected CONSISTENT, got MIXED — '论文直推式任务通常采用的 L2 系数与代码一致：论文对 Cora/Citeseer 设 λ=0.0005，`execute_cora.py` 和 `execute_cora_sparse.py` 均设 `l2_coef = 0.0005`，并传入训练函数用于 L2 正则化。需注意论文另述 Pubmed 使用 λ=0.0'
- `gat-l2` fixed #0: expected CONSISTENT, got PARTIAL — '论文描述：直推式任务中，Cora 和 CiteSeer 使用 λ=0.0005；Pubmed 因训练集较小将其加强为 λ=0.001。\n代码实现：当前有证据的 Cora 训练脚本设置 l2_coef=0.0005，并将其传入训练函数；未找到 CiteSeer 或 Pubmed 的对应正则化系数设置。\n差异：Cora 的'
- `gat-l2` fixed #1: expected CONSISTENT, got PARTIAL — '论文说明：Cora 和 CiteSeer 的直推式任务使用 L2 系数 λ=0.0005；Pubmed 使用 λ=0.001。代码中 Cora 训练脚本设置 l2_coef=0.0005。因此，对 Cora 设置一致；不能据现有代码候选确认 CiteSeer 或 Pubmed 的代码设置是否一致。'
- `gat-l2` fixed #2: expected CONSISTENT, got PARTIAL — '论文描述：直推式任务中，Cora 和 CiteSeer 使用 L2 系数 λ=0.0005；Pubmed 将其加强为 λ=0.001（另有输出头数调整）。代码的 Cora 训练脚本设置 l2_coef=0.0005，并将其传入训练函数。因此，Cora 的值一致；当前代码证据只显示 Cora 设置，不能据此判断 Cite'
- `gat-l2x` agent #2: expected INCONSISTENT, got MIXED — '代码与论文的直推式 L2 系数不一致：论文对 Cora/Citeseer 设为 0.0005（Pubmed 为 0.001），而仓库 Cora 训练脚本设置为 0.005。'
- `gat-leakyrelu` fixed #0: expected CONSISTENT, got PARTIAL — '论文描述注意力机制对 logits 应用 LeakyReLU，负输入斜率 α=0.2。代码在稠密和稀疏注意力头中都调用 `tf.nn.leaky_relu`，因此实现了该激活；但所给代码片段未显示显式设置斜率，无法确认代码中的斜率值是否为 0.2。'
- `gat-leakyrelu` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文描述：注意力机制使用 LeakyReLU，负输入斜率 α = 0.2。代码候选片段仅显示模型层将注意力头输出接入配置的激活函数；现有片段未展示注意力系数计算及其非线性函数，因此无法确认代码是否实现了该 LeakyReLU。'
- `gat-leakyrelu` fixed #2: expected CONSISTENT, got PARTIAL — '论文描述：注意力机制的单层前馈网络使用 LeakyReLU，负输入斜率 α=0.2。代码实现：稠密与稀疏注意力头都对注意力 logits 使用 LeakyReLU，但候选代码未显示显式指定斜率。总体上实现了该激活机制；是否采用论文所述 α=0.2，现有证据无法确认。'
- `gat-patiencex` fixed #1: expected INCONSISTENT, got NOT_LOCATED — '论文描述：在验证集交叉熵损失及准确率（传导式）或 micro-F1（归纳式）上早停，patience 为 100 个 epoch。代码描述：早停计数达到变量 `patience` 时停止，但当前代码证据未显示该变量的赋值，因此无法核实其数值是否为 100。'
- `simsiam-pred` fixed #0: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未提供 prediction MLP 隐藏层维度，无法确认论文所述值。代码将预测器隐藏维度设为 `pred_dim=512`，且命令行默认值也是 512。因此不能判断两者是否一致。'
- `simsiam-pred` fixed #1: expected CONSISTENT, got NOT_LOCATED — '论文候选文本未提供 prediction MLP 隐藏层维度，无法核实论文数值。代码中 predictor 的隐藏层默认维度为 512，因此现有证据不足以判断两者是否一致。'
- `simsiam-predx` fixed #0: expected INCONSISTENT, got NOT_LOCATED — '论文候选文本未给出 prediction MLP 隐藏层维度，无法判断是否与代码默认值一致。代码的构造参数和命令行默认值均为 1024；但 builder 注释写着默认 512，与这两个代码默认值不一致。'
- `simsiam-projector` fixed #1: expected CONSISTENT, got INCONSISTENT — '论文描述：仅说明 CIFAR-10 使用 ResNet-18 后接 **2 层 projection MLP**；所给论文证据未说明各层是否有 BN，也未说明输出层是否有 ReLU。代码实现：projector 为 **3 层**，前两层各接 BN 和 ReLU；输出层接 BN（`affine=False`），不接 R'
- `simsiam-projector` fixed #2: expected CONSISTENT, got NOT_LOCATED — '论文给出的候选证据未说明 projection MLP 的层数、各层是否使用 BN，或输出层是否有 ReLU；因此无法据此核对论文描述。代码实现为 3 层 projection MLP：前两层各为 Linear、BN、ReLU；输出层为 Linear（使用原 encoder 的 fc）、BN（affine=False）'
- `simsiam-warmup` agent #0: expected NOT_LOCATED, got ABSTAIN — '目前不足以完成逐条对照：已核实代码使用按 epoch 的余弦学习率调度，但本次调查没有取得论文关于大 batch warm-up 的原文证据，因此不能判断两者是否一致。'
- `simsiam-warmup` agent #1: expected NOT_LOCATED, got INCONSISTENT — '论文明确称 batch size ≥1024 时使用 10 个 epoch 的 warm-up；代码里的 `main_simsiam.py` 学习率函数只有余弦衰减（及可选固定 predictor 学习率），没有 warm-up 阶段，因此该实验设置未在代码中实现。'
- `simsiam-warmup` agent #2: expected NOT_LOCATED, got INCONSISTENT — '论文规定 batch size ≥1024 时进行 10 个 epoch 的 warm-up；代码没有实现该 warm-up。训练循环每个 epoch 仅调用余弦退火学习率调整，因此该点不一致。'
- `simsiam-warmup` fixed #0: expected NOT_LOCATED, got PARTIAL — '论文说明：batch size ≥1024 时使用 10 个 epoch 的学习率 warm-up。代码中可见按 epoch 调用学习率调整函数，但该函数只设置余弦衰减（及可选固定预测器学习率），没有 warm-up 逻辑。因此，论文描述的 warm-up 未在当前代码证据中找到实现。'
