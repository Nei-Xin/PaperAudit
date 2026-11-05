"""Read saved projects and audit exports without model calls or data migration."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from paperaudit.models import AuditRun
from paperaudit.reporting import render_markdown
from paperaudit.storage import ProjectStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storage", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    store = ProjectStore(args.storage.resolve())
    projects, audits = [], []
    for project in store.list_projects():
        saved = store.load_learning_project(project.project_id)
        projects.append(dict(project_id=project.project_id, pages=saved.paper.page_count,
                             pdf_sha256=sha256(saved.pdf_bytes).hexdigest()))
        for record in store.list_audit_runs(project.project_id):
            _, run = store.load_audit_run(project.project_id, record.audit_id)
            exported = run.model_dump_json()
            if AuditRun.model_validate_json(exported) != run:
                raise ValueError("JSON export roundtrip failed")
            markdown = render_markdown(run)
            if not markdown.strip():
                raise ValueError("Empty Markdown export")
            audits.append(dict(project_id=project.project_id, audit_id=record.audit_id,
                               deep_audit=run.deep_audit, claims=len(run.audits),
                               json_sha256=sha256(exported.encode()).hexdigest(),
                               markdown_sha256=sha256(markdown.encode()).hexdigest()))
    result = dict(projects=projects, audits=audits, project_count=len(projects),
                  audit_count=len(audits), all_exports_roundtrip=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in {"projects", "audits"}}))


if __name__ == "__main__":
    main()
