"""Embedding layer: configurable vector embeddings for semantic search.

Supports two backends:
- Ollama (default): local models via HTTP API. Free, GPU-accelerated.
  Set OI_EMBED_MODEL to any Ollama model name (default: nomic-embed-text).
  Set OI_OLLAMA_URL to override Ollama endpoint (default: http://127.0.0.1:11434).
- litellm: any cloud provider (OpenAI, Cohere, etc).
  Prefix model with "litellm/" to use, e.g. OI_EMBED_MODEL=litellm/text-embedding-3-small.

Storage: embeddings.json alongside knowledge.yaml.
Graceful degradation: if embedding fails, search falls back to keyword-only.
"""

import json
import math
import os
from pathlib import Path

import requests

DEFAULT_EMBED_MODEL = os.environ.get("OI_EMBED_MODEL", "nomic-embed-text")
OLLAMA_URL = os.environ.get("OI_OLLAMA_URL", "http://127.0.0.1:11434")

# Cache file name
EMBEDDINGS_FILE = "embeddings.json"


def get_embedding(text: str, model: str = None) -> list[float] | None:
    """Get embedding vector for text.

    Routes to Ollama (default) or litellm (if model starts with "litellm/").
    Returns None on any failure.
    """
    model = model or DEFAULT_EMBED_MODEL
    try:
        if model.startswith("litellm/"):
            return _embed_litellm(text, model[len("litellm/"):])
        return _embed_ollama(text, model)
    except Exception:
        return None


def _embed_ollama(text: str, model: str) -> list[float] | None:
    """Get embedding via Ollama HTTP API."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def _embed_litellm(text: str, model: str) -> list[float] | None:
    """Get embedding via litellm (cloud providers)."""
    from litellm import embedding
    response = embedding(model=model, input=[text])
    return response.data[0]["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors using stdlib math."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embeddings_path(session_dir: Path) -> Path:
    return session_dir / EMBEDDINGS_FILE


def load_embeddings(session_dir: Path) -> dict:
    """Load embeddings from disk.

    Returns {"model": str, "vectors": {node_id: [float, ...]}}.
    """
    path = _embeddings_path(session_dir)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and "model" in data and "vectors" in data:
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {"model": "", "vectors": {}}


def save_embeddings(session_dir: Path, data: dict) -> None:
    """Save embeddings to disk."""
    session_dir.mkdir(parents=True, exist_ok=True)
    _embeddings_path(session_dir).write_text(json.dumps(data))


def embed_node(node: dict, model: str = None) -> list[float] | None:
    """Embed a node's summary text."""
    summary = node.get("summary", "")
    if not summary:
        return None
    return get_embedding(summary, model)


def ensure_embeddings(session_dir: Path, knowledge: dict, model: str = None) -> dict:
    """Ensure all active nodes have embeddings. Re-embeds on model change.

    Returns the embeddings dict (loaded or updated).
    """
    model = model or DEFAULT_EMBED_MODEL
    data = load_embeddings(session_dir)

    # Model changed — re-embed everything
    if data["model"] and data["model"] != model:
        data = {"model": model, "vectors": {}}

    active_ids = {
        n["id"] for n in knowledge.get("nodes", [])
        if n.get("status") != "superseded"
    }

    # Remove stale embeddings
    data["vectors"] = {k: v for k, v in data["vectors"].items() if k in active_ids}

    # Embed missing nodes
    missing = active_ids - set(data["vectors"].keys())
    if missing:
        nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
        for nid in missing:
            node = nodes_by_id.get(nid)
            if node:
                vec = embed_node(node, model)
                if vec:
                    data["vectors"][nid] = vec

        data["model"] = model
        save_embeddings(session_dir, data)

    return data


def semantic_search(
    query: str,
    session_dir: Path,
    knowledge: dict,
    model: str = None,
    top_k: int = 10,
    min_score: float = 0.3,
) -> list[dict]:
    """Find semantically similar nodes to query.

    Returns [{node_id, score}] sorted by score descending.
    Returns empty list if embeddings unavailable.
    """
    model = model or DEFAULT_EMBED_MODEL
    query_vec = get_embedding(query, model)
    if not query_vec:
        return []

    data = ensure_embeddings(session_dir, knowledge, model)
    if not data["vectors"]:
        return []

    results = []
    for nid, vec in data["vectors"].items():
        score = cosine_similarity(query_vec, vec)
        if score >= min_score:
            results.append({"node_id": nid, "score": score})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]
