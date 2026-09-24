"""Run the real entry point with isolated storage and no model API calls."""
from pathlib import Path

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

from paperaudit.config import Settings
from paperaudit.models import PaperChunk, ParsedPaper
from paperaudit.storage import ProjectStore, save_storage_settings

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPERAUDIT_SETTINGS_DIR", str(tmp_path / "settings"))
    monkeypatch.setattr(Settings, "from_env", lambda: Settings("", "", "offline"))
    return tmp_path


def test_setup_and_empty_upload_modes(workspace):
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert any(item.label == "保存并进入项目" for item in app.button)
    save_storage_settings(workspace / "library", workspace / "settings")
    app.run()
    assert not app.exception
    for mode in ("模拟投稿评审", "审计已有报告", "生成论文讲解"):
        app.session_state["launch_mode"] = mode
        app.run()
        assert not app.exception
    assert app.session_state["launch_mode"] == "生成论文讲解"


def test_sidebar_and_url_switch_clear_project_state(workspace, monkeypatch):
    from paperaudit.ui import pdf_selector

    # AppTest does not mount browser-side v2 components. Exercise the real PDF
    # preparation and toolbar, replacing only the browser selection component.
    monkeypatch.setattr(pdf_selector, "_pdf_selector", lambda **kwargs: {})
    settings = save_storage_settings(workspace / "library", workspace / "settings")
    store = ProjectStore(settings.storage_root)
    projects = []
    for title in ("First Paper", "Second Paper"):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), title)
            pdf = document.tobytes()
        paper = ParsedPaper(title=title, page_count=1, chunks=[
            PaperChunk(chunk_id="p1_b1", page=1, content=title),
        ])
        projects.append(store.save_paper_project(pdf, title + ".pdf", paper))
    app = AppTest.from_file(str(APP)).run()
    app.button(key=f"sidebar-open-{projects[0].project_id}").click().run()
    assert not app.exception
    app.session_state["peer_review_revision_pdf"] = b"stale-preview"
    app.session_state["peer-major-0-manual-note"] = "stale-note"
    app.query_params["project"] = projects[1].project_id
    app.run()
    assert not app.exception
    assert app.session_state["active_project_id"] == projects[1].project_id
    assert "peer_review_revision_pdf" not in app.session_state
    assert "peer-major-0-manual-note" not in app.session_state
    app.button(key="sidebar-new-project").click().run()
    assert not app.exception
    assert "active_project_id" not in app.session_state
    assert "project" not in app.query_params
