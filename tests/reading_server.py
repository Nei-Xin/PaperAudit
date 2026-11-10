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
        from paperaudit.ui.demo_data import get_demo_audit_run
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


if __name__ == "__main__":
    with TemporaryDirectory(prefix="paperaudit-reading-e2e-") as directory:
        root = Path(directory)
        runner = BrowserService()
        app = create_app(storage_root=root / "library", settings_dir=root / "settings",
                         settings=Settings(api_base="https://example.invalid/v1", api_key="fake-only", model="fake"),
                         service_factory=lambda _: runner, code_service_factory=lambda _: runner)
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
