"""Session state lifecycle shared by the Streamlit project views.

The application keeps transient UI state in ``st.session_state`` while the
project store remains the source of truth.  Keeping the key list and project
switch operations here prevents a newly added view from accidentally leaking
state into another project.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from paperaudit.display import recover_paper_title


PROJECT_SESSION_KEYS: tuple[str, ...] = (
    "learning_report", "peer_review", "learning_pdf_bytes", "learning_paper",
    "parsed_codebase", "audit_run", "active_audit_id", "audit_record_metadata",
    "audit_origin", "audit_save_error", "audit_submit_notice", "launch_audit_job_id",
    "learning_job_id", "peer_review_job_id", "peer_review_revision_pdf",
    "peer_review_revision_pdf_name", "peer_review_revision_page", "peer_review_pdf_focus",
    "result_mode", "learning_selected_evidence", "learning_evidence_group",
    "learning_evidence_section", "learning_active_section", "learning_active_point",
    "learning_pdf_page", "learning_pdf_zoom", "learning_pdf_anchor_sync",
    "learning_focus_evidence", "qa_selected_evidence", "qa_evidence_group",
    "qa_pdf_page", "qa_pdf_zoom", "qa_pdf_anchor_sync", "qa_focus_evidence",
    "paper_qa_history", "paper_qa_pending", "paper_text_selection",
    "learning_workspace_mode", "learning_switch_to_qa", "learning_pdf_focus",
    "joint_qa_history", "project_conversations", "active_conversation_id",
    "joint_qa_pending", "joint_paper_selection", "joint_active_paper_citation",
    "joint_active_code_citation", "joint_code_selection", "joint_code_path",
    "joint_code_path_pending", "joint_code_rendered_path", "joint_pdf_page",
    "joint_paper_sync", "joint_layout_mode", "joint_layout_mode_pending",
    "code_parse_warning", "active_project_id", "project_original_filename",
    "project_save_error", "paper_pdf_upload", "source_code_upload",
    "workspace_audit_input_mode", "workspace_audit_pasted_text",
    "workspace_audit_report_file", "workspace_audit_scope_mode",
    "workspace_audit_scope_values",
)


class ProjectSession:
    """Own project scoped Streamlit state and switch it atomically."""

    def __init__(self, state: MutableMapping[str, Any], query_params: MutableMapping[str, Any]):
        self.state = state
        self.query_params = query_params

    def clear(self) -> None:
        for key in PROJECT_SESSION_KEYS:
            self.state.pop(key, None)
        self.query_params.pop("project", None)

    def save_conversations(self, store: Any, project_id: str) -> None:
        conversations = self.state.get("project_conversations")
        if isinstance(conversations, list) and conversations:
            store.save_conversations(
                project_id,
                conversations,
                str(self.state.get("active_conversation_id", "")),
            )
            return
        store.save_histories(
            project_id,
            self.state.get("paper_qa_history", []),
            self.state.get("joint_qa_history", []),
        )

    def restore(self, store: Any, project_id: str, *, keep_upload: bool = False) -> None:
        saved = store.load_learning_project(project_id)
        restored_title = recover_paper_title(saved.paper)
        if restored_title != saved.metadata.title:
            store.update_project_title(saved.metadata.project_id, restored_title)
        paper = saved.paper.model_copy(update={"title": restored_title})
        report = saved.report.model_copy(update={"paper_title": restored_title}) if saved.report else None
        review = store.load_peer_review(project_id)
        self.state.update({
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
        })
        if not keep_upload:
            self.state.pop("paper_pdf_upload", None)
        if report is not None:
            self.state["result_mode"] = "learning"
        elif self.state.get("peer_review") is not None:
            self.state["result_mode"] = "peer_review"
        else:
            records = store.list_audit_runs(saved.metadata.project_id)
            if records:
                metadata, run = store.load_audit_run(saved.metadata.project_id, records[0].audit_id)
                self.state.update({
                    "audit_run": run.model_copy(update={"paper_title": restored_title}),
                    "active_audit_id": metadata.audit_id,
                    "audit_record_metadata": metadata,
                })
            self.state["result_mode"] = "audit_project"
        self.state.pop("code_parse_warning", None)
        self.query_params["project"] = saved.metadata.project_id

    def open(self, store: Any, project_id: str) -> None:
        current_id = self.state.get("active_project_id")
        if current_id and current_id != project_id:
            self.save_conversations(store, str(current_id))
        self.clear()
        self.restore(store, project_id)

    def initialize_learning(
        self, paper: Any, pdf_bytes: bytes, report: Any, codebase: Any,
        code_warning: str | None, filename: str,
    ) -> None:
        self.state.update({
            "learning_report": report, "learning_pdf_bytes": pdf_bytes,
            "learning_paper": paper, "parsed_codebase": codebase,
            "result_mode": "learning", "paper_qa_history": [],
            "joint_qa_history": [], "project_original_filename": filename,
        })
        if code_warning:
            self.state["code_parse_warning"] = code_warning
        else:
            self.state.pop("code_parse_warning", None)
        for key in PROJECT_SESSION_KEYS:
            if key.startswith(("learning_", "qa_", "joint_")) and key not in {
                "learning_report", "learning_pdf_bytes", "learning_paper", "learning_report",
            }:
                self.state.pop(key, None)
