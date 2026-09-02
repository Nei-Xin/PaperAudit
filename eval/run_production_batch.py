"""Process a fixed batch of unseen public papers for v1 runtime observation.

This is an operational observation job, not a labeled benchmark and not a rule-tuning job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from paperaudit.config import Settings
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOAD_DIR = ROOT / "tmp" / "production_batch_v1"
DEFAULT_STORAGE = Path(r"D:\data\tmp\PaperAuditData")


@dataclass(frozen=True)
class PaperSpec:
    key: str
    arxiv_id: str
    expected_title: str
    report: str


PAPERS_BATCH_1 = (
    PaperSpec("bart", "1910.13461v1", "BART", "The paper presents BART, a denoising autoencoder for pretraining sequence-to-sequence models. It corrupts text with arbitrary noising and trains reconstruction, then evaluates on language understanding and generation tasks."),
    PaperSpec("t5", "1910.10683v1", "Exploring the Limits", "The paper proposes a unified text-to-text framework that casts diverse NLP tasks as text-to-text problems. It pretrains a Transformer on a large unlabeled corpus and evaluates transfer across benchmarks."),
    PaperSpec("dino", "2104.14294v1", "Emerging Properties in Self-Supervised Vision Transformers", "The paper introduces a self-distillation method for learning visual features without labels. It trains student and teacher networks and evaluates the learned representations on image tasks."),
    PaperSpec("mae", "2111.06377v1", "Masked Autoencoders Are Scalable Vision Learners", "The paper proposes masked autoencoders that reconstruct missing image patches from visible patches. It uses an asymmetric encoder-decoder architecture and evaluates self-supervised pretraining."),
    PaperSpec("ppo", "1707.06347v2", "Proximal Policy Optimization Algorithms", "The paper proposes proximal policy optimization, a policy gradient method that alternates data collection and multiple epochs of minibatch updates. It uses a clipped surrogate objective."),
    PaperSpec("sac", "1801.01290v2", "Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor", "The paper presents soft actor-critic, an off-policy actor-critic algorithm based on maximum entropy reinforcement learning. It optimizes expected return together with policy entropy."),
    PaperSpec("dgi", "1809.10341v1", "Deep Graph Infomax", "The paper introduces Deep Graph Infomax for unsupervised representation learning on graphs. It maximizes mutual information between local node representations and a global summary."),
    PaperSpec("tabnet", "1908.07442v1", "TabNet: Attentive Interpretable Tabular Learning", "The paper proposes TabNet, a sequential attention model for tabular data. It uses interpretable feature selection at each decision step and supports end-to-end learning."),
)

PAPERS_BATCH_2 = (
    PaperSpec("nin", "1312.4400v3", "Network In Network", "The paper introduces Network In Network, a neural network architecture that uses micro neural networks to improve local feature modeling. It evaluates the architecture on image classification benchmarks."),
    PaperSpec("seq2seq", "1409.3215v3", "Sequence to Sequence Learning with Neural Networks", "The paper introduces a general end-to-end approach to sequence to sequence learning. It uses a multilayered Long Short-Term Memory network to map an input sequence to an output sequence."),
    PaperSpec("deeplab", "1506.04579v2", "Semantic segmentation", "The paper proposes a semantic image segmentation method that combines deep convolutional networks with fully connected conditional random fields. It evaluates the approach on the PASCAL VOC 2012 segmentation benchmark."),
    PaperSpec("retinanet", "1708.02002v2", "Focal Loss for Dense Object Detection", "The paper introduces focal loss to address the extreme foreground-background class imbalance in dense object detection. It builds RetinaNet and evaluates it against one-stage and two-stage detectors."),
    PaperSpec("ddpg", "1509.02971v6", "Continuous control", "The paper presents an actor-critic algorithm for continuous action spaces. It combines deterministic policy gradients with deep function approximators and experience replay."),
    PaperSpec("a3c", "1602.01783v2", "Asynchronous Methods for Deep Reinforcement Learning", "The paper introduces asynchronous actor-critic methods for deep reinforcement learning. Multiple actor-learners run in parallel and update shared model parameters."),
    PaperSpec("graphsage", "1706.02216v4", "Inductive Representation Learning on Large Graphs", "The paper proposes GraphSAGE, an inductive framework that generates node embeddings by sampling and aggregating features from a node's local neighborhood. It evaluates the method on several graph tasks."),
    PaperSpec("pointnet", "1612.00593v2", "PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation", "The paper introduces PointNet, a neural network that directly consumes point clouds. It performs classification and segmentation while being invariant to input point permutations."),
)

PAPERS_BATCH_3 = (
    PaperSpec("hubert", "2106.07447v1", "HuBERT", "The paper presents HuBERT, a self-supervised speech representation learning approach based on masked prediction of hidden units. It evaluates the learned representations on speech recognition tasks."),
    PaperSpec("timesnet", "2210.02186v2", "TimesNet", "The paper proposes TimesNet for general time series analysis. It transforms one-dimensional time series into two-dimensional variations and evaluates the approach across forecasting and classification tasks."),
)

PAPERS_BATCH_4 = (
    PaperSpec("whisper", "2212.04356v1", "Robust Speech Recognition", "The paper presents a large-scale weakly supervised approach for speech recognition. It trains an encoder-decoder Transformer on diverse audio and text data and evaluates zero-shot transfer across speech tasks."),
    PaperSpec("clap", "2211.06687v1", "Contrastive Language-Audio Pretraining", "The paper introduces a contrastive language-audio pretraining model that learns aligned representations from audio and text. It evaluates the representations on audio classification and retrieval tasks."),
    PaperSpec("informer", "2012.07436v1", "Informer", "The paper proposes Informer for efficient long sequence time-series forecasting. It introduces ProbSparse self-attention and a generative-style decoder for long-horizon prediction."),
    PaperSpec("patchtst", "2211.14730v1", "A Time Series is Worth 64 Words", "The paper proposes PatchTST for long-term time-series forecasting. It segments time series into patches and applies a Transformer to the patch tokens."),
    PaperSpec("perceiver", "2103.03206v2", "Perceiver", "The paper introduces Perceiver, an architecture that uses iterative attention to process inputs from different modalities. It reduces the dependence of attention cost on the input size."),
    PaperSpec("flamingo", "2204.14198v1", "Flamingo", "The paper presents Flamingo, a visual language model for few-shot learning. It interleaves frozen vision and language models and evaluates few-shot multimodal tasks."),
    PaperSpec("blip", "2201.12086v1", "BLIP", "The paper proposes BLIP for unified vision-language understanding and generation. It introduces a bootstrapping method that improves noisy image-text pretraining data."),
    PaperSpec("moco", "1911.05722v2", "Momentum Contrast", "The paper introduces Momentum Contrast for unsupervised visual representation learning. It maintains a dynamic dictionary with a queue and a momentum-updated encoder."),
    PaperSpec("simclr", "2002.05709v2", "A Simple Framework for Contrastive Learning", "The paper presents a simple framework for contrastive learning of visual representations. It studies data augmentation, nonlinear projection heads, and large-batch training."),
    PaperSpec("ast", "2104.01778v2", "Audio Spectrogram Transformer", "The paper applies a vision Transformer architecture to audio classification by treating spectrograms as sequences of patches. It evaluates the approach on several audio benchmarks."),
)


def _download(spec: PaperSpec, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{spec.arxiv_id}.pdf"
    if not path.exists():
        urllib.request.urlretrieve(f"https://arxiv.org/pdf/{spec.arxiv_id}", path)
    return path


def run_batch(download_dir: Path, storage_root: Path, papers: tuple[PaperSpec, ...], batch_name: str) -> dict[str, object]:
    settings = Settings.from_env()
    if not settings.is_configured:
        raise RuntimeError("API 配置不完整。")
    service = AuditService(settings)
    store = ProjectStore(storage_root.resolve())
    rows: list[dict[str, object]] = []
    for spec in papers:
        pdf_path = _download(spec, download_dir)
        pdf_bytes = pdf_path.read_bytes()
        paper = parse_pdf(pdf_bytes)
        first_page_text = " ".join(chunk.content for chunk in paper.chunks if chunk.page <= 2)
        if (
            spec.expected_title.casefold() not in paper.title.casefold()
            and spec.expected_title.casefold() not in first_page_text.casefold()
        ):
            raise RuntimeError(f"标题校验失败：{spec.key} -> {paper.title}")
        metadata = store.save_paper_project(pdf_bytes, pdf_path.name, paper)
        source_label = f"v1 production observation {batch_name}"
        existing = [item for item in store.list_audit_runs(metadata.project_id) if item.source_label == source_label]
        if existing:
            audit_metadata = existing[0]
            _, run = store.load_audit_run(metadata.project_id, audit_metadata.audit_id)
        else:
            run = service.audit(
                paper,
                spec.report,
                [ClaimCategory.CONTRIBUTION, ClaimCategory.METHOD, ClaimCategory.RESULTS],
                mode="production_observation_v1",
            )
            audit_metadata = store.save_audit_run(
                metadata.project_id,
                run,
                source_type="uploaded_report",
                source_label=source_label,
                model=settings.model,
                reasoning_effort=settings.reasoning_effort,
                retrieval_top_k=settings.retrieval_top_k,
                judge_batch_size=settings.judge_batch_size,
            )
        rows.append(
            {
                "key": spec.key,
                "paper_title": paper.title,
                "page_count": paper.page_count,
                "chunk_count": len(paper.chunks),
                "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                "project_id": metadata.project_id,
                "audit_id": audit_metadata.audit_id,
                "audit_count": len(run.audits),
                "grade": run.summary.grade.value,
                "audit_coverage": run.summary.audit_coverage,
                "evidence_discovery_rate": run.summary.evidence_discovery_rate,
                "abstain_count": sum(a.judgment.label.value == "ABSTAIN" for a in run.audits),
            }
        )
    return {
        "passed": len(rows) == len(papers),
        "paper_count": len(rows),
        "papers": rows,
        "storage_root": str(storage_root.resolve()),
        "model": settings.model,
        "policy": "生产观测，不作为金标评测，不自动调参",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="运行 v1 生产观测新论文批次。")
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "production_batch_v1_result.json")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3, 4], default=1)
    args = parser.parse_args()
    papers = {1: PAPERS_BATCH_1, 2: PAPERS_BATCH_2, 3: PAPERS_BATCH_3, 4: PAPERS_BATCH_4}[args.batch]
    if args.download_dir == DEFAULT_DOWNLOAD_DIR and args.batch != 1:
        args.download_dir = ROOT / "tmp" / f"production_batch_v{args.batch}"
    if args.output == ROOT / "eval" / "production_batch_v1_result.json" and args.batch != 1:
        args.output = ROOT / "eval" / f"production_batch_v{args.batch}_result.json"
    result = run_batch(args.download_dir, args.storage_root, papers, f"batch 20260830-{args.batch}")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
