"""Small synthetic development check; does not use or overwrite frozen holdouts.

Run explicitly: python -m eval.check_core_audit_dev
Uses the configured API for three complete audits of one development report.
"""
from __future__ import annotations

from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from paperaudit.config import Settings
from paperaudit.models import ClaimCategory, PaperChunk, ParsedPaper
from paperaudit.service import AuditService


REPORT = """# 开发报告
学习优化器在 Dataset A 上将准确率提升了 5 个百分点。
学习优化器在所有任务上提升 50% 的性能。
学习优化器在所有任务上将准确率提升了 5 个百分点。
架构搜索方法在三个图像分类数据集上找到了性能更好的架构。
架构搜索方法已证明能自动发现适用于所有领域的最优架构。
算法在目标函数为凸且 L-光滑、最小值存在、使用规定步长时，保证收敛到全局最优解。
学习优化器在 Dataset A 上将准确率提升了 50 个百分点。
该方法可用于回归、优化和图像补全。
"""

PAPER = ParsedPaper(
    title="Synthetic core audit development fixture",
    page_count=1,
    chunks=[PaperChunk(chunk_id=f"p1_b{i}", page=1, content=text) for i, text in enumerate([
        "The learned optimizer was evaluated only on Dataset A. It improved accuracy "
        "from 80% to 85%, an absolute gain of 5 percentage points. Results for the "
        "learned optimizer on other tasks have not been established.",
        "Our architecture search method found better-performing architectures on three "
        "image classification datasets. We report the observed validation accuracy of "
        "the selected architectures on these datasets.",
        "Theorem 1 (global convergence). For a convex L-smooth objective with a minimizer, "
        "the algorithm with the prescribed step size converges to a global optimum.",
        "The method can be used for regression, optimization, and image completion.",
    ], 1)],
)

EXPECTED = {
    "S0002": ({"SUPPORTED"}, "none"),
    "S0003": ({"NO_SUPPORT_FOUND", "CONTRADICTED"}, "high"),
    "S0004": ({"PARTIALLY_SUPPORTED"}, "medium"),
    "S0005": ({"SUPPORTED"}, "none"),
    "S0006": ({"NO_SUPPORT_FOUND", "CONTRADICTED"}, "high"),
    "S0007": ({"SUPPORTED"}, "none"),
    "S0008": ({"CONTRADICTED"}, "high"),
    "S0009": ({"SUPPORTED"}, "none"),
}


def main() -> None:
    settings = Settings.from_env()
    def audit_once(repeat):
        print(f"Development audit {repeat + 1}/3 started", flush=True)
        run = AuditService(settings).audit(
            PAPER, REPORT, list(ClaimCategory),
            progress=lambda stage, _: print(f"Run {repeat + 1}: {stage}", flush=True),
        )
        print(f"Development audit {repeat + 1}/3: {len(run.audits)} claims", flush=True)
        return run.model_dump(mode="json")

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(audit_once, range(3)))
    failures = []
    signatures = []
    for repeat, row in enumerate(rows, 1):
        by_source = {}
        for audit in row["audits"]:
            by_source.setdefault(audit["claim"]["source_id"], []).append(audit)
        signatures.append({source: sorted(a["judgment"]["label"] for a in audits)
                           for source, audits in by_source.items()})
        if set(by_source) != set(EXPECTED):
            failures.append(f"run {repeat}: source coverage mismatch")
        for source, (labels, severity) in EXPECTED.items():
            audits = by_source.get(source, [])
            if len(audits) != 1 or any(
                a["judgment"]["label"] not in labels or a["judgment"]["severity"] != severity
                for a in audits
            ):
                failures.append(f"run {repeat}: unexpected split or judgment for {source}")
    agreement = sum(left.get(s) == right.get(s) for left, right in combinations(signatures, 2)
                    for s in EXPECTED) / (3 * len(EXPECTED))
    result = {
        "fixture": "synthetic-core-audit-dev-v1",
        "model": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "claim_extraction_version": "sentence-sources-v1",
        "run_count": 3,
        "source_label_agreement": agreement,
        "passed": not failures,
        "failures": failures,
        "runs": rows,
        "limitation": "Synthetic development cases only; not an independent holdout quality estimate.",
    }
    output = Path(__file__).with_name("core_audit_dev_check.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}, ensure_ascii=True), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
