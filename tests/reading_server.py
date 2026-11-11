"""Test-only server: ephemeral library and deterministic model; no network model calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import uvicorn
from paperaudit.api.main import create_app
from paperaudit.config import Settings
from test_api import FakeService


class BrowserService(FakeService):
    attempts: dict[str, int] = {}

    def generate_learning_report(self, paper):
        time.sleep(0.5)
        count = self.attempts.get(paper.title, 0) + 1
        self.attempts[paper.title] = count
        if "Retry" in paper.title and count == 1:
            raise RuntimeError("测试任务失败，请手动重试。")
        if "Regenerate" in paper.title:
            time.sleep(2)
            if count == 2:
                raise RuntimeError("测试详细讲解质量检查失败")
            report = super().generate_learning_report(paper)
            if count >= 3:
                report.one_sentence_summary = "重新生成的详细讲解"
                report.sections[0].points[0].explanation = "详细讲解的新解释，已通过质量检查。"
            return report
        return super().generate_learning_report(paper)

    def audit(self, paper, text, scope, *, mode, progress=None):
        from demo_data import get_demo_audit_run
        time.sleep(.7)
        count = self.attempts.get(text, 0) + 1
        self.attempts[text] = count
        if "FAIL_ONCE" in text and count == 1:
            raise RuntimeError("测试审计失败")
        if progress:
            progress("核对完成", .9)
        return get_demo_audit_run().model_copy(update={"paper_title":paper.title,"report_text":text,"scope":scope,"mode":mode})

    def generate_peer_review(self, paper, *, venue, rubric_weights):
        from test_backend_complete import report
        time.sleep(.6)
        key = "review:" + paper.title
        count = self.attempts.get(key, 0) + 1
        self.attempts[key] = count
        if "Retry" in paper.title and count == 1:
            raise RuntimeError("测试评审失败，请重试。")
        return report().model_copy(update={"paper_title":paper.title,"venue":venue,"rubric_weights":rubric_weights})

    def compare_related_work(self, paper, references):
        from paperaudit.models import RelatedWorkComparison
        time.sleep(.2)
        return RelatedWorkComparison(references=references, assessment="已比较用户提供的相关工作", distinctions=["实验设置不同"], confidence=3)

    def answer(self, paper, codebase, question, **kwargs):
        from paperaudit.models import JointAnswer, CodeCitation
        time.sleep(.2)
        selected=kwargs.get("selected_code")
        file=codebase.files[0]
        return JointAnswer(question=question, answer="已结合论文和代码回答", scope="joint", status="ANSWERED", selected_code=selected,
            code_citations=[CodeCitation(chunk_id="test-code",path=file.path,start_line=1,end_line=2,text=file.content)],
            paper_citations=super().answer_question(paper,question,[]).citations)

    def answer_question(self, paper, question, history, **kwargs):
        time.sleep(0.25)
        if question == "触发失败":
            raise ValueError("模拟模型失败")
        return super().answer_question(paper, question, history, **kwargs)

    def plan_consistency(self, paper, codebase, *, max_checkpoints, progress=None, strategy="one-shot"):
        from paperaudit.models import ConsistencyPlan, ConsistencyCheckpoint, EvidenceAnchor
        from paperaudit.consistency_inputs import input_hashes
        time.sleep(.4)
        chunk = paper.chunks[0]
        return ConsistencyPlan(strategy="test-planner", model="fake", target=max_checkpoints,
            max_requests=160, requests=2, tokens=120, proposed=2, rejected=0, stop_reason="finished",
            **input_hashes(paper, codebase), checkpoints=[ConsistencyCheckpoint(
                checkpoint_id=f"K{i:02d}", topic=topic, category="training", question=f"{topic}是否一致？",
                paper_anchor=EvidenceAnchor(chunk_id=chunk.chunk_id, page=chunk.page, text=chunk.content,
                                            quote=chunk.content))
                for i, topic in enumerate(["训练配置", "评估设置"], 1)])

    def check_consistency(self, paper, codebase, checkpoints, plan, *, progress=None):
        from paperaudit.models import ConsistencyReport, ConsistencyItem, ConsistencySummary, PaperCodeFinding, FindingVerification
        from paperaudit.agents.consistency import summarize
        time.sleep(.4)
        if progress:
            progress("正在核对所选要点", .6)
        items = []
        for c in checkpoints:
            answer = self.answer(paper, codebase, c.question)
            pending = c.checkpoint_id == "K01"
            finding = PaperCodeFinding(text="默认 warmup 配置一致。", verdict="CONSISTENT",
                paper_citations=answer.paper_citations, code_citations=answer.code_citations,
                verification=FindingVerification(status="failed" if pending else "passed", required=True,
                    reason="论文为 40，代码为 20，不支持一致判定。" if pending else "证据支持该判定。",
                    paper_statement="40 epochs", code_statement="20 epochs" if pending else "40 epochs"))
            items.append(ConsistencyItem(checkpoint=c, status="checked",
                answer=answer.model_copy(update={"findings": [finding]})))
        return ConsistencyReport(model="fake", paper_title=paper.title, codebase_name=codebase.name,
            plan_id=plan.plan_id, items=items, summary=summarize(items),
            planned=plan.proposed, plan_rejected=0,
            plan_unselected=len(plan.checkpoints) - sum(c.source == "planner" for c in checkpoints),
            max_checkpoints=len(checkpoints), max_requests=160, concurrency=4, plan_requests=2,
            requests=2 + 2 * len(checkpoints))


if __name__ == "__main__":
    with TemporaryDirectory(prefix="paperaudit-reading-e2e-") as directory:
        root = Path(directory)
        runner = BrowserService()
        app = create_app(storage_root=root / "library", settings_dir=root / "settings",
                         settings=Settings(api_base="https://example.invalid/v1", api_key="fake-only", model="fake"),
                         service_factory=lambda _: runner, code_service_factory=lambda _: runner)
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
