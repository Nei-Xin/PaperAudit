"""Download pinned public PDFs and reconstruct the frozen evaluation reports."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    samples = json.loads(Path('eval/unseen_e2e_samples_20260924.json').read_text())
    for report in samples['reports']:
        pdf = Path(report['pdf_path'])
        if pdf.exists():
            data = pdf.read_bytes()
        else:
            request = urllib.request.Request(report['url'], headers={'User-Agent': 'PaperAudit evaluation/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
        if not data.startswith(b'%PDF') or hashlib.sha256(data).hexdigest() != report['pdf_sha256']:
            raise ValueError('Pinned PDF hash mismatch: ' + report['paper_id'])
        if not pdf.exists():
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(data)
        text = '\n'.join(fact['text'] for fact in report['facts']) + '\n'
        report_path = Path(report['report_path'])
        if report_path.exists() and report_path.read_text() != text:
            raise ValueError('Existing report differs; refuse overwrite')
        if not report_path.exists():
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(text)
        print(report['paper_id'], 'PDF and report verified')


if __name__ == '__main__':
    main()
