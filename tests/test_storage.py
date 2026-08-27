from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from paperaudit.models import (
    AnswerScope,
    AnswerStatus,
    AuditJobStatus,
    AuditRuntimeSnapshot,
    ClaimCategory,
    CodeChunk,
    CodeFile,
    CodeSelection,
    EvidenceAnchor,
    ExplanationPoint,
    LearningReport,
    LearningSectionType,
    JointAnswer,
    PaperAnswer,
    PaperChunk,
    ParsedPaper,
    ParsedCodebase,
    ReportSection,
)
from paperaudit.storage import (
    ProjectStore,
    StorageError,
    load_storage_settings,
    save_storage_settings,
)
from paperaudit.ui.demo_data import get_demo_audit_run


def _paper() -> ParsedPaper:
    return ParsedPaper(
        title="Saved Paper",
        page_count=1,
        chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence text.")],
    )


def _report() -> LearningReport:
    return LearningReport(
        paper_title="Saved Paper",
        one_sentence_summary="Summary.",
        sections=[
            ReportSection(
                section_type=section_type,
                title=section_type.value,
                overview="Overview.",
                points=[
                    ExplanationPoint(
                        title="Point",
                        explanation="Explanation.",
                        evidence=[
                            EvidenceAnchor(
                                chunk_id="p1_b1",
                                page=1,
                                text="Evidence text.",
                            )
                        ],
                    )
                ],
            )
            for section_type in LearningSectionType
        ],
    )


def test_storage_settings_round_trip(tmp_path: Path) -> None:
    settings_dir = tmp_path / "settings"
    storage_root = tmp_path / "library"

    saved = save_storage_settings(storage_root, settings_dir)
    loaded = load_storage_settings(settings_dir)

    assert loaded is not None
    assert loaded.storage_root == saved.storage_root
    assert (storage_root / "projects").is_dir()


def test_storage_settings_require_absolute_path(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="绝对路径"):
        save_storage_settings("relative/path", tmp_path / "settings")


def test_learning_project_and_history_round_trip(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    pdf_bytes = b"minimal-pdf-fixture"
    metadata = store.save_learning_project(
        pdf_bytes,
        "paper.pdf",
        _paper(),
        _report(),
    )
    answer = PaperAnswer(
        question="What is supported?",
        answer="The saved evidence supports it.",
        status=AnswerStatus.ANSWERED,
        citations=[EvidenceAnchor(chunk_id="p1_b1", page=1, text="Evidence text.")],
    )
    joint_answer = JointAnswer(
        question="Explain the selection.",
        answer="It resets cached image state.",
        scope=AnswerScope.CODE,
        status=AnswerStatus.ANSWERED,
        selected_code=CodeSelection(
            path="predictor.py",
            start_line=10,
            end_line=11,
            text="self.features = None",
            context_text="self.features = None",
        ),
    )
    store.save_histories(metadata.project_id, [answer], [joint_answer])

    restored = store.load_learning_project(metadata.project_id)

    assert restored.metadata.title == "Saved Paper"
    assert restored.pdf_bytes == pdf_bytes
    assert restored.paper == _paper()
    assert restored.report == _report()
    assert restored.paper_history == [answer]
    assert restored.joint_history == [joint_answer]
    assert [item.project_id for item in store.list_projects()] == [metadata.project_id]


def test_loading_legacy_code_index_upgrades_once_without_losing_history(
    tmp_path: Path,
) -> None:
    store = ProjectStore(tmp_path / "library")
    content = "class Demo:\n    def run(self):\n        return 1\n"
    legacy = ParsedCodebase(
        name="demo",
        files=[CodeFile(path="demo.py", language="python", content=content, line_count=3)],
        chunks=[
            CodeChunk(
                chunk_id="old-class",
                path="demo.py",
                language="python",
                symbol="Demo",
                start_line=1,
                end_line=3,
                content=content,
            )
        ],
    )
    metadata = store.save_learning_project(
        b"legacy-code-paper",
        "paper.pdf",
        _paper(),
        _report(),
        codebase=legacy,
        joint_history=[
            JointAnswer(
                question="旧问题",
                answer="旧回答",
                scope=AnswerScope.CODE,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        ],
    )
    code_path = store._project_dir(metadata.project_id) / "codebase.json"
    before = json.loads(code_path.read_text(encoding="utf-8"))
    before.pop("index_version", None)
    code_path.write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")

    restored = store.load_learning_project(metadata.project_id)
    first_bytes = code_path.read_bytes()
    restored_again = store.load_learning_project(metadata.project_id)

    assert restored.codebase is not None
    assert restored.codebase.index_version == 2
    assert [chunk.symbol for chunk in restored.codebase.chunks] == ["Demo", "Demo.run"]
    assert restored.joint_history[0].question == "旧问题"
    assert restored_again.joint_history == restored.joint_history
    assert code_path.read_bytes() == first_bytes


def test_audit_only_project_supports_multiple_audit_records(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    pdf_bytes = b"audit-only-paper"
    metadata = store.save_paper_project(pdf_bytes, "paper.pdf", _paper())

    restored = store.load_learning_project(metadata.project_id)

    assert restored.report is None
    assert metadata.has_learning_report is False
    first_run = get_demo_audit_run().model_copy(update={"report_text": "报告一"})
    second_run = get_demo_audit_run().model_copy(update={"report_text": "报告二"})
    first = store.save_audit_run(
        metadata.project_id,
        first_run,
        source_type="uploaded_report",
        source_label="first.md",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )
    second = store.save_audit_run(
        metadata.project_id,
        second_run,
        source_type="uploaded_report",
        source_label="slides.pptx",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )

    records = store.list_audit_runs(metadata.project_id)

    assert len(records) == 2
    assert {record.audit_id for record in records} == {first.audit_id, second.audit_id}
    assert store.list_projects()[0].has_learning_report is False


def test_adding_learning_report_upgrades_audit_only_project(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    pdf_bytes = b"upgrade-paper"
    initial = store.save_paper_project(pdf_bytes, "paper.pdf", _paper())

    upgraded = store.save_learning_project(
        pdf_bytes,
        "paper.pdf",
        _paper(),
        _report(),
    )

    assert upgraded.project_id == initial.project_id
    assert upgraded.has_learning_report is True
    assert store.load_learning_project(upgraded.project_id).report == _report()


def test_invalid_project_id_is_rejected(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")

    with pytest.raises(StorageError, match="项目 ID 无效"):
        store.load_learning_project("../outside")


def _saved_store(tmp_path: Path) -> tuple[ProjectStore, str]:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_learning_project(
        b"audit-paper",
        "paper.pdf",
        _paper(),
        _report(),
    )
    return store, metadata.project_id


def test_delete_project_removes_the_complete_project_directory(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)
    project_dir = store._project_dir(project_id)

    store.delete_project(project_id)

    assert not project_dir.exists()
    assert store.list_projects() == []
    with pytest.raises(StorageError):
        store.load_learning_project(project_id)


def test_delete_project_refuses_an_active_audit_job(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)
    store.create_audit_job(
        project_id,
        report_text="待审计报告",
        source_type="uploaded_report",
        source_label="notes.md",
        source_filename="notes.md",
        scope=[ClaimCategory.CONTRIBUTION],
        audit_mode="audit_existing",
        runtime=AuditRuntimeSnapshot(
            model="fake-model",
            reasoning_effort="high",
            retrieval_top_k=5,
            judge_batch_size=6,
        ),
    )

    with pytest.raises(StorageError, match="审计任务正在执行"):
        store.delete_project(project_id)
    assert store._project_dir(project_id).exists()


def test_project_title_can_be_repaired_without_changing_project_id(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)

    updated = store.update_project_title(project_id, "Saved Paper Complete Title")

    assert updated.project_id == project_id
    assert updated.title == "Saved Paper Complete Title"
    assert store.list_projects()[0].title == "Saved Paper Complete Title"


def test_audit_history_round_trip_and_multiple_versions(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)
    run = get_demo_audit_run().model_copy(update={"report_text": "版本一"})
    first = store.save_audit_run(
        project_id,
        run,
        source_type="generated_learning_report",
        source_label="当前论文讲解",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )
    second_run = run.model_copy(update={"report_text": "版本二"})
    second = store.save_audit_run(
        project_id,
        second_run,
        source_type="uploaded_report",
        source_label="notes.md",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=8,
        judge_batch_size=4,
    )

    records = store.list_audit_runs(project_id)
    loaded_metadata, loaded_run = store.load_audit_run(project_id, first.audit_id)

    assert first.audit_id != second.audit_id
    assert {record.audit_id for record in records} == {first.audit_id, second.audit_id}
    assert loaded_metadata == first
    assert loaded_run == run
    assert first.report_hash == sha256("版本一".encode("utf-8")).hexdigest()
    assert second.report_hash == sha256("版本二".encode("utf-8")).hexdigest()
    assert (store._project_dir(project_id) / "audits" / "index.json").is_file()


def test_audit_index_recovers_and_skips_corrupt_record(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)
    run = get_demo_audit_run()
    saved = store.save_audit_run(
        project_id,
        run,
        source_type="generated_learning_report",
        source_label="当前论文讲解",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )
    audits_dir = store._project_dir(project_id) / "audits"
    (audits_dir / "index.json").write_text("broken", encoding="utf-8")
    (audits_dir / "audit-20260825T000000Z-broken.json").write_text(
        "not-json", encoding="utf-8"
    )

    records = store.list_audit_runs(project_id)

    assert [record.audit_id for record in records] == [saved.audit_id]
    rebuilt = json.loads((audits_dir / "index.json").read_text(encoding="utf-8"))
    assert rebuilt["records"][0]["audit_id"] == saved.audit_id


def test_audit_job_round_trip_duplicate_guard_and_interruption(tmp_path: Path) -> None:
    store, project_id = _saved_store(tmp_path)
    runtime = AuditRuntimeSnapshot(
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )
    job = store.create_audit_job(
        project_id,
        report_text="待审计报告",
        source_type="uploaded_report",
        source_label="notes.md",
        source_filename="notes.md",
        scope=[ClaimCategory.CONTRIBUTION],
        audit_mode="audit_existing",
        runtime=runtime,
    )

    assert store.load_audit_job(project_id, job.job_id) == job
    with pytest.raises(StorageError, match="已有审计任务"):
        store.create_audit_job(
            project_id,
            report_text="待审计报告",
            source_type="uploaded_report",
            source_label="notes.md",
            source_filename="notes.md",
            scope=[ClaimCategory.CONTRIBUTION],
            audit_mode="audit_existing",
            runtime=runtime,
        )

    assert store.mark_interrupted_audit_jobs() == 1
    interrupted = store.load_audit_job(project_id, job.job_id)
    assert interrupted.status == AuditJobStatus.INTERRUPTED
    assert interrupted.completed_at is not None
    serialized = (
        store._project_dir(project_id) / "audit-jobs" / f"{job.job_id}.json"
    ).read_text(encoding="utf-8")
    assert "api_key" not in serialized
    assert "api_base" not in serialized

    invalid_result = interrupted.model_copy(
        update={
            "status": AuditJobStatus.SUCCEEDED,
            "audit_id": "../outside",
        }
    )
    with pytest.raises(StorageError, match="审计记录 ID 无效"):
        store.update_audit_job(project_id, invalid_result)
