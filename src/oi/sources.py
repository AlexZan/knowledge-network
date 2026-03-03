"""Source registry for logical provenance URIs.

Sources are registered with a name and physical path. Provenance URIs
stored in knowledge nodes use the source name rather than physical paths,
making the graph portable when files move.

URI formats:
    doc://{source_id}/{rel_path}#{fragment}   — document roots
    chatgpt://{source_id}/{conv_id}           — ChatGPT exports
    chatlog://claude-code/{session_id}:L{n}  — Claude Code sessions (no registry needed)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

SOURCES_FILE = "sources.yaml"


# === Registry CRUD ===


def load_sources(session_dir: Path) -> list[dict]:
    """Load the source registry from sources.yaml."""
    path = session_dir / SOURCES_FILE
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("sources", []) if data else []


def save_sources(session_dir: Path, sources: list[dict]) -> None:
    """Save the source registry to sources.yaml."""
    path = session_dir / SOURCES_FILE
    path.write_text(
        yaml.dump({"sources": sources}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def register_source(
    session_dir: Path,
    id: str,
    type: str,
    path: str,
    label: str = "",
) -> dict:
    """Register a named source in the registry.

    Returns:
        {"status": "registered", "source_id": id}  — new entry created
        {"status": "exists",     "source_id": id}  — already registered, same path
        {"status": "conflict",   "error": "..."}   — id exists with different path
    """
    sources = load_sources(session_dir)
    path_str = str(Path(path).resolve())

    for source in sources:
        if source["id"] == id:
            existing = str(Path(source["path"]).resolve()) if source.get("path") else ""
            if existing == path_str:
                return {"status": "exists", "source_id": id}
            return {
                "status": "conflict",
                "error": (
                    f"Source '{id}' already registered at '{source['path']}'. "
                    f"Use a different id or update the registry manually."
                ),
            }

    sources.append({
        "id": id,
        "type": type,
        "path": path_str,
        "label": label or id,
        "registered": datetime.now().isoformat(),
    })
    save_sources(session_dir, sources)
    return {"status": "registered", "source_id": id}


def get_source(session_dir: Path, source_id: str) -> dict | None:
    """Get a registered source by ID. Returns None if not found."""
    for source in load_sources(session_dir):
        if source["id"] == source_id:
            return source
    return None


# === URI construction ===


def build_doc_uri(source_id: str, rel_path: str, fragment: str | None = None) -> str:
    """Build a logical doc:// URI.

    Result: doc://{source_id}/{rel_path}#{fragment}
    """
    rel_path = rel_path.replace("\\", "/")
    uri = f"doc://{source_id}/{rel_path}"
    if fragment:
        uri += f"#{fragment}"
    return uri


def build_chatgpt_uri(source_id: str, conv_id: str) -> str:
    """Build a logical chatgpt:// URI.

    Result: chatgpt://{source_id}/{conv_id}
    """
    return f"chatgpt://{source_id}/{conv_id}"


def rewrite_doc_uri(uri: str, source_id: str) -> str:
    """Rewrite a legacy doc://{path} URI to doc://{source_id}/{path}.

    Idempotent: if the URI already starts with doc://{source_id}/, returns unchanged.
    Non-doc:// URIs are returned unchanged.
    """
    if not uri or not uri.startswith("doc://"):
        return uri
    rest = uri[len("doc://"):]
    # Already logical if it starts with source_id/
    if rest.startswith(f"{source_id}/"):
        return uri
    return f"doc://{source_id}/{rest}"


# === URI resolution ===


def resolve_uri(uri: str, session_dir: Path) -> dict | None:
    """Resolve a logical URI to its physical location.

    Supports:
        doc://{source_id}/{rel_path}#{fragment}
        chatgpt://{source_id}/{conv_id}

    Returns dict with keys:
        source_id, source_type, physical_path (Path), relative_ref (str), fragment (str|None)
    Returns None if the source is not registered or the URI scheme is unsupported.
    """
    if not uri:
        return None

    fragment = None
    if "#" in uri:
        uri, fragment = uri.rsplit("#", 1)

    if uri.startswith("doc://"):
        scheme = "doc"
        rest = uri[len("doc://"):]
    elif uri.startswith("chatgpt://"):
        scheme = "chatgpt"
        rest = uri[len("chatgpt://"):]
    else:
        return None

    parts = rest.split("/", 1)
    if len(parts) < 2:
        return None
    source_id, relative_ref = parts[0], parts[1]

    source = get_source(session_dir, source_id)
    if not source:
        return None

    physical_base = Path(source["path"])
    physical_path = physical_base / relative_ref if scheme == "doc" else physical_base

    return {
        "source_id": source_id,
        "source_type": source["type"],
        "physical_path": physical_path,
        "relative_ref": relative_ref,
        "fragment": fragment,
    }
