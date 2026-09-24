"""Read-only diagnosis of frozen report audits. Never creates a model client.

Reference evidence overlap is an observable proxy, not proof of retrieval failure
or judgment error. Full facts retain the original worst-label aggregation rule.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from paperaudit import claim_extraction

LABEL_RANK = {"SUPPORTED": 0, "PARTIALLY_SUPPORTED": 1, "NO_SUPPORT_FOUND": 2, "CONTRADICTED": 3}
OUTCOMES = {
    "agree": "与参考一致",
    "audit_failed": "整份审计失败",
    "alignment_failed": "对齐结果缺失",
    "extraction_missing": "抽取缺失",
    "extraction_partial": "抽取覆盖不完整",
    "alignment_uncertain": "语义对齐不确定",
    "abstain": "完整覆盖后弃权",
    "label_disagreement": "已判定但与参考不一致",
    "reference_unresolved": "参考未决（不计一致率）",
}


def quote_matches(quote: str, source: str) -> bool:
    """Same normalization as frozen reference validation, without API imports."""
    marked = re.sub(r"(?<=[A-Za-z])-\s*\n\s*(?=[A-Za-z])", "\ue000", source)
    canonical = re.sub(r"\s+", "", unicodedata.normalize("NFKC", marked))
    q = re.sub(r"\s+", "", unicodedata.normalize("NFKC", quote))
    if not q:
        return False
    pattern = "\ue000?".join("[-\ue000]" if char == "-" else re.escape(char) for char in q)
    return re.search(pattern, canonical) is not None


class Inputs:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.hashes: dict[str, str] = {}
        self.cache: dict[str, object] = {}

    def path(self, name: str) -> Path:
        path = (self.root / name.replace("\\", "/")).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Input escapes experiment directory: {name}")
        return path

    def read(self, name: str):
        path = self.path(name)
        key = path.relative_to(self.root).as_posix()
        if key not in self.cache:
            data = path.read_bytes()
            self.hashes[key] = hashlib.sha256(data).hexdigest()
            self.cache[key] = json.loads(data)
        return self.cache[key]

    def verify_frozen_inputs(self) -> dict:
        """Verify consumed inputs, without reading unrelated request payloads."""
        expected = {}
        for name in ("reference_freeze.json", "alignment_freeze.json"):
            for key, digest in self.read(name)["sha256"].items():
                expected[key.replace("\\", "/")] = digest
        expected.update({k.replace("\\", "/"): v for k, v in self.read("protocol.json")["input_sha256"].items()})
        checked = 0
        for name, digest in self.hashes.items():
            if name in expected:
                if digest != expected[name]:
                    raise ValueError(f"Frozen input hash mismatch: {name}")
                checked += 1
        return {"matched_consumed_files": checked, "consumed_files": len(self.hashes),
                "note": "Only consumed frozen inputs are checked; run JSONs are fingerprinted, not certified by these freezes."}


def unique_index(items: list[dict], key: str) -> dict:
    result = {item[key]: item for item in items}
    if len(result) != len(items):
        raise ValueError(f"Duplicate {key}")
    return result


def aggregate_prediction(match: dict, audits: dict) -> tuple[str | None, list[dict]]:
    ids = match.get("claim_ids", [])
    if len(ids) != len(set(ids)) or any(cid not in audits for cid in ids):
        raise ValueError("Alignment contains duplicate or unknown claim IDs")
    selected = [audits[cid] for cid in ids]
    if match.get("coverage") != "full" or not selected:
        return None, selected
    labels = [a["judgment"]["label"] for a in selected]
    if any(label not in {*LABEL_RANK, "ABSTAIN"} for label in labels):
        raise ValueError("Unknown judgment label")
    if "ABSTAIN" in labels:
        return None, selected
    return max(labels, key=LABEL_RANK.__getitem__), selected


def outcome(run_ok: bool, resolved: bool, coverage: str, predicted: str | None, reference: str | None) -> str:
    if not resolved:
        return "reference_unresolved"
    if not run_ok:
        return "audit_failed"
    if coverage in {"missing", "partial"}:
        return "extraction_" + coverage
    if coverage == "uncertain":
        return "alignment_uncertain"
    if coverage != "full":
        return "alignment_failed"
    if predicted is None:
        return "abstain"
    return "agree" if predicted == reference else "label_disagreement"


def evidence_overlap(reference: dict, selected: list[dict], chunks: dict) -> dict:
    evidence = reference.get("evidence", [])
    candidates = [c for audit in selected for c in audit["candidates"]]
    validated, hits, invalid = [], [], []
    for item in evidence:
        chunk = chunks.get(item["chunk_id"])
        if chunk is None or not quote_matches(item["quote"], chunk["content"]):
            invalid.append(item["chunk_id"])
            continue
        validated.append(item)
        # Match actual candidate text as well as ID: a matching ID alone does not
        # establish that the model received the referenced passage.
        if any(c["chunk_id"] == item["chunk_id"] and quote_matches(item["quote"], c["text"]) for c in candidates):
            hits.append(item)
    if invalid:
        status = "invalid_reference_quote"
    elif not validated:
        status = "no_reference_evidence"
    elif not hits:
        status = "none"
    elif len(hits) == len(validated):
        status = "all"
    else:
        status = "some"
    return {"status": status, "reference_quotes": len(evidence), "validated_quotes": len(validated),
            "matched_quotes": len(hits), "invalid_chunk_ids": invalid,
            "reference_chunk_ids": sorted({e["chunk_id"] for e in evidence}),
            "matched_chunk_ids": sorted({e["chunk_id"] for e in hits})}


def review_responses(run: dict) -> dict:
    reviews = defaultdict(list)
    for index, raw in enumerate(run.get("raw_outputs", []), 1):
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict) or "evidence_sufficient" not in data or not isinstance(data.get("judgment"), dict):
            continue
        judgment = data["judgment"]
        reviews[judgment.get("claim_id")].append({
            "raw_output_index": index, "evidence_sufficient": data["evidence_sufficient"],
            "label": judgment.get("label"), "evidence_ids": judgment.get("evidence_ids", []),
            "explanation": judgment.get("explanation", ""),
        })
    return reviews


def extraction_quote_issues(run: dict, sources: dict[str, str]) -> list[dict]:
    """Check literal provenance against full sentences, not fact subspans.

    The caller verifies the local splitter matches the frozen source hash.
    This checks an observable invariant, not the entire extraction validator.
    """
    issues = []
    for index, raw in enumerate(run.get("raw_outputs", []), 1):
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            continue
        for item in data["sources"]:
            original = sources.get(item["source_id"])
            for claim in item.get("claims", []):
                quote = claim.get("source_quote", "")
                if original is not None and quote and quote not in original:
                    issues.append({"raw_output_index": index, "source_id": item["source_id"],
                                   "claim_id": claim.get("claim_id"), "returned_quote": quote,
                                   "original_source": original})
    return issues


def summarize_rows(rows: list[dict]) -> dict:
    resolved = [row for row in rows if row["reference_status"] == "resolved"]
    counts = Counter(row["outcome"] for row in resolved)
    full_errors = [row for row in resolved if row["outcome"] in {"abstain", "label_disagreement"}]
    claim_keys = {(r["report_id"], r["repeat"], cid) for r in full_errors for cid in r["claim_ids"]}
    decided = sum(r["prediction_label"] is not None for r in resolved)
    return {
        "fact_observations": len(rows), "resolved_reference_observations": len(resolved),
        "excluded_reference_observations": len(rows) - len(resolved),
        "outcomes": dict(counts), "end_to_end_label_accuracy": counts["agree"] / len(resolved) if resolved else None,
        "decided_label_accuracy": counts["agree"] / decided if decided else None,
        "full_coverage_error_observations": len(full_errors), "full_coverage_error_claims": len(claim_keys),
        "evidence_overlap_by_outcome": {
            name: dict(Counter(r["evidence_overlap"]["status"] for r in full_errors if r["outcome"] == name))
            for name in ("abstain", "label_disagreement")
        },
        "review_missing_ids_observations": sum(bool(r["review_missing_ids_claims"]) for r in full_errors),
        "review_missing_ids_claims": len({(r["report_id"], r["repeat"], cid) for r in full_errors for cid in r["review_missing_ids_claims"]}),
        "mixed_reference_claim_observations": sum(bool(r["mixed_reference_claim_ids"]) for r in full_errors),
        "mixed_reference_claims": len({(r["report_id"], r["repeat"], cid) for r in full_errors for cid in r["mixed_reference_claim_ids"]}),
    }


def diagnose(root: Path) -> tuple[dict, list[dict], dict]:
    source = Inputs(root)
    protocol = source.read("protocol.json")
    splitter_path = Path(claim_extraction.__file__)
    splitter_hash = hashlib.sha256(splitter_path.read_bytes()).hexdigest()
    source_hashes = {k.replace("\\", "/"): v for k, v in protocol["source_sha256"].items()}
    if source_hashes.get("src/paperaudit/claim_extraction.py") != splitter_hash:
        raise ValueError("Local report splitter differs from the frozen experiment; replay needs its original version")
    frozen = source.read("analysis/summary.json")
    refdir = source.read("reference_selection.json")["directory"]
    rows, failures = [], []
    for report in protocol["reports"]:
        rid, pid = report["report_id"], report["paper_id"]
        blind = source.read(f"inputs/blind_{rid}.json")
        facts = unique_index(blind["facts"], "fact_id")
        refs = unique_index([r for r in source.read(f"{refdir}/{pid}/labels.json") if r["report_id"] == rid], "fact_id")
        if set(refs) != set(facts):
            raise ValueError(f"Reference fact IDs differ from input: {rid}")
        chunks = unique_index(source.read(f"inputs/{pid}_paper.json")["chunks"], "chunk_id")
        for repeat in range(1, report["repeats"] + 1):
            run_path = f"run_{repeat}/{rid}.json"
            run = source.read(run_path)
            good = run["status"] == "ok"
            audits = {
                a["claim"]["claim_id"]: a for a in run.get("audit", {}).get("audits", [])
            }
            if len(audits) != len(run.get("audit", {}).get("audits", [])):
                raise ValueError(f"Duplicate extracted claim ID: {run_path}")
            alignment, alignment_path = {}, None
            if good:
                for attempt in (1, 2):
                    candidate = f"alignment/{rid}_{repeat}_attempt{attempt}.json"
                    if source.path(candidate).exists():
                        data = source.read(candidate)
                        if data["status"] == "ok":
                            alignment = unique_index(data["value"]["matches"], "fact_id")
                            alignment_path = candidate
                            if set(alignment) != set(facts):
                                raise ValueError(f"Alignment fact IDs differ from input: {candidate}")
                            break
            else:
                failures.append({"report_id": rid, "repeat": repeat, "kind": report["kind"],
                                 "error_type": run.get("error_type"), "run_path": run_path,
                                 "extraction_quote_issues": extraction_quote_issues(
                                     run, {s.source_id: s.text for s in claim_extraction.split_report_sources(blind["report_text"])})})
            shared = defaultdict(list)
            for fid, match in alignment.items():
                if match["coverage"] == "full" and refs[fid]["status"] == "resolved":
                    for cid in match["claim_ids"]:
                        shared[cid].append({"fact_id": fid, "label": refs[fid]["reference"]["label"]})
            reviews = review_responses(run)
            skipped = {s["source_id"]: s for s in run.get("audit", {}).get("skipped_sources", [])}
            for fid, fact in facts.items():
                match = alignment.get(fid, {})
                predicted, selected = aggregate_prediction(match, audits)
                coverage = match.get("coverage", "alignment_failed" if good else "audit_failed")
                if coverage not in {"full", "partial", "missing", "uncertain", "alignment_failed", "audit_failed"}:
                    raise ValueError("Unknown semantic coverage")
                if coverage == "full" and not selected:
                    raise ValueError("Full coverage requires at least one claim")
                ref = refs[fid]
                reference = ref.get("reference") or {}
                category = outcome(good, ref["status"] == "resolved", coverage, predicted, reference.get("label"))
                # Last recorded supplemental review only. Earlier repaired errors
                # must not be counted again as independent blocked claims.
                missing_ids = [a["claim"]["claim_id"] for a in selected
                    if a["judgment"]["label"] == "ABSTAIN"
                    and reviews.get(a["claim"]["claim_id"])
                    and reviews[a["claim"]["claim_id"]][-1]["evidence_sufficient"] is True
                    and reviews[a["claim"]["claim_id"]][-1]["label"] != "ABSTAIN"
                    and not reviews[a["claim"]["claim_id"]][-1]["evidence_ids"]]
                rows.append({
                    "report_id": rid, "paper_id": pid, "kind": report["kind"], "repeat": repeat,
                    "fact_id": fid, "fact_text": fact["text"], "source_id": fact.get("source_id"),
                    "source_quote": fact.get("source_quote"), "reference_status": ref["status"],
                    "reference_label": reference.get("label"), "reference_explanation": reference.get("explanation"),
                    "reference_evidence": reference.get("evidence", []),
                    "coverage": coverage, "alignment_reason": match.get("reason"),
                    "prediction_label": predicted, "outcome": category,
                    "claim_ids": match.get("claim_ids", []),
                    "claims": [{"claim": a["claim"], "judgment": a["judgment"],
                                "candidate_chunk_ids": [c["chunk_id"] for c in a["candidates"]],
                                "last_review": (reviews.get(a["claim"]["claim_id"]) or [None])[-1]}
                               for a in selected],
                    "evidence_overlap": evidence_overlap(reference, selected, chunks),
                    "review_missing_ids_claims": missing_ids,
                    "shared_claim_references": {cid: shared[cid] for cid in match.get("claim_ids", [])},
                    "mixed_reference_claim_ids": [cid for cid in match.get("claim_ids", []) if len({s["label"] for s in shared[cid]}) > 1],
                    "skipped_source": skipped.get(fact.get("source_id")),
                    "run_path": run_path, "alignment_path": alignment_path,
                })
    groups = {kind: summarize_rows([row for row in rows if row["kind"] == kind]) for kind in sorted({r["kind"] for r in rows})}
    # Fail closed when this diagnostic cannot reproduce the published denominator.
    checks = {}
    for kind, group in groups.items():
        expected = frozen["groups"][kind]
        checks[kind] = all(group[key] == expected[key] for key in (
            "fact_observations", "resolved_reference_observations", "end_to_end_label_accuracy", "decided_label_accuracy"))
    if not all(checks.values()):
        raise ValueError(f"Frozen summary reconciliation failed: {checks}")
    integrity = source.verify_frozen_inputs()
    summary = {"schema_version": 1, "experiment": root.name,
               "protocol_model": protocol.get("model"), "groups": groups,
               "splitter_sha256": splitter_hash,
               "by_report": {rid: summarize_rows([r for r in rows if r["report_id"] == rid]) for rid in sorted({r["report_id"] for r in rows})},
               "failures": failures, "frozen_summary_reconciled": checks, "integrity": integrity,
               "limitations": ["同模型参考与语义对齐，不是独立人工准确率。", "参考证据未命中不能证明不存在替代证据；全部命中也不证明复合论断的全部条件均可判断。", "每份自然报告仅运行一次；同一claim对应多个fact，事实观测不独立。", "整次失败保留分母；未决参考单列。候选为运行中保存的最终候选，可能包含补查证据。"]}
    return summary, rows, source.hashes


def percentage(n: int, d: int) -> str:
    return f"{n / d:.2%}" if d else "N/A"


def write_report(summary: dict, rows: list[dict]) -> str:
    group = summary["groups"]["natural"]
    total = group["resolved_reference_observations"]
    counts = group["outcomes"]
    errors = total - counts.get("agree", 0)
    lines = ["# 自然报告离线诊断", "", f"实验：`{summary['experiment']}`；协议模型：`{summary['protocol_model']}`。未调用模型 API；原始运行、参考和对齐数据保持不变。", "",
             f"自然组 {group['fact_observations']} 条事实，其中 {total} 条参考已决、{group['excluded_reference_observations']} 条参考未决。端到端标签一致率为 {counts['agree']}/{total} = {group['end_to_end_label_accuracy']:.2%}。",
             "", "## 端到端损失分解", "", "| 结果 | 事实数 | 占已决参考 | 占未得到一致结果 |", "| --- | ---: | ---: | ---: |"]
    for name in OUTCOMES:
        if name in counts:
            n = counts[name]
            lines.append(f"| {OUTCOMES[name]} | {n} | {percentage(n,total)} | {'—' if name == 'agree' else percentage(n,errors)} |")
    lines += ["", "整次审计失败独立列出，不能把它的所有事实归为漏抽取或漏检索。missing/partial 是冻结语义对齐的结论，可能受事实粒度和对齐标准影响。", "", "## 已完整覆盖事实的证据情况", "",
              f"{group['full_coverage_error_observations']} 条弃权或标签分歧事实对应 {group['full_coverage_error_claims']} 个不同的系统 claim。", "",
              "| 最终结果 | 参考引文全部在候选中 | 部分在候选中 | 全部不在候选中 | 无参考引文 | 参考引文校验失败 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, values in group["evidence_overlap_by_outcome"].items():
        lines.append("| " + " | ".join([OUTCOMES[name], *[str(values.get(k, 0)) for k in ("all", "some", "none", "no_reference_evidence", "invalid_reference_quote")]]) + " |")
    lines += ["", "这里只比较参考引文与已保存候选的 chunk ID 和实际文本；**未命中是检索排查线索，命中后的分歧仍需核对复合论断、参考标签和判断口径**。不能直接称为已确认的三类因果错误率。", "",
              f"补查回答称证据充分、给出非弃权标签却漏填 evidence_ids：{group['review_missing_ids_claims']} 个不同 claim，关联 {group['review_missing_ids_observations']} 条未一致事实（与上表重叠）。",
              f"同一系统 claim 对应多个不同参考标签：关联 {group['mixed_reference_claim_observations']} 条未一致事实、{group['mixed_reference_claims']} 个 claim。复合判断回填到细粒度事实可能产生连带弃权/分歧。", "",
              "## 按自然报告拆分", "", "| 报告 | 参考分母 | 一致 | 整次失败 | 缺失/部分覆盖 | 弃权 | 已判定分歧 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for rid, s in summary["by_report"].items():
        if not rid.endswith("_natural"):
            continue
        c = s["outcomes"]
        lines.append(f"| {rid} | {s['resolved_reference_observations']} | {c.get('agree',0)} | {c.get('audit_failed',0)} | {c.get('extraction_missing',0)+c.get('extraction_partial',0)} | {c.get('abstain',0)} | {c.get('label_disagreement',0)} |")
    natural = [r for r in rows if r["kind"] == "natural" and r["outcome"] not in {"agree", "reference_unresolved"}]
    selectors = [
        ("整份失败", lambda r: r["outcome"] == "audit_failed"),
        ("原文被跳过", lambda r: r["outcome"] == "extraction_missing" and r["skipped_source"]),
        ("覆盖不完整", lambda r: r["outcome"] == "extraction_partial"),
        ("参考引文未进入候选", lambda r: r["outcome"] == "abstain" and r["evidence_overlap"]["status"] == "none"),
        ("补查结构缺字段", lambda r: r["review_missing_ids_claims"]),
        ("同一claim映射不同参考标签", lambda r: r["mixed_reference_claim_ids"]),
        ("参考引文齐全仍有标签分歧", lambda r: r["outcome"] == "label_disagreement" and r["evidence_overlap"]["status"] == "all"),
    ]
    lines += ["", "## 自动案例索引", "", "每个排查维度取协议顺序中的首例，展示机制，不代表随机抽样。更多证据见 facts.jsonl；人工核对后的建议见 review.md。"]
    for title, predicate in selectors:
        case = next((r for r in natural if predicate(r)), None)
        if not case:
            continue
        lines += ["", f"### {title}：{case['report_id']} / F{case['fact_id'].removeprefix('F')} / 第 {case['repeat']} 次", "",
                  case["fact_text"], "", f"参考：{case['reference_label']}；系统：{case['prediction_label'] or OUTCOMES[case['outcome']]}；claim：{', '.join(case['claim_ids']) or '无'}。",
                  "", f"对齐说明：{case['alignment_reason'] or '无完整审计/对齐结果'}", "", f"参考说明：{case['reference_explanation']}", "", f"原始运行：`{case['run_path']}`"]
        for claim in case["claims"]:
            lines += ["", f"系统解释（{claim['claim']['claim_id']}）：{claim['judgment']['explanation']}"]
    lines += ["", "## 口径与可复现性", "", *[f"- {note}" for note in summary["limitations"]],
              f"- 三组冻结统计均已复算对齐；读取的冻结输入有 {summary['integrity']['matched_consumed_files']} 份通过原始字节散列校验。", "- 输入路径与散列见 inputs.json；不会修改历史快照或进行新检索。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, dest = args.experiment.resolve(), args.output_dir.resolve()
    if dest.is_relative_to(root) or root.is_relative_to(dest):
        parser.error("Output must be separate from the frozen experiment tree")
    if dest.exists() and any(dest.iterdir()):
        parser.error("Output directory must be new or empty; do not overwrite a diagnosis")
    summary, rows, hashes = diagnose(root)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "facts.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (dest / "inputs.json").write_text(json.dumps({"files": hashes, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + "\n", encoding="utf-8")
    (dest / "report.md").write_text(write_report(summary, rows), encoding="utf-8")
    print(json.dumps({"output": str(dest), "natural": summary["groups"]["natural"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
