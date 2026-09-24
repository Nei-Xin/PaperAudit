"""Project state shared by sidebar navigation, uploads and workspace views.

Model configuration and rubric preferences belong to the session. Reports,
conversations, evidence selections and review edits belong to one project.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from paperaudit.display import recover_paper_title
from paperaudit.models import LearningReport, ParsedCodebase, ParsedPaper
from paperaudit.storage import ProjectStore


PROJECT_SESSION_KEYS = (
    "peer_review", "parsed_codebase", "result_mode", "active_audit_id", "launch_audit_job_id",
    "paper_qa_history", "paper_qa_pending", "paper_text_selection",
    "project_conversations", "active_conversation_id", "code_parse_warning",
    "active_project_id", "project_original_filename", "project_save_error",
    "project_restore_error", "paper_pdf_upload", "source_code_upload",
    "report_file_upload", "report_source_mode", "launch_mode",
)
# Dynamic widget keys include issue indices, paper titles, and audit IDs.
PROJECT_SESSION_PREFIXES = (
    "learning_", "learning-", "qa_", "qa-", "joint_", "joint-", "audit_",
    "workspace_audit_", "peer_review_", "peer-review-", "peer-major-",
    "peer-minor-", "peer-revision-", "upload_pdf_", "upload_report_",
)
SESSION_PREFERENCE_KEYS = {"peer_review_venue", "peer_review_rubric_weights"}
UPLOAD_WIDGET_KEYS = {
    "paper_pdf_upload", "source_code_upload", "report_file_upload",
    "report_source_mode", "launch_mode", "audit_scope_mode",
    "peer-review-privacy-ack",
}


class ProjectSession:
    """Load a target completely before replacing the active project state."""

    def __init__(
        self, state: MutableMapping[str, Any], query_params: MutableMapping[str, Any],
    ):
        self.state = state
        self.query_params = query_params

    def clear(self, *, keep_upload: bool = False) -> None:
        for key in list(self.state):
            if key in SESSION_PREFERENCE_KEYS or key.startswith("peer-review-weight-"):
                continue
            # Streamlit form widgets have already rendered when a submission is
            # processed. Keep their values until the next navigation/rerun.
            if keep_upload and (
                key in UPLOAD_WIDGET_KEYS or key.startswith(("upload_pdf_", "upload_report_"))
            ):
                continue
            if key in PROJECT_SESSION_KEYS or key.startswith(PROJECT_SESSION_PREFIXES):
                del self.state[key]
        self.query_params.pop("project", None)

    def save_conversations(self, store: ProjectStore, project_id: str) -> None:
        conversations = self.state.get("project_conversations")
        if isinstance(conversations, list) and conversations:
            store.save_conversations(
                project_id, conversations,
                str(self.state.get("active_conversation_id", "")),
            )
            return
        store.save_histories(
            project_id,
            self.state.get("paper_qa_history", []),
            self.state.get("joint_qa_history", []),
        )

    def restore(self, store: ProjectStore, project_id: str, *, keep_upload: bool = False) -> None:
        saved = store.load_learning_project(project_id)
        restored_title = recover_paper_title(saved.paper)
        if restored_title != saved.metadata.title:
            store.update_project_title(saved.metadata.project_id, restored_title)
        paper = saved.paper.model_copy(update={"title": restored_title})
        report = saved.report.model_copy(update={"paper_title": restored_title}) if saved.report else None
        review = store.load_peer_review(project_id)
        restored = {
            "learning_report": report,
            "peer_review": review.model_copy(update={"paper_title": restored_title}) if review else None,
            "learning_pdf_bytes": saved.pdf_bytes,
            "learning_paper": paper,
            "parsed_codebase": saved.codebase,
            "paper_qa_history": saved.paper_history,
            "joint_qa_history": saved.joint_history,
            "project_conversations": saved.conversations,
            "active_conversation_id": saved.active_conversation_id,
            "project_original_filename": saved.metadata.original_filename,
            "active_project_id": saved.metadata.project_id,
        }
        if report is not None:
            restored["result_mode"] = "learning"
        elif review is not None:
            restored["result_mode"] = "peer_review"
        else:
            records = store.list_audit_runs(saved.metadata.project_id)
            if records:
                metadata, run = store.load_audit_run(saved.metadata.project_id, records[0].audit_id)
                restored.update({
                    "audit_run": run.model_copy(update={"paper_title": restored_title}),
                    "active_audit_id": metadata.audit_id,
                    "audit_record_metadata": metadata,
                })
            restored["result_mode"] = "audit_project"
        self.clear(keep_upload=keep_upload)
        self.state.update(restored)
        self.query_params["project"] = saved.metadata.project_id

    def open(self, store: ProjectStore, project_id: str) -> None:
        current_id = self.state.get("active_project_id")
        if current_id:
            self.save_conversations(store, str(current_id))
        self.restore(store, project_id)

    def initialize_learning(
        self, paper: ParsedPaper, pdf_bytes: bytes, report: LearningReport,
        codebase: ParsedCodebase | None, code_warning: str | None, filename: str,
    ) -> None:
        self.clear(keep_upload=True)
        self.state.update({
            "learning_report": report, "learning_pdf_bytes": pdf_bytes,
            "learning_paper": paper, "parsed_codebase": codebase,
            "result_mode": "learning", "paper_qa_history": [],
            "joint_qa_history": [], "project_original_filename": filename,
        })
        if code_warning:
            self.state["code_parse_warning"] = code_warning
