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
                         service_factory=lambda _: runner)
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
