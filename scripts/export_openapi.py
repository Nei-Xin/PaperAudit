"""Generate the contract without starting services or accessing project data."""
import json
from pathlib import Path
from paperaudit.api.main import create_app

path = Path(__file__).resolve().parents[1] / "web" / "openapi.json"
path.write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n")
