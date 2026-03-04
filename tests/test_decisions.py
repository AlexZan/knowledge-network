"""Validate decision state registry against decision docs."""

import re
from pathlib import Path

import yaml

DECISIONS_DIR = Path(__file__).parent.parent / "docs" / "decisions"
STATE_FILE = DECISIONS_DIR / "state.yaml"
ALLOWED_STATUSES = {"draft", "accepted", "implemented", "superseded", "reverted", "deferred"}
REQUIRED_FIELDS = {"id", "title", "status"}


def _load_state():
    return yaml.safe_load(STATE_FILE.read_text())


def _decision_md_files():
    return sorted(DECISIONS_DIR.glob("[0-9]*.md"))


class TestDecisionRegistry:
    def test_state_yaml_exists(self):
        assert STATE_FILE.exists(), "docs/decisions/state.yaml missing"

    def test_every_md_has_state_entry(self):
        entries = {e["id"] for e in _load_state()}
        for md in _decision_md_files():
            doc_id = md.name.split("-", 1)[0]
            assert doc_id in entries, f"{md.name} has no state.yaml entry (id={doc_id})"

    def test_every_state_entry_has_md(self):
        md_ids = {f.name.split("-", 1)[0] for f in _decision_md_files()}
        for entry in _load_state():
            assert entry["id"] in md_ids, f"state.yaml entry {entry['id']} has no .md file"

    def test_statuses_are_valid(self):
        for entry in _load_state():
            assert entry["status"] in ALLOWED_STATUSES, (
                f"Decision {entry['id']}: status '{entry['status']}' "
                f"not in {ALLOWED_STATUSES}"
            )

    def test_required_fields_present(self):
        for entry in _load_state():
            for field in REQUIRED_FIELDS:
                assert field in entry, f"Decision {entry.get('id', '?')}: missing field '{field}'"

    def test_ids_are_unique(self):
        ids = [e["id"] for e in _load_state()]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_md_status_matches_state_yaml(self):
        state_map = {e["id"]: e["status"] for e in _load_state()}
        for md in _decision_md_files():
            doc_id = md.name.split("-", 1)[0]
            if doc_id not in state_map:
                continue
            text = md.read_text()
            match = re.search(r"\*\*Status\*\*:\s*(\w+)", text)
            assert match, f"{md.name}: no **Status**: line found"
            md_status = match.group(1).lower()
            yaml_status = state_map[doc_id]
            assert md_status == yaml_status, (
                f"{md.name}: status '{md_status}' != state.yaml '{yaml_status}'"
            )

    def test_superseded_entries_reference_valid_ids(self):
        all_ids = {e["id"] for e in _load_state()}
        for entry in _load_state():
            refs = entry.get("superseded_by") or []
            for ref in refs:
                assert ref in all_ids, (
                    f"Decision {entry['id']}: superseded_by references "
                    f"unknown id '{ref}'"
                )

    def test_depends_on_references_valid_ids(self):
        all_ids = {e["id"] for e in _load_state()}
        for entry in _load_state():
            deps = entry.get("depends_on") or []
            for dep in deps:
                assert dep in all_ids, (
                    f"Decision {entry['id']}: depends_on references "
                    f"unknown id '{dep}'"
                )
