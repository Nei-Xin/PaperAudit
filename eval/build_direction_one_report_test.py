"""构建方向一完整报告三档判别实验数据。"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EVAL_DIR / "direction_one_report_test"
SOURCE_SAMPLES = EVAL_DIR / "final_holdout_resolved_samples.jsonl"
SOURCE_PAPERS = EVAL_DIR / "final_holdout_papers.json"

TIER_REPORT_IDS = {
    "garnelo2018_neural_processes": {"high": "R014", "medium": "R003", "low": "R017"},
    "andrychowicz2016_learning_to_learn": {"high": "R008", "medium": "R015", "low": "R001"},
    "abadi2016_differential_privacy": {"high": "R011", "medium": "R006", "low": "R018"},
    "zoph2016_nas_rl": {"high": "R004", "medium": "R013", "low": "R009"},
    "guo2017_deepfm": {"high": "R016", "medium": "R002", "low": "R012"},
    "ulyanov2017_deep_image_prior": {"high": "R005", "medium": "R010", "low": "R007"},
}

RESEARCH_QUESTIONS = {
    "garnelo2018_neural_processes": (
        "论文研究如何结合神经网络与随机过程，以便根据上下文观测快速适应并表达预测不确定性。",
        "p1_b5",
        1,
    ),
    "andrychowicz2016_learning_to_learn": (
        "论文研究能否把优化算法本身的设计转化为学习问题。",
        "p1_b13",
        1,
    ),
    "abadi2016_differential_privacy": (
        "论文研究如何在差分隐私框架下训练具有非凸目标的深度神经网络。",
        "p1_b7",
        1,
    ),
    "zoph2016_nas_rl": (
        "论文研究如何利用强化学习自动生成有竞争力的神经网络架构。",
        "p1_b5",
        1,
    ),
    "guo2017_deepfm": (
        "论文研究如何在点击率预测中同时学习低阶和高阶特征交互，并减少人工特征工程。",
        "p1_b5",
        1,
    ),
    "ulyanov2017_deep_image_prior": (
        "论文研究未经数据集预训练的生成网络结构能否充当图像恢复先验。",
        "p1_b9",
        1,
    ),
}

LIMITATION_CLAIMS = {
    "garnelo2018_neural_processes": (
        "论文只在一系列具体任务上展示 NP，不能据此外推到所有任务。",
        "p1_b5",
        1,
    ),
    "andrychowicz2016_learning_to_learn": (
        "论文的优势结论针对训练任务，泛化结论限定于结构相似的新任务。",
        "p1_b13",
        1,
    ),
    "abadi2016_differential_privacy": (
        "论文将隐私训练的代价描述为可管理，而不是完全没有软件、效率或模型质量成本。",
        "p1_b7",
        1,
    ),
    "zoph2016_nas_rl": (
        "论文的实证结论来自 CIFAR-10 和 Penn Treebank，不能直接推广为所有领域的最优架构。",
        "p1_b5",
        1,
    ),
    "guo2017_deepfm": (
        "论文只报告基准数据和商业数据上的改进，不能据此推出所有线上广告平台都已部署。",
        "p1_b5",
        1,
    ),
    "ulyanov2017_deep_image_prior": (
        "论文报告的是所测试逆问题上的表现，不能据此声称 DIP 在所有图像任务上都达到最先进水平。",
        "p1_b30",
        1,
    ),
}

CORRECTED_TEXT = {
    "dp_final_003": "该方法能够训练具有非凸目标函数的深度神经网络。",
    "dp_final_004": "隐私训练在软件复杂度、训练效率和模型质量方面产生可管理的成本。",
    "dp_final_005": "论文在适度的个位数隐私预算下训练深度神经网络。",
    "dp_final_006": "该方法旨在降低模型暴露训练数据中私人信息的风险。",
    "dp_final_007": "论文明确研究了神经网络的差分隐私训练。",
    "dp_final_008": "实验表明该方法能够在差分隐私约束下训练深度神经网络。",
    "l2l_final_003": "学习优化器在训练任务上优于通用的手工设计优化器。",
    "l2l_final_004": "学习优化器能够泛化到结构相似的新任务。",
    "l2l_final_006": "实验覆盖简单凸问题、神经网络训练和神经艺术风格化等任务。",
    "l2l_final_007": "论文报告学习优化器在训练任务上优于通用手工优化器，但没有声称统一提升百分之五十。",
    "l2l_final_008": "论文研究学习得到的优化器，并评估其在训练任务和结构相似新任务上的表现。",
    "np_final_003": "Neural Processes 是概率模型，会定义函数分布。",
    "np_final_004": "训练后的 NP 前向推理复杂度随上下文点和目标点数量按 O(n+m) 线性增长。",
    "np_final_005": "论文在回归、优化等一系列任务上展示 NP，并与相关模型进行比较。",
    "np_final_006": "NP 可用于回归、优化和图像补全等多种任务。",
    "np_final_007": "NP 的推理复杂度为 O(n+m)，而经典高斯过程为 O((n+m)^3)。",
    "np_final_008": "NP 为学习函数分布，需要同时使用多个数据集进行训练。",
    "deepfm_final_003": "DeepFM 同时建模低阶和高阶特征交互。",
    "deepfm_final_004": "论文在基准数据和商业数据上实验，结果显示相对已有模型具有一致改进。",
    "deepfm_final_006": "DeepFM 的宽部和深部共享相同的原始特征输入与嵌入。",
    "deepfm_final_007": "DeepFM 在商业数据上相对已有模型表现出一致改进，但论文没有声称点击率提升百分之百。",
    "deepfm_final_008": "论文在基准数据和商业数据上评估 DeepFM。",
    "dip_final_003": "DIP 的网络权重始终随机初始化，不从大型图像数据集预训练。",
    "dip_final_004": "DIP 在论文测试的多种逆问题上表现良好，包括去噪、超分辨率和修复。",
    "dip_final_005": "DIP 可用于去噪、超分辨率和图像修复。",
    "dip_final_007": "DIP 的多数实验使用最多约两百万参数的编码器-解码器沙漏架构。",
    "dip_final_008": "论文提供了 DIP 的代码和补充材料。",
    "nas_final_003": "NAS 在 CIFAR-10 上的测试错误率是 3.84。",
    "nas_final_004": "NAS 同时在 CIFAR-10 图像识别和 Penn Treebank 语言建模上进行评估。",
    "nas_final_005": "NAS 在 CIFAR-10 上生成的架构可与最佳人工设计架构相媲美。",
    "nas_final_006": "NAS 控制器使用验证集准确率作为奖励信号，通过策略梯度更新。",
    "nas_final_007": "Penn Treebank 单元的测试困惑度为 62.4。",
    "nas_final_008": "论文表明 NAS 能在 CIFAR-10 和 Penn Treebank 上自动设计有竞争力的架构。",
}

MEDIUM_EXTRA = {
    "l2l_final_004": "学习优化器可以泛化到所有结构的新任务。",
    "deepfm_final_007": "DeepFM 在所有商业点击率预测场景中都带来一致提升。",
    "dip_final_002": "DIP 可用于所有图像恢复问题。",
    "nas_final_005": "NAS 生成的架构在所有图像数据集上都可与最佳人工设计架构相媲美。",
}

SECTION_TITLES = {
    "research_question": "研究问题",
    "contribution": "核心贡献",
    "method": "方法",
    "dataset_setup": "数据与实验设置",
    "results": "主要结果",
    "limitations": "局限与边界",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_claims(paper_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    question, chunk_id, page = RESEARCH_QUESTIONS[paper_id]
    claims = [
        {
            "source_sample_id": f"{paper_id}_research_question",
            "category": "research_question",
            "high_text": question,
            "source_page": page,
            "gold_evidence_chunk_ids": [chunk_id],
        }
    ]
    for row in rows:
        sample_id = str(row["sample_id"])
        claims.append(
            {
                "source_sample_id": sample_id,
                "category": str(row["category"]),
                "high_text": str(CORRECTED_TEXT.get(sample_id, row["report_text"])),
                "low_text": str(row["report_text"]),
                "source_page": int(row["source_page"]),
                "gold_evidence_chunk_ids": [str(value) for value in row["gold_evidence_chunk_ids"]],
                "source_gold_label": str(row["gold_label"]),
                "source_gold_error_type": row.get("gold_error_type"),
                "source_gold_severity": str(row["gold_severity"]),
            }
        )
    limitation, limitation_chunk, limitation_page = LIMITATION_CLAIMS[paper_id]
    claims.append(
        {
            "source_sample_id": f"{paper_id}_limitation",
            "category": "limitations",
            "high_text": limitation,
            "source_page": limitation_page,
            "gold_evidence_chunk_ids": [limitation_chunk],
        }
    )
    return claims


def _claim_for_tier(claim: dict[str, Any], tier: str) -> dict[str, Any]:
    result = dict(claim)
    result.update(
        {
            "text": claim["high_text"],
            "gold_label": "SUPPORTED",
            "gold_error_type": None,
            "gold_severity": "none",
            "citation_mode": "valid",
        }
    )
    if tier == "medium":
        if claim.get("source_gold_label") == "PARTIALLY_SUPPORTED":
            result.update(
                {
                    "text": claim["low_text"],
                    "gold_label": "PARTIALLY_SUPPORTED",
                    "gold_error_type": claim["source_gold_error_type"],
                    "gold_severity": "medium",
                }
            )
        elif claim["source_sample_id"] in MEDIUM_EXTRA:
            result.update(
                {
                    "text": MEDIUM_EXTRA[claim["source_sample_id"]],
                    "gold_label": "PARTIALLY_SUPPORTED",
                    "gold_error_type": "overgeneralization",
                    "gold_severity": "medium",
                }
            )
    elif tier == "low" and claim.get("source_gold_label") not in {None, "SUPPORTED"}:
        result.update(
            {
                "text": claim["low_text"],
                "gold_label": claim["source_gold_label"],
                "gold_error_type": claim["source_gold_error_type"],
                "gold_severity": claim["source_gold_severity"],
            }
        )
    return result


def _render_report(title: str, claims: list[dict[str, Any]], tier: str) -> str:
    lines = [
        f"# {title} 论文讲解报告",
        "",
        "本报告围绕论文的研究问题、贡献、方法、实验结果与适用边界进行结构化说明。",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        grouped.setdefault(str(claim["category"]), []).append(claim)
    claim_number = 0
    fake_used = False
    for category in SECTION_TITLES:
        group = grouped.get(category, [])
        if not group:
            continue
        lines.extend(["", f"## {SECTION_TITLES[category]}", ""])
        for claim in group:
            claim_number += 1
            citation = f"（证据：论文第{claim['source_page']}页）"
            if tier == "medium" and claim_number in {4, 8}:
                citation = ""
                claim["citation_mode"] = "missing"
            if (
                tier == "low"
                and claim["gold_label"] != "SUPPORTED"
                and not fake_used
            ):
                citation = "（证据：论文第999页，表99）"
                claim["citation_mode"] = "fabricated"
                fake_used = True
            lines.append(f"- {claim['text']}{citation}")
    lines.extend(
        [
            "",
            "## 阅读结论",
            "",
            "以上内容按论文中的研究问题、方法与实验结论组织，便于读者逐项回到原文核验。",
            "",
        ]
    )
    return "\n".join(lines)


def _protocol() -> str:
    return """# 方向一完整报告三档判别实验协议

## 目标

验证 PaperAudit 能否在完整论文讲解报告上稳定区分高、中、低三档质量。实验复用冻结的
`final_holdout` 六篇论文，不用于继续调整提示词或规则，也不声称是新的独立论文泛化集。

## 数据

- 六篇论文，每篇高、中、低三档，共 18 份完整报告；
- 每份报告结构一致，包含研究问题、贡献、方法、结果和局限边界；
- 高档全部使用受支持论断和有效页码；
- 中档保留两条边界错误，并删除部分证据锚点；
- 低档使用冻结错误样本，并加入一处伪造页码；
- `report_index.jsonl` 保存隐藏档位，盲标模板不包含档位和预期标签。

## 正式运行

每份报告在相同 Hy3、提示词、检索与采样配置下独立运行三次。正式结果生成后不得据此
修改数据、提示词或门槛；若修改，本轮结果降级为开发结果。

## 预注册门槛

- 三档严格排序正确率不低于 5/6；
- 重复运行论断标签两两一致率不低于 90%；
- 每份报告总分标准差的平均值不高于 3 分；
- 平均自动审计覆盖率不低于 80%；
- 注入高风险错误的多数运行检出率不低于 80%。

## 边界

当前协议用重复运行验证自动一致性。`human_annotation_template.csv` 仅是第七步的独立人工
盲标入口；没有第二位真人评审前，不报告人工一致性或 Cohen's kappa。
"""


def build(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_rows = _read_jsonl(SOURCE_SAMPLES)
    papers = json.loads(SOURCE_PAPERS.read_text(encoding="utf-8"))
    papers_by_id = {str(row["paper_id"]): row for row in papers}
    if set(papers_by_id) != set(TIER_REPORT_IDS):
        raise ValueError("报告 ID 计划与 final_holdout 论文集合不一致。")

    index_rows: list[dict[str, Any]] = []
    mutation_rows: list[dict[str, Any]] = []
    blind_rows: list[dict[str, Any]] = []
    length_by_paper: dict[str, dict[str, int]] = {}
    for paper_id, tier_ids in TIER_REPORT_IDS.items():
        paper = papers_by_id[paper_id]
        pdf_path = EVAL_DIR / str(paper["local_pdf"])
        if _sha256(pdf_path) != paper["sha256"]:
            raise ValueError(f"{paper_id} 的 PDF SHA-256 不匹配。")
        base_claims = _base_claims(
            paper_id,
            [row for row in source_rows if str(row["paper_id"]) == paper_id],
        )
        if len(base_claims) != 10:
            raise ValueError(f"{paper_id} 应生成 10 条报告论断。")
        length_by_paper[paper_id] = {}
        for tier, report_id in tier_ids.items():
            claims = [_claim_for_tier(claim, tier) for claim in base_claims]
            report_text = _render_report(str(paper["title"]), claims, tier)
            report_path = reports_dir / f"{report_id}.md"
            report_path.write_text(report_text, encoding="utf-8")
            length_by_paper[paper_id][tier] = len(report_text)
            index_rows.append(
                {
                    "report_id": report_id,
                    "paper_id": paper_id,
                    "tier": tier,
                    "report_path": report_path.relative_to(output_dir).as_posix(),
                    "report_sha256": _sha256(report_path),
                    "character_count": len(report_text),
                    "claim_count": len(claims),
                }
            )
            for claim_index, claim in enumerate(claims, start=1):
                blind_rows.append(
                    {
                        "report_id": report_id,
                        "claim_no": claim_index,
                        "category": claim["category"],
                        "claim_text": claim["text"],
                    }
                )
                if claim["gold_label"] == "SUPPORTED" and claim["citation_mode"] == "valid":
                    continue
                mutation_rows.append(
                    {
                        "report_id": report_id,
                        "paper_id": paper_id,
                        "tier": tier,
                        "claim_no": claim_index,
                        "source_sample_id": claim["source_sample_id"],
                        "category": claim["category"],
                        "claim_text": claim["text"],
                        "gold_label": claim["gold_label"],
                        "gold_error_type": claim["gold_error_type"],
                        "gold_severity": claim["gold_severity"],
                        "citation_mode": claim["citation_mode"],
                        "source_page": claim["source_page"],
                        "gold_evidence_chunk_ids": claim["gold_evidence_chunk_ids"],
                    }
                )

    for paper_id, lengths in length_by_paper.items():
        shortest = min(lengths.values())
        longest = max(lengths.values())
        if longest / shortest > 1.12:
            raise ValueError(f"{paper_id} 三档报告篇幅差异超过 12%：{lengths}")

    index_rows.sort(key=lambda row: str(row["report_id"]))
    blind_rows.sort(key=lambda row: (str(row["report_id"]), int(row["claim_no"])))
    _write_jsonl(output_dir / "report_index.jsonl", index_rows)
    _write_jsonl(output_dir / "mutations.jsonl", mutation_rows)
    _write_jsonl(output_dir / "blind_claims.jsonl", blind_rows)
    with (output_dir / "human_annotation_template.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        fieldnames = [
            "report_id",
            "claim_no",
            "category",
            "claim_text",
            "annotator_id",
            "label",
            "error_type",
            "severity",
            "evidence_page",
            "note",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            row
            | {
                "annotator_id": "",
                "label": "",
                "error_type": "",
                "severity": "",
                "evidence_page": "",
                "note": "",
            }
            for row in blind_rows
        )
    (output_dir / "papers.json").write_text(
        json.dumps(papers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "protocol.md").write_text(_protocol(), encoding="utf-8")

    manifest = {
        "dataset": "direction-one-report-test-v1",
        "status": "prepared-not-run",
        "source_dataset": "../final_holdout_resolved_samples.jsonl",
        "source_papers": "../final_holdout_papers.json",
        "paper_count": len(papers),
        "report_count": len(index_rows),
        "claims_per_report": 10,
        "repeats": 3,
        "thresholds": {
            "ranking_accuracy": 0.8333,
            "label_pairwise_agreement": 0.90,
            "mean_report_score_std": 3.0,
            "mean_audit_coverage": 80.0,
            "high_risk_recall": 0.80,
        },
        "policy": (
            "复用冻结 final_holdout 论文做完整报告扩展；正式结果不得用于调参，"
            "不作为新的独立论文泛化证明。"
        ),
        "files": {
            "report_index": "report_index.jsonl",
            "mutations": "mutations.jsonl",
            "blind_claims": "blind_claims.jsonl",
            "human_annotation_template": "human_annotation_template.csv",
            "papers": "papers.json",
            "protocol": "protocol.md",
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest | {"length_by_paper": length_by_paper}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
