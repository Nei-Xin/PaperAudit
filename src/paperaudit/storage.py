"""Local single-user project persistence for the paper learning workspace."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import shutil
from tempfile import NamedTemporaryFile
from typing import Any, Sequence

from paperaudit.code_parser import CURRENT_CODE_INDEX_VERSION, rebuild_code_index

from paperaudit.models import (
    AuditJob,
    AuditJobStatus,
    AuditRun,
    AuditRuntimeSnapshot,
    ClaimCategory,
    JointAnswer,
    LearningJob,
    LearningReport,
    PaperAnswer,
    ParsedCodebase,
    ParsedPaper,
)


SETTINGS_SCHEMA_VERSION = 1
PROJECT_SCHEMA_VERSION = 1
AUDIT_SCHEMA_VERSION = 1
AUDIT_JOB_SCHEMA_VERSION = 1
LEARNING_JOB_SCHEMA_VERSION = 1
AUDIT_SOURCE_TYPES = {"generated_learning_report", "uploaded_report"}


class StorageError(RuntimeError):
    """Raised when a configured storage location or saved project is unusable."""


@dataclass(frozen=True)
class StorageSettings:
    storage_root: Path
    schema_version: int = SETTINGS_SCHEMA_VERSION


@dataclass(frozen=True)
class ProjectMetadata:
    project_id: str
    title: str
    original_filename: str
    created_at: str
    updated_at: str
    has_code: bool = False
    has_learning_report: bool = True


@dataclass(frozen=True)
class SavedLearningProject:
    metadata: ProjectMetadata
    pdf_bytes: bytes
    paper: ParsedPaper
    report: LearningReport | None
    codebase: ParsedCodebase | None
    paper_history: list[PaperAnswer]
    joint_history: list[JointAnswer]


@dataclass(frozen=True)
class AuditRecordMetadata:
    audit_id: str
    project_id: str
    created_at: str
    source_type: str
    source_label: str
    report_hash: str
    grade: str
    total_score: float | None
    audit_coverage: float
    critical_count: int
    high_count: int
    model: str
    reasoning_effort: str


def default_settings_dir() -> Path:
    override = os.getenv("PAPERAUDIT_SETTINGS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "PaperAudit"
    return Path.home() / ".paperaudit"


def suggested_storage_root() -> Path:
    documents = Path.home() / "Documents"
    base = documents if documents.exists() else Path.home()
    return base / "PaperAuditData"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise StorageError(f"无法写入 {path}：{exc}") from exc


def _atomic_write_json(path: Path, value: Any) -> bool:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if path.exists():
        try:
            if path.read_bytes() == payload:
                return False
        except OSError:
            pass
    _atomic_write(path, payload)
    return True


def validate_storage_root(value: str | Path) -> Path:
    raw_path = Path(value).expanduser()
    if not raw_path.is_absolute():
        raise StorageError("请输入完整的绝对路径，例如 D:\\PaperAuditData。")
    try:
        root = raw_path.resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / "projects").mkdir(exist_ok=True)
    except OSError as exc:
        raise StorageError(f"无法创建保存目录：{exc}") from exc

    marker = root / ".paperaudit-write-test"
    try:
        marker.write_text("ok", encoding="utf-8")
        marker.unlink()
    except OSError as exc:
        marker.unlink(missing_ok=True)
        raise StorageError(f"保存目录不可写：{exc}") from exc
    return root


def load_storage_settings(settings_dir: Path | None = None) -> StorageSettings | None:
    path = (settings_dir or default_settings_dir()) / "settings.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if int(data.get("schema_version", 0)) != SETTINGS_SCHEMA_VERSION:
            raise StorageError("存储设置版本不受支持，请重新选择保存位置。")
        configured = Path(str(data["storage_root"])).expanduser()
        if not configured.is_absolute() or not configured.exists():
            raise StorageError("原保存目录当前不可访问，请重新选择保存位置。")
        return StorageSettings(storage_root=configured.resolve())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise StorageError("存储设置文件已损坏，请重新选择保存位置。") from exc


def save_storage_settings(
    storage_root: str | Path,
    settings_dir: Path | None = None,
) -> StorageSettings:
    root = validate_storage_root(storage_root)
    path = (settings_dir or default_settings_dir()) / "settings.json"
    _atomic_write_json(
        path,
        {
            "schema_version": SETTINGS_SCHEMA_VERSION,
            "storage_root": str(root),
        },
    )
    return StorageSettings(storage_root=root)


def choose_storage_directory(initial_directory: str | Path | None = None) -> Path | None:
    """Open the native local folder chooser; callers should retain a text fallback."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            title="选择 PaperAudit 项目保存位置",
            initialdir=str(initial_directory or suggested_storage_root().parent),
            mustexist=False,
        )
        root.destroy()
        return Path(selected) if selected else None
    except Exception as exc:
        raise StorageError(f"无法打开系统文件夹选择器：{exc}") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _metadata_from_dict(data: dict[str, Any]) -> ProjectMetadata:
    return ProjectMetadata(
        project_id=str(data["project_id"]),
        title=str(data["title"]),
        original_filename=str(data.get("original_filename", "paper.pdf")),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        has_code=bool(data.get("has_code", False)),
        has_learning_report=bool(data.get("has_learning_report", True)),
    )


def _audit_metadata_from_dict(data: dict[str, Any]) -> AuditRecordMetadata:
    return AuditRecordMetadata(
        audit_id=str(data["audit_id"]),
        project_id=str(data["project_id"]),
        created_at=str(data["created_at"]),
        source_type=str(data["source_type"]),
        source_label=str(data["source_label"]),
        report_hash=str(data["report_hash"]),
        grade=str(data["grade"]),
        total_score=(
            float(data["total_score"])
            if data.get("total_score") is not None
            else None
        ),
        audit_coverage=float(data["audit_coverage"]),
        critical_count=int(data.get("critical_count", 0)),
        high_count=int(data.get("high_count", 0)),
        model=str(data["model"]),
        reasoning_effort=str(data["reasoning_effort"]),
    )


def _record_id(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}-{secrets.token_hex(3)}"


def _validate_record_id(value: str, prefix: str, label: str) -> str:
    if (
        not value.startswith(f"{prefix}-")
        or any(character not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-" for character in value)
    ):
        raise StorageError(f"{label} ID 无效。")
    return value


class ProjectStore:
    def __init__(self, storage_root: str | Path):
        self.storage_root = validate_storage_root(storage_root)
        self.projects_dir = self.storage_root / "projects"

    def _project_dir(self, project_id: str) -> Path:
        if not project_id or any(character not in "0123456789abcdef" for character in project_id):
            raise StorageError("项目 ID 无效。")
        return self.projects_dir / project_id

    @staticmethod
    def project_id(pdf_bytes: bytes) -> str:
        from hashlib import sha256

        return sha256(pdf_bytes).hexdigest()[:16]

    def save_learning_project(
        self,
        pdf_bytes: bytes,
        original_filename: str,
        paper: ParsedPaper,
        report: LearningReport,
        codebase: ParsedCodebase | None = None,
        paper_history: Sequence[PaperAnswer] = (),
        joint_history: Sequence[JointAnswer] = (),
    ) -> ProjectMetadata:
        metadata = self.save_paper_project(pdf_bytes, original_filename, paper)
        project_id = metadata.project_id
        project_dir = self._project_dir(project_id)
        metadata_path = project_dir / "metadata.json"
        metadata = ProjectMetadata(
            project_id=project_id,
            title=report.paper_title,
            original_filename=original_filename,
            created_at=metadata.created_at,
            updated_at=_utc_now(),
            has_code=codebase is not None or (project_dir / "codebase.json").exists(),
            has_learning_report=True,
        )
        _atomic_write(project_dir / "learning-report.json", report.model_dump_json(indent=2).encode("utf-8"))
        if codebase is not None:
            _atomic_write(project_dir / "codebase.json", codebase.model_dump_json(indent=2).encode("utf-8"))
        self._save_session(project_dir, paper_history, joint_history)
        _atomic_write_json(metadata_path, metadata.__dict__)
        return metadata

    def save_paper_project(
        self,
        pdf_bytes: bytes,
        original_filename: str,
        paper: ParsedPaper,
    ) -> ProjectMetadata:
        """Create or refresh a paper project without requiring a learning report."""

        project_id = self.project_id(pdf_bytes)
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = project_dir / "metadata.json"
        created_at = _utc_now()
        has_code = (project_dir / "codebase.json").exists()
        has_learning_report = (project_dir / "learning-report.json").exists()
        if metadata_path.exists():
            try:
                existing = _metadata_from_dict(
                    json.loads(metadata_path.read_text(encoding="utf-8"))
                )
                created_at = existing.created_at
                has_code = existing.has_code or has_code
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
        metadata = ProjectMetadata(
            project_id=project_id,
            title=paper.title,
            original_filename=original_filename,
            created_at=created_at,
            updated_at=_utc_now(),
            has_code=has_code,
            has_learning_report=has_learning_report,
        )
        _atomic_write(project_dir / "paper.pdf", pdf_bytes)
        _atomic_write(
            project_dir / "paper-index.json",
            paper.model_dump_json(indent=2).encode("utf-8"),
        )
        session_path = project_dir / "session.json"
        if not session_path.exists():
            self._save_session(project_dir, (), ())
        _atomic_write_json(metadata_path, metadata.__dict__)
        return metadata

    def save_histories(
        self,
        project_id: str,
        paper_history: Sequence[PaperAnswer],
        joint_history: Sequence[JointAnswer],
    ) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise StorageError("需要保存的项目不存在。")
        if self._save_session(project_dir, paper_history, joint_history):
            metadata_path = project_dir / "metadata.json"
            try:
                metadata = _metadata_from_dict(
                    json.loads(metadata_path.read_text(encoding="utf-8"))
                )
                updated = ProjectMetadata(
                    project_id=metadata.project_id,
                    title=metadata.title,
                    original_filename=metadata.original_filename,
                    created_at=metadata.created_at,
                    updated_at=_utc_now(),
                    has_code=metadata.has_code,
                    has_learning_report=metadata.has_learning_report,
                )
                _atomic_write_json(metadata_path, updated.__dict__)
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise StorageError("项目元数据已损坏，无法更新保存时间。") from exc

    @staticmethod
    def _save_session(
        project_dir: Path,
        paper_history: Sequence[PaperAnswer],
        joint_history: Sequence[JointAnswer],
    ) -> bool:
        return _atomic_write_json(
            project_dir / "session.json",
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "paper_qa_history": [item.model_dump(mode="json") for item in paper_history],
                "joint_qa_history": [item.model_dump(mode="json") for item in joint_history],
            },
        )

    def load_learning_project(self, project_id: str) -> SavedLearningProject:
        project_dir = self._project_dir(project_id)
        try:
            metadata = _metadata_from_dict(
                json.loads((project_dir / "metadata.json").read_text(encoding="utf-8"))
            )
            pdf_bytes = (project_dir / "paper.pdf").read_bytes()
            paper = ParsedPaper.model_validate_json(
                (project_dir / "paper-index.json").read_text(encoding="utf-8")
            )
            report_path = project_dir / "learning-report.json"
            report = (
                LearningReport.model_validate_json(
                    report_path.read_text(encoding="utf-8")
                )
                if report_path.exists()
                else None
            )
            code_path = project_dir / "codebase.json"
            codebase = (
                ParsedCodebase.model_validate_json(code_path.read_text(encoding="utf-8"))
                if code_path.exists()
                else None
            )
            if codebase is not None and codebase.index_version < CURRENT_CODE_INDEX_VERSION:
                try:
                    codebase = rebuild_code_index(codebase)
                    _atomic_write(
                        code_path,
                        codebase.model_dump_json(indent=2).encode("utf-8"),
                    )
                except (OSError, ValueError, StorageError) as exc:
                    raise StorageError(
                        "代码索引自动升级失败，旧索引未被修改。"
                    ) from exc
            session_path = project_dir / "session.json"
            session = (
                json.loads(session_path.read_text(encoding="utf-8"))
                if session_path.exists()
                else {}
            )
            paper_history = [
                PaperAnswer.model_validate(item)
                for item in session.get("paper_qa_history", [])
            ]
            joint_history = [
                JointAnswer.model_validate(item)
                for item in session.get("joint_qa_history", [])
            ]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("项目文件不完整或已损坏，无法恢复。") from exc
        return SavedLearningProject(
            metadata=metadata,
            pdf_bytes=pdf_bytes,
            paper=paper,
            report=report,
            codebase=codebase,
            paper_history=paper_history,
            joint_history=joint_history,
        )

    def list_projects(self) -> list[ProjectMetadata]:
        projects: list[ProjectMetadata] = []
        for metadata_path in self.projects_dir.glob("*/metadata.json"):
            try:
                projects.append(
                    _metadata_from_dict(
                        json.loads(metadata_path.read_text(encoding="utf-8"))
                    )
                )
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> None:
        """Permanently remove one persisted project and all of its records."""

        project_dir = self._require_project_dir(project_id)
        active_statuses = {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
        if any(job.status in active_statuses for job in self.list_audit_jobs(project_id)):
            raise StorageError("当前论文仍有审计任务正在执行，完成后才能删除。")
        if any(job.status in active_statuses for job in self.list_learning_jobs(project_id)):
            raise StorageError("当前论文仍在生成讲解，完成后才能删除。")

        projects_root = self.projects_dir.resolve()
        target = project_dir.resolve()
        if target.parent != projects_root:
            raise StorageError("项目目录无效，已取消删除。")
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise StorageError(f"无法删除论文项目：{exc}") from exc

    def update_project_title(self, project_id: str, title: str) -> ProjectMetadata:
        """Persist a repaired display title without changing project contents."""

        project_dir = self._require_project_dir(project_id)
        metadata_path = project_dir / "metadata.json"
        try:
            metadata = _metadata_from_dict(
                json.loads(metadata_path.read_text(encoding="utf-8"))
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("项目元数据已损坏，无法更新标题。") from exc
        clean_title = " ".join(title.split()).strip()
        if not clean_title or clean_title == metadata.title:
            return metadata
        updated = replace(metadata, title=clean_title)
        _atomic_write_json(metadata_path, updated.__dict__)
        return updated

    def _require_project_dir(self, project_id: str) -> Path:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists() or not (project_dir / "metadata.json").exists():
            raise StorageError("需要保存审计的论文项目不存在。")
        return project_dir

    def _touch_project(self, project_dir: Path) -> None:
        metadata_path = project_dir / "metadata.json"
        try:
            metadata = _metadata_from_dict(
                json.loads(metadata_path.read_text(encoding="utf-8"))
            )
            updated = ProjectMetadata(
                project_id=metadata.project_id,
                title=metadata.title,
                original_filename=metadata.original_filename,
                created_at=metadata.created_at,
                updated_at=_utc_now(),
                has_code=metadata.has_code,
                has_learning_report=metadata.has_learning_report,
            )
            _atomic_write_json(metadata_path, updated.__dict__)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("项目元数据已损坏，无法更新保存时间。") from exc

    def save_audit_run(
        self,
        project_id: str,
        run: AuditRun,
        *,
        source_type: str,
        source_label: str,
        model: str,
        reasoning_effort: str,
        retrieval_top_k: int,
        judge_batch_size: int,
    ) -> AuditRecordMetadata:
        project_dir = self._require_project_dir(project_id)
        if source_type not in AUDIT_SOURCE_TYPES:
            raise StorageError("审计来源无效。")
        if not source_label.strip():
            raise StorageError("审计来源名称不能为空。")

        audit_id = _record_id("audit")
        created_at = _utc_now()
        metadata = AuditRecordMetadata(
            audit_id=audit_id,
            project_id=project_id,
            created_at=created_at,
            source_type=source_type,
            source_label=source_label.strip(),
            report_hash=sha256(run.report_text.encode("utf-8")).hexdigest(),
            grade=run.summary.grade.value,
            total_score=run.summary.total_score,
            audit_coverage=run.summary.audit_coverage,
            critical_count=run.summary.critical_count,
            high_count=run.summary.high_count,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        audits_dir = project_dir / "audits"
        audits_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(
            audits_dir / f"{audit_id}.json",
            {
                "schema_version": AUDIT_SCHEMA_VERSION,
                "metadata": metadata.__dict__,
                "runtime": {
                    "retrieval_top_k": retrieval_top_k,
                    "judge_batch_size": judge_batch_size,
                },
                "run": run.model_dump(mode="json"),
            },
        )
        records = self._scan_audit_runs(project_id, audits_dir)
        _atomic_write_json(
            audits_dir / "index.json",
            {
                "schema_version": AUDIT_SCHEMA_VERSION,
                "records": [item.__dict__ for item in records],
            },
        )
        self._touch_project(project_dir)
        return metadata

    def _scan_audit_runs(
        self,
        project_id: str,
        audits_dir: Path,
    ) -> list[AuditRecordMetadata]:
        records: list[AuditRecordMetadata] = []
        for audit_path in audits_dir.glob("audit-*.json"):
            try:
                payload = json.loads(audit_path.read_text(encoding="utf-8"))
                if int(payload.get("schema_version", 0)) != AUDIT_SCHEMA_VERSION:
                    continue
                metadata = _audit_metadata_from_dict(payload["metadata"])
                _validate_record_id(metadata.audit_id, "audit", "审计记录")
                if metadata.project_id != project_id:
                    continue
                records.append(metadata)
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def list_audit_runs(self, project_id: str) -> list[AuditRecordMetadata]:
        project_dir = self._require_project_dir(project_id)
        audits_dir = project_dir / "audits"
        if not audits_dir.exists():
            return []

        audit_files = list(audits_dir.glob("audit-*.json"))
        index_path = audits_dir / "index.json"
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            if int(payload.get("schema_version", 0)) != AUDIT_SCHEMA_VERSION:
                raise ValueError("unsupported audit index")
            records = [
                _audit_metadata_from_dict(item) for item in payload.get("records", [])
            ]
            if len(records) != len(audit_files):
                raise ValueError("stale audit index")
            for metadata in records:
                _validate_record_id(metadata.audit_id, "audit", "审计记录")
                if metadata.project_id != project_id:
                    raise ValueError("wrong audit project")
                if not (audits_dir / f"{metadata.audit_id}.json").is_file():
                    raise ValueError("missing audit record")
            return sorted(records, key=lambda item: item.created_at, reverse=True)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            records = self._scan_audit_runs(project_id, audits_dir)
            _atomic_write_json(
                index_path,
                {
                    "schema_version": AUDIT_SCHEMA_VERSION,
                    "records": [item.__dict__ for item in records],
                },
            )
            return records

    def load_audit_run(
        self,
        project_id: str,
        audit_id: str,
    ) -> tuple[AuditRecordMetadata, AuditRun]:
        project_dir = self._require_project_dir(project_id)
        _validate_record_id(audit_id, "audit", "审计记录")
        try:
            payload = json.loads(
                (project_dir / "audits" / f"{audit_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            if int(payload.get("schema_version", 0)) != AUDIT_SCHEMA_VERSION:
                raise ValueError("unsupported audit record")
            metadata = _audit_metadata_from_dict(payload["metadata"])
            if metadata.audit_id != audit_id or metadata.project_id != project_id:
                raise ValueError("audit record identity mismatch")
            run = AuditRun.model_validate(payload["run"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("审计记录不存在、已损坏或版本不受支持。") from exc
        return metadata, run

    def create_audit_job(
        self,
        project_id: str,
        *,
        report_text: str,
        source_type: str,
        source_label: str,
        source_filename: str | None,
        scope: Sequence[ClaimCategory],
        audit_mode: str,
        runtime: AuditRuntimeSnapshot | dict[str, Any],
    ) -> AuditJob:
        project_dir = self._require_project_dir(project_id)
        clean_report = report_text.strip()
        if not clean_report:
            raise StorageError("待审计报告不能为空。")
        if source_type not in AUDIT_SOURCE_TYPES:
            raise StorageError("审计来源无效。")
        if not scope:
            raise StorageError("请至少选择一个审计范围。")
        runtime_snapshot = AuditRuntimeSnapshot.model_validate(runtime)
        report_hash = sha256(clean_report.encode("utf-8")).hexdigest()
        for existing in self.list_audit_jobs(project_id):
            if (
                existing.report_hash == report_hash
                and existing.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
            ):
                raise StorageError("相同报告已有审计任务正在排队或执行。")

        job = AuditJob(
            schema_version=AUDIT_JOB_SCHEMA_VERSION,
            job_id=_record_id("audit-job"),
            project_id=project_id,
            created_at=_utc_now(),
            source_type=source_type,
            source_label=source_label.strip() or "审计报告",
            source_filename=(source_filename.strip() if source_filename else None),
            report_hash=report_hash,
            report_text=clean_report,
            scope=list(scope),
            audit_mode=audit_mode,
            runtime=runtime_snapshot,
        )
        jobs_dir = project_dir / "audit-jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            jobs_dir / f"{job.job_id}.json",
            job.model_dump_json(indent=2).encode("utf-8"),
        )
        return job

    def load_audit_job(self, project_id: str, job_id: str) -> AuditJob:
        project_dir = self._require_project_dir(project_id)
        _validate_record_id(job_id, "audit-job", "审计任务")
        try:
            job = AuditJob.model_validate_json(
                (project_dir / "audit-jobs" / f"{job_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            if (
                job.schema_version != AUDIT_JOB_SCHEMA_VERSION
                or job.project_id != project_id
                or job.job_id != job_id
            ):
                raise ValueError("audit job identity mismatch")
            if job.status == AuditJobStatus.SUCCEEDED and not job.audit_id:
                raise ValueError("completed audit job has no result")
            if job.audit_id is not None:
                _validate_record_id(job.audit_id, "audit", "审计记录")
        except (OSError, TypeError, ValueError) as exc:
            raise StorageError("审计任务不存在、已损坏或版本不受支持。") from exc
        return job

    def list_audit_jobs(self, project_id: str) -> list[AuditJob]:
        project_dir = self._require_project_dir(project_id)
        jobs_dir = project_dir / "audit-jobs"
        if not jobs_dir.exists():
            return []
        jobs: list[AuditJob] = []
        for job_path in jobs_dir.glob("audit-job-*.json"):
            try:
                job = AuditJob.model_validate_json(job_path.read_text(encoding="utf-8"))
                _validate_record_id(job.job_id, "audit-job", "审计任务")
                if (
                    job.schema_version == AUDIT_JOB_SCHEMA_VERSION
                    and job.project_id == project_id
                ):
                    if job.status == AuditJobStatus.SUCCEEDED and not job.audit_id:
                        continue
                    if job.audit_id is not None:
                        _validate_record_id(job.audit_id, "audit", "审计记录")
                    jobs.append(job)
            except (OSError, TypeError, ValueError):
                continue
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

    def update_audit_job(self, project_id: str, job: AuditJob) -> None:
        project_dir = self._require_project_dir(project_id)
        _validate_record_id(job.job_id, "audit-job", "审计任务")
        if job.project_id != project_id:
            raise StorageError("审计任务不属于当前论文项目。")
        if job.status == AuditJobStatus.SUCCEEDED and not job.audit_id:
            raise StorageError("已完成的审计任务缺少结果记录。")
        if job.audit_id is not None:
            _validate_record_id(job.audit_id, "audit", "审计记录")
        _atomic_write(
            project_dir / "audit-jobs" / f"{job.job_id}.json",
            job.model_dump_json(indent=2).encode("utf-8"),
        )

    def mark_interrupted_audit_jobs(self) -> int:
        interrupted = 0
        for metadata in self.list_projects():
            for job in self.list_audit_jobs(metadata.project_id):
                if job.status not in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}:
                    continue
                updated = job.model_copy(
                    update={
                        "status": AuditJobStatus.INTERRUPTED,
                        "completed_at": _utc_now(),
                        "stage": "任务已中断",
                        "error": "应用在任务完成前退出，请重新执行审计。",
                    }
                )
                self.update_audit_job(metadata.project_id, updated)
                interrupted += 1
        return interrupted

    def create_learning_job(
        self,
        project_id: str,
        *,
        runtime: AuditRuntimeSnapshot | dict[str, Any],
    ) -> LearningJob:
        saved = self.load_learning_project(project_id)
        if saved.report is not None:
            raise StorageError("当前项目已经包含论文讲解。")
        for existing in self.list_learning_jobs(project_id):
            if existing.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}:
                raise StorageError("当前论文已有讲解任务正在执行。")
        job = LearningJob(
            schema_version=LEARNING_JOB_SCHEMA_VERSION,
            job_id=_record_id("learning-job"),
            project_id=project_id,
            created_at=_utc_now(),
            runtime=AuditRuntimeSnapshot.model_validate(runtime),
        )
        jobs_dir = self._project_dir(project_id) / "learning-jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            jobs_dir / f"{job.job_id}.json",
            job.model_dump_json(indent=2).encode("utf-8"),
        )
        return job

    def load_learning_job(self, project_id: str, job_id: str) -> LearningJob:
        project_dir = self._require_project_dir(project_id)
        _validate_record_id(job_id, "learning-job", "论文讲解任务")
        try:
            job = LearningJob.model_validate_json(
                (project_dir / "learning-jobs" / f"{job_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            if (
                job.schema_version != LEARNING_JOB_SCHEMA_VERSION
                or job.project_id != project_id
                or job.job_id != job_id
            ):
                raise ValueError("learning job identity mismatch")
        except (OSError, TypeError, ValueError) as exc:
            raise StorageError("论文讲解任务不存在、已损坏或版本不受支持。") from exc
        return job

    def list_learning_jobs(self, project_id: str) -> list[LearningJob]:
        project_dir = self._require_project_dir(project_id)
        jobs_dir = project_dir / "learning-jobs"
        if not jobs_dir.exists():
            return []
        jobs: list[LearningJob] = []
        for job_path in jobs_dir.glob("learning-job-*.json"):
            try:
                job = LearningJob.model_validate_json(job_path.read_text(encoding="utf-8"))
                _validate_record_id(job.job_id, "learning-job", "论文讲解任务")
                if (
                    job.schema_version == LEARNING_JOB_SCHEMA_VERSION
                    and job.project_id == project_id
                ):
                    jobs.append(job)
            except (OSError, TypeError, ValueError):
                continue
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

    def update_learning_job(self, project_id: str, job: LearningJob) -> None:
        project_dir = self._require_project_dir(project_id)
        _validate_record_id(job.job_id, "learning-job", "论文讲解任务")
        if job.project_id != project_id:
            raise StorageError("论文讲解任务不属于当前项目。")
        _atomic_write(
            project_dir / "learning-jobs" / f"{job.job_id}.json",
            job.model_dump_json(indent=2).encode("utf-8"),
        )

    def mark_interrupted_learning_jobs(self) -> int:
        interrupted = 0
        for metadata in self.list_projects():
            for job in self.list_learning_jobs(metadata.project_id):
                if job.status not in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}:
                    continue
                updated = job.model_copy(
                    update={
                        "status": AuditJobStatus.INTERRUPTED,
                        "completed_at": _utc_now(),
                        "stage": "任务已中断",
                        "error": "应用在讲解生成完成前退出，请重新生成。",
                    }
                )
                self.update_learning_job(metadata.project_id, updated)
                interrupted += 1
        return interrupted
