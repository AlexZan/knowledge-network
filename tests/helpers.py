"""Shared test fixtures and helpers."""

import json
import yaml
from pathlib import Path


def setup_concluded_effort(session_dir, effort_id, summary, raw_content=None, raw_lines=None):
    """Create a concluded effort with manifest entry and raw log.

    Args:
        session_dir: Session directory path (will be created if needed)
        effort_id: Effort ID string
        summary: Summary text for the manifest entry
        raw_content: Raw JSONL string (mutually exclusive with raw_lines)
        raw_lines: List of (role, content) tuples to convert to JSONL
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    efforts_dir = session_dir / "efforts"
    efforts_dir.mkdir(exist_ok=True)

    if raw_content is not None:
        pass  # use as-is
    elif raw_lines is not None:
        raw_content = ""
        for role, content in raw_lines:
            raw_content += json.dumps({"role": role, "content": content, "ts": "t"}) + "\n"
    else:
        raw_content = (
            json.dumps({"role": "user", "content": f"Working on {effort_id}", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": f"Details about {effort_id}", "ts": "t2"}) + "\n"
        )
    (efforts_dir / f"{effort_id}.jsonl").write_text(raw_content)

    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {"efforts": []}
    else:
        manifest = {"efforts": []}

    manifest["efforts"].append({
        "id": effort_id,
        "status": "concluded",
        "summary": summary,
    })
    manifest_path.write_text(yaml.dump(manifest))
