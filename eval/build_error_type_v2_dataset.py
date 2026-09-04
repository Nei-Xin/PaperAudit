"""从冻结 v1 样本生成错误类型规范 v2 的四组正式金标。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from paperaudit.pdf_parser import parse_pdf


EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EVAL_DIR / "error_type_v2"

DATASETS = {
    "holdout": ("holdout_resolved_samples.jsonl", "holdout_papers.json"),
    "broad": ("broad_resolved_samples.jsonl", "broad_papers.json"),
    "body": ("body_resolved_samples.jsonl", "broad_papers.json"),
    "cross_v2": ("cross_resolved_samples_v2.jsonl", "cross_papers_v2.json"),
}

UPDATES: dict[tuple[str, str], dict[str, Any]] = {
    ("holdout", "vit_008"): {
        "construction": "contradiction",
        "gold_label": "CONTRADICTED",
        "gold_error_type": "contradiction",
        "gold_severity": "high",
    },
    ("holdout", "dqn_008"): {
        "construction": "numeric_or_metric_mismatch",
        "gold_label": "CONTRADICTED",
        "gold_error_type": "numeric_or_metric_mismatch",
        "gold_severity": "high",
    },
    ("broad", "gcn_003"): {
        "construction": "numeric_or_metric_mismatch",
        "gold_label": "CONTRADICTED",
        "gold_error_type": "numeric_or_metric_mismatch",
        "gold_severity": "high",
    },
    ("broad", "ddpm_007"): {
        "construction": "external_hallucination",
        "gold_label": "NO_SUPPORT_FOUND",
        "gold_error_type": "external_hallucination",
        "gold_severity": "high",
    },
    ("body", "gcn_body_004"): {
        "construction": "external_hallucination",
        "gold_label": "NO_SUPPORT_FOUND",
        "gold_error_type": "external_hallucination",
        "gold_severity": "high",
    },
    ("body", "gcn_body_008"): {
        "construction": "supported",
        "gold_label": "SUPPORTED",
        "gold_error_type": None,
        "gold_severity": "none",
    },
    ("cross_v2", "w2v2_007"): {
        "construction": "external_hallucination",
        "gold_label": "NO_SUPPORT_FOUND",
        "gold_error_type": "external_hallucination",
        "gold_severity": "high",
    },
}

REPLACEMENTS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("cross_v2", "dqn2_008"): [
        {
            "sample_id": "dqn2_008a",
            "claim_id": "T008A",
            "report_text": "该模型采用 U-Net 架构。",
            "query_en": "DQN model uses the U-Net architecture",
            "construction": "external_hallucination",
            "gold_label": "NO_SUPPORT_FOUND",
            "gold_error_type": "external_hallucination",
            "gold_severity": "high",
            "source_quote": (
                "The model is a convolutional neural network, trained with a variant of Q-learning"
            ),
            "gold_evidence_chunk_ids": ["p1_b7"],
        },
        {
            "sample_id": "dqn2_008b",
            "claim_id": "T008B",
            "report_text": "该模型用于医学图像分割。",
            "query_en": "DQN model is used for medical image segmentation",
            "construction": "external_hallucination",
            "gold_label": "NO_SUPPORT_FOUND",
            "gold_error_type": "external_hallucination",
            "gold_severity": "high",
            "source_quote": "We apply our method to seven Atari 2600 games",
            "gold_evidence_chunk_ids": ["p1_b7"],
        },
    ],
    ("cross_v2", "w2v2_006"): [
        {
            "sample_id": "w2v2_006a",
            "claim_id": "T006A",
            "report_text": "该论文将词向量用于图像识别任务。",
            "query_en": "paper applies word vectors to image recognition tasks",
            "construction": "external_hallucination",
            "gold_label": "NO_SUPPORT_FOUND",
            "gold_error_type": "external_hallucination",
            "gold_severity": "high",
            "source_quote": "The quality of these representations is measured in a word similarity task",
            "gold_evidence_chunk_ids": ["p1_b15"],
        },
        {
            "sample_id": "w2v2_006b",
            "claim_id": "T006B",
            "report_text": "词向量不适用于语言任务。",
            "query_en": "word vectors are not applicable to language tasks",
            "construction": "contradiction",
            "gold_label": "CONTRADICTED",
            "gold_error_type": "contradiction",
            "gold_severity": "high",
            "source_quote": "The quality of these representations is measured in a word similarity task",
            "gold_evidence_chunk_ids": ["p1_b15"],
        },
    ],
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _replacement(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    row = dict(base)
    row.update(update)
    row["numbers"] = []
    row["metric"] = None
    row["source_page"] = 1
    row["provided_evidence"] = "第1页"
    row["evidence_match_score"] = 1.0
    return row


def _validate_taxonomy(row: dict[str, Any]) -> None:
    label = row["gold_label"]
    error = row.get("gold_error_type")
    severity = row["gold_severity"]
    if label == "SUPPORTED" and (error is not None or severity != "none"):
        raise ValueError(f"{row['sample_id']} 的支持标签映射无效。")
    if label == "PARTIALLY_SUPPORTED" and (
        error not in {"missing_condition", "overgeneralization"} or severity != "medium"
    ):
        raise ValueError(f"{row['sample_id']} 的部分支持标签映射无效。")
    if label == "CONTRADICTED" and (
        error
        not in {"contradiction", "numeric_or_metric_mismatch", "wrong_attribution"}
        or severity != "high"
    ):
        raise ValueError(f"{row['sample_id']} 的矛盾标签映射无效。")
    if label == "NO_SUPPORT_FOUND" and (
        error != "external_hallucination" or severity != "high"
    ):
        raise ValueError(f"{row['sample_id']} 的无支持标签映射无效。")


def build() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    parsed_chunk_ids: dict[str, set[str]] = {}
    for name, (samples_name, papers_name) in DATASETS.items():
        source_rows = _load_jsonl(EVAL_DIR / samples_name)
        output_rows: list[dict[str, Any]] = []
        for source in source_rows:
            key = (name, str(source["sample_id"]))
            if key in REPLACEMENTS:
                output_rows.extend(_replacement(source, item) for item in REPLACEMENTS[key])
                continue
            row = dict(source)
            row.update(UPDATES.get(key, {}))
            output_rows.append(row)

        sample_ids = [str(row["sample_id"]) for row in output_rows]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError(f"{name} 存在重复 sample_id。")
        claim_keys = [(str(row["paper_id"]), str(row["claim_id"])) for row in output_rows]
        if len(claim_keys) != len(set(claim_keys)):
            raise ValueError(f"{name} 存在重复 paper_id/claim_id。")

        papers = json.loads((EVAL_DIR / papers_name).read_text(encoding="utf-8"))
        paper_by_id = {str(paper["paper_id"]): paper for paper in papers}
        for row in output_rows:
            _validate_taxonomy(row)
            paper = paper_by_id.get(str(row["paper_id"]))
            if paper is None:
                raise ValueError(f"{name}/{row['sample_id']} 缺少论文清单。")
            pdf_path = EVAL_DIR / str(paper["local_pdf"])
            pdf_bytes = pdf_path.read_bytes()
            if hashlib.sha256(pdf_bytes).hexdigest() != paper["sha256"]:
                raise ValueError(f"{paper['local_pdf']} SHA-256 不匹配。")
            cache_key = str(pdf_path.resolve())
            if cache_key not in parsed_chunk_ids:
                parsed_chunk_ids[cache_key] = {
                    chunk.chunk_id for chunk in parse_pdf(pdf_bytes).chunks
                }
            missing = set(str(value) for value in row["gold_evidence_chunk_ids"]) - (
                parsed_chunk_ids[cache_key]
            )
            if missing:
                raise ValueError(f"{name}/{row['sample_id']} 缺少金标 chunk：{sorted(missing)}")

        output_name = f"{name}_resolved_samples.jsonl"
        papers_output_name = f"{name}_papers.json"
        output_path = OUTPUT_DIR / output_name
        papers_output_path = OUTPUT_DIR / papers_output_name
        _write_jsonl(output_path, output_rows)
        papers_output_path.write_text(
            json.dumps(papers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest_rows.append(
            {
                "name": name,
                "source_samples": samples_name,
                "samples": output_name,
                "papers": papers_output_name,
                "source_sample_count": len(source_rows),
                "sample_count": len(output_rows),
                "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            }
        )

    manifest = {
        "version": "error-taxonomy-v2",
        "status": "reviewed",
        "policy": "v1 冻结文件保持不变；v2 仅应用已审定重标和原子化替换。",
        "taxonomy": "../error_taxonomy_v2.md",
        "annotation_review": "../error_type_annotation_review_v2.jsonl",
        "relabel_count": len(UPDATES),
        "rewritten_source_count": len(REPLACEMENTS),
        "replacement_sample_count": sum(len(rows) for rows in REPLACEMENTS.values()),
        "datasets": manifest_rows,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
