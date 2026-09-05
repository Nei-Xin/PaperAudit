# 预期论断与原文依据

沿用既有冻结标注；本文件仅便于核对，不修改金标。

## R002

### S0004 · 论文研究如何在点击率预测中同时学习低阶和高阶特征交互，并减少人工特征工程。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0007 · DeepFM 同时建模低阶和高阶特征交互。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0010 · DeepFM 除原始特征外不需要特征工程。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0012 · DeepFM 同时建模低阶和高阶特征交互。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0016 · DeepFM 在所有推荐数据集上都显著优于所有基线。

预期：PARTIALLY_SUPPORTED / medium

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0018 · DeepFM 的目标是预测用户点击率。

预期：SUPPORTED / none

p1_b7：

The prediction of click-through rate (CTR) is critical in rec-
ommender system, where the task is to estimate the probabil-
ity a user will click on a recommended item. In many recom-
mender systems the goal is to maximize the number of clicks,
and so the items returned to a user can be ranked by estimated
CTR; while in other application scenarios such as online ad-
vertising it is also important to improve revenue, and so the
ranking strategy can be adjusted as CTR×bid across all can-
didates, where “bid” is the beneﬁt the system receives if the
item is clicked by a user. In either case, it is clear that the key
is in estimating CTR correctly.

### S0013 · DeepFM 的宽部和深部共享相同的原始特征输入与嵌入。

预期：SUPPORTED / none

p2_b1：

(FM) [Rendle, 2010] model pairwise feature interactions as
inner product of latent vectors between features and show
very promising results. While in principle FM can model
high-order feature interaction, in practice usually only order-
2 feature interactions are considered due to high complexity.
As a powerful approach to learning feature representa-
tion, deep neural networks have the potential to learn so-
phisticated feature interactions.
Some ideas extend CNN
and RNN for CTR predition [Liu et al., 2015; Zhang et
al., 2014], but CNN-based models are biased to the in-
teractions between neighboring features while RNN-based
models are more suitable for click data with sequential de-
pendency. [Zhang et al., 2016] studies feature representa-
tions and proposes Factorization-machine supported Neural
Network (FNN). This model pre-trains FM before applying
DNN, thus limited by the capability of FM. Feature interac-
tion is studied in [Qu et al., 2016], by introducing a prod-
uct layer between embedding layer and fully-connected layer,
and proposing the Product-based Neural Network (PNN). As
noted in [Cheng et al., 2016], PNN and FNN, like other deep
models, capture little low-order feature interactions, which
are also essential for CTR prediction. To model both low-
and high-order feature interactions, [Cheng et al., 2016] pro-
poses an interesting hybrid network structure (Wide & Deep)
that combines a linear (“wide”) model and a deep model. In
this model, two different inputs are required for the “wide
part” and “deep part”, respectively, and the input of “wide
part” still relies on expertise feature engineering.

### S0020 · DeepFM 在所有商业点击率预测场景中都带来一致提升。

预期：PARTIALLY_SUPPORTED / medium

p2_b5：

• We evaluate DeepFM on both benchmark data and com-
mercial data, which shows consistent improvement over
existing models for CTR prediction.

### S0021 · 论文在基准数据和商业数据上评估 DeepFM。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

### S0024 · 论文只报告基准数据和商业数据上的改进，不能据此推出所有线上广告平台都已部署。

预期：SUPPORTED / none

p1_b5：

Learning sophisticated feature interactions behind
user behaviors is critical in maximizing CTR for
recommender systems. Despite great progress, ex-
isting methods seem to have a strong bias towards
low- or high-order interactions, or require exper-
tise feature engineering. In this paper, we show
that it is possible to derive an end-to-end learn-
ing model that emphasizes both low- and high-
order feature interactions.
The proposed model,
DeepFM, combines the power of factorization ma-
chines for recommendation and deep learning for
feature learning in a new neural network architec-
ture. Compared to the latest Wide & Deep model
from Google, DeepFM has a shared input to its
“wide” and “deep” parts, with no need of feature
engineering besides raw features. Comprehensive
experiments are conducted to demonstrate the ef-
fectiveness and efﬁciency of DeepFM over the ex-
isting models for CTR prediction, on both bench-
mark data and commercial data.

## R005

### S0004 · 论文研究未经数据集预训练的生成网络结构能否充当图像恢复先验。

预期：SUPPORTED / none

p1_b9：

Deep convolutional networks have become a popular
tool for image generation and restoration. Generally, their
excellent performance is imputed to their ability to learn re-
alistic image priors from a large number of example images.
In this paper, we show that, on the contrary, the structure of
a generator network is sufﬁcient to capture a great deal of
low-level image statistics prior to any learning. In order
to do so, we show that a randomly-initialized neural net-
work can be used as a handcrafted prior with excellent re-
sults in standard inverse problems such as denoising, super-
resolution, and inpainting. Furthermore, the same prior
can be used to invert deep neural representations to diag-
nose them, and to restore images based on ﬂash-no ﬂash
input pairs.

### S0007 · 随机初始化的网络可以作为图像恢复的手工先验。

预期：SUPPORTED / none

p1_b9：

Deep convolutional networks have become a popular
tool for image generation and restoration. Generally, their
excellent performance is imputed to their ability to learn re-
alistic image priors from a large number of example images.
In this paper, we show that, on the contrary, the structure of
a generator network is sufﬁcient to capture a great deal of
low-level image statistics prior to any learning. In order
to do so, we show that a randomly-initialized neural net-
work can be used as a handcrafted prior with excellent re-
sults in standard inverse problems such as denoising, super-
resolution, and inpainting. Furthermore, the same prior
can be used to invert deep neural representations to diag-
nose them, and to restore images based on ﬂash-no ﬂash
input pairs.

### S0010 · DIP 可用于去噪、超分辨率和修复。

预期：SUPPORTED / none

p1_b9：

Deep convolutional networks have become a popular
tool for image generation and restoration. Generally, their
excellent performance is imputed to their ability to learn re-
alistic image priors from a large number of example images.
In this paper, we show that, on the contrary, the structure of
a generator network is sufﬁcient to capture a great deal of
low-level image statistics prior to any learning. In order
to do so, we show that a randomly-initialized neural net-
work can be used as a handcrafted prior with excellent re-
sults in standard inverse problems such as denoising, super-
resolution, and inpainting. Furthermore, the same prior
can be used to invert deep neural representations to diag-
nose them, and to restore images based on ﬂash-no ﬂash
input pairs.

### S0012 · DIP 的网络权重始终随机初始化，不从大型图像数据集预训练。

预期：SUPPORTED / none

p2_b4：

We show that this very simple formulation is very com-
petitive for standard image processing problems such as de-
noising, inpainting and super-resolution. This is particu-
larly remarkable because no aspect of the network is learned
from data; instead, the weights of the network are always
randomly initialized, so that the only prior information is in
the structure of the network itself. To the best of our knowl-
edge, this is the ﬁrst study that directly investigates the prior
captured by deep convolutional generative networks inde-
pendently of learning the network parameters from images.

### S0023 · DIP 在论文测试的多种逆问题上表现良好，包括去噪、超分辨率和修复。

预期：SUPPORTED / none

p1_b30：

Figure 1: Super-resolution using the deep image prior.
Our method uses a randomly-initialized convnet to upsam-
ple an image, using its strucrture as an image prior; similar
to bicubic upsampling, this method does not require learn-
ing, but produces much cleaner results with sharper edges.
In fact, our results are quite close to state-of-the-art super-
resolution methods that use ConvNets learned from large
datasets. The deep image prior works well for all inverse
problems we could test.

### S0014 · DIP 可用于去噪、超分辨率和图像修复。

预期：SUPPORTED / none

p1_b9：

Deep convolutional networks have become a popular
tool for image generation and restoration. Generally, their
excellent performance is imputed to their ability to learn re-
alistic image priors from a large number of example images.
In this paper, we show that, on the contrary, the structure of
a generator network is sufﬁcient to capture a great deal of
low-level image statistics prior to any learning. In order
to do so, we show that a randomly-initialized neural net-
work can be used as a handcrafted prior with excellent re-
sults in standard inverse problems such as denoising, super-
resolution, and inpainting. Furthermore, the same prior
can be used to invert deep neural representations to diag-
nose them, and to restore images based on ﬂash-no ﬂash
input pairs.

### S0016 · DIP 通过在单个退化图像上拟合生成器网络来恢复图像。

预期：SUPPORTED / none

p2_b3：

To show this, we apply untrained ConvNets to the so-
lution of several such problems. Instead of following the
common paradigm of training a ConvNet on a large dataset
of example images, we ﬁt a generator network to a single
degraded image. In this scheme, the network weights serve
as a parametrization of the restored image. The weights are
randomly initialized and ﬁtted to maximize their likelihood
given a speciﬁc degraded image and a task-dependent ob-
servation model.

### S0018 · DIP 的多数实验使用最多约两百万参数的编码器-解码器沙漏架构。

预期：SUPPORTED / none

p2_b18：

In this paper, we investigate the prior implicitly captured
by the choice of a particular generator network structure,
before any of its parameters are learned. We do so by inter-
preting the neural network as a parametrization x = fθ(z)
of an image x ∈R3×H×W . Here z ∈RC′×H′×W ′ is a
code tensor/vector and θ are the network parameters. The
network itself alternates ﬁltering operations such as convo-
lution, upsampling and non-linear activation. In particular,
most of our experiments are performed using am encoder-
decorder “hourglass” architecture with as many as two mil-
lion parameters θ (see Supplementary Material for details
of all used architectures).

### S0020 · 论文提供了 DIP 的代码和补充材料。

预期：SUPPORTED / none

p1_b13：

Code and supplementary material are available at https://
dmitryulyanov.github.io/deep_image_prior

### S0026 · 论文报告的是所测试逆问题上的表现，不能据此声称 DIP 在所有图像任务上都达到最先进水平。

预期：SUPPORTED / none

p1_b30：

Figure 1: Super-resolution using the deep image prior.
Our method uses a randomly-initialized convnet to upsam-
ple an image, using its strucrture as an image prior; similar
to bicubic upsampling, this method does not require learn-
ing, but produces much cleaner results with sharper edges.
In fact, our results are quite close to state-of-the-art super-
resolution methods that use ConvNets learned from large
datasets. The deep image prior works well for all inverse
problems we could test.

## R018

### S0004 · 论文研究如何在差分隐私框架下训练具有非凸目标的深度神经网络。

预期：SUPPORTED / none

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0007 · 论文提出了面向深度学习的差分隐私算法技术。

预期：SUPPORTED / none

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0015 · 实验在 MNIST 和 CIFAR-10 图像分类任务上评估方法。

预期：SUPPORTED / none

p1_b15：

3. We build on the machine learning framework Ten-
sorFlow [3] for training models with diﬀerential
privacy. We evaluate our approach on two stan-
dard image-classiﬁcation tasks, MNIST and CIFAR-
10. Our experience indicates that privacy protec-
tion for deep neural networks can be achieved at
a modest cost in software complexity, training ef-
ﬁciency, and model quality.

### S0010 · 该方法只适用于凸目标函数。

预期：CONTRADICTED / high

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0017 · 隐私保护不会带来任何软件复杂度、训练效率或模型质量成本。

预期：PARTIALLY_SUPPORTED / medium

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0019 · 论文使用单一隐私预算 epsilon=1。

预期：CONTRADICTED / high

p1_b10：

In this paper, we present the ﬁrst study that com-
bines state-of-the-art machine learning methods with
state-of-the-art privacy-preserving mechanisms, train-
ing neural networks within a modest (“single-digit”) pri-
vacy budget. We treat models with non-convex objec-
tives, several layers, and tens of thousands to millions of
parameters. (In contrast, previous work obtains strong
results on convex models with smaller numbers of pa-
rameters, or treats complex neural networks but with a
large privacy loss.) For this purpose, we develop new al-
gorithmic techniques, a reﬁned analysis of privacy costs

### S0024 · 方法保证模型永远不会泄露任何训练信息。

预期：PARTIALLY_SUPPORTED / medium

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0012 · 论文完全不涉及神经网络训练。

预期：CONTRADICTED / high

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0021 · 该隐私训练方法已在医疗生产数据上部署并通过监管认证。

预期：NO_SUPPORT_FOUND / high

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.

### S0026 · 论文将隐私训练的代价描述为可管理，而不是完全没有软件、效率或模型质量成本。

预期：SUPPORTED / none

p1_b7：

Machine learning techniques based on neural networks
are achieving remarkable results in a wide variety of do-
mains. Often, the training of models requires large, rep-
resentative datasets, which may be crowdsourced and
contain sensitive information. The models should not
expose private information in these datasets. Address-
ing this goal, we develop new algorithmic techniques for
learning and a reﬁned analysis of privacy costs within
the framework of diﬀerential privacy. Our implemen-
tation and experiments demonstrate that we can train
deep neural networks with non-convex objectives, un-
der a modest privacy budget, and at a manageable cost
in software complexity, training eﬃciency, and model
quality.
