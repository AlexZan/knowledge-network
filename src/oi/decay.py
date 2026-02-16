"""Salience decay: auto-collapse expanded efforts after N turns without reference.

Keeps orchestrator clean by isolating decay logic here.
"""

from pathlib import Path

from .state import (
    _load_expanded_state, _load_manifest, _save_expanded,
    _load_summary_references, _save_summary_references,
)
from .tools import collapse_effort

DECAY_THRESHOLD = 3
SUMMARY_EVICTION_THRESHOLD = 20
AMBIENT_WINDOW = 10
MIN_KEYWORD_OVERLAP = 2

STOPWORDS = frozenset({
    "the", "a", "an", "is", "was", "were", "been", "be", "are", "am",
    "has", "have", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "and", "but", "or", "nor", "not", "no", "so", "yet",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "than", "too", "very",
    "this", "that", "these", "those", "its", "it",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who", "whom",
    "just", "about", "also", "now", "still", "even",
})


def extract_keywords(summary: str) -> set[str]:
    """Extract salient keywords from effort summary for reference detection.

    Splits on whitespace, lowercases, strips punctuation, filters stopwords
    and short words (< 3 chars).
    """
    if not summary:
        return set()
    words = set()
    for word in summary.lower().split():
        word = word.strip(".,;:!?\"'()-[]{}/*#@&^%$`~<>|\\+_=")
        if len(word) >= 3 and word not in STOPWORDS:
            words.add(word)
    return words


def is_referenced(message: str, effort_id: str, keywords: set[str]) -> bool:
    """Check if a message references an expanded effort.

    Two detection methods:
    1. Direct effort ID match (with or without hyphens)
    2. Keyword overlap >= MIN_KEYWORD_OVERLAP
    """
    msg_lower = message.lower()

    # Direct ID mention (kebab-case or space-separated)
    if effort_id.lower() in msg_lower or effort_id.replace("-", " ") in msg_lower:
        return True

    # Keyword overlap
    msg_words = set()
    for word in msg_lower.split():
        word = word.strip(".,;:!?\"'()-[]{}/*#@&^%$`~<>|\\+_=")
        if word:
            msg_words.add(word)
    overlap = keywords & msg_words
    return len(overlap) >= MIN_KEYWORD_OVERLAP


def check_decay(session_dir: Path, current_turn: int, user_message: str, assistant_response: str) -> list[str]:
    """Check all expanded efforts for decay. Returns list of auto-collapsed effort IDs.

    For each expanded effort:
    1. Check if user_message or assistant_response references it
    2. If yes: update last_referenced_turn
    3. If no: check if turns_since >= DECAY_THRESHOLD
    4. If decayed: call collapse_effort, collect ID
    """
    expanded_state = _load_expanded_state(session_dir)
    expanded_ids = set(expanded_state.get("expanded", []))

    if not expanded_ids:
        return []

    manifest = _load_manifest(session_dir)
    lrt = expanded_state.get("last_referenced_turn", {})
    decayed = []

    for effort_id in list(expanded_ids):
        # Get summary for keyword extraction
        summary = ""
        for e in manifest.get("efforts", []):
            if e["id"] == effort_id:
                summary = e.get("summary", "") or ""
                break

        keywords = extract_keywords(summary)

        # Check if referenced in this turn
        referenced = (
            is_referenced(user_message, effort_id, keywords)
            or is_referenced(assistant_response, effort_id, keywords)
        )

        if referenced:
            lrt[effort_id] = current_turn
        else:
            last_ref = lrt.get(effort_id, 0)
            turns_since = current_turn - last_ref
            if turns_since >= DECAY_THRESHOLD:
                collapse_effort(session_dir, effort_id)
                expanded_ids.discard(effort_id)
                lrt.pop(effort_id, None)
                decayed.append(effort_id)

    # Save updated state (only if we still have expanded efforts or had changes)
    if expanded_ids or decayed:
        _save_expanded(session_dir, expanded_ids, last_referenced_turn=lrt)

    return decayed


def update_summary_references(session_dir: Path, current_turn: int,
                              user_message: str, assistant_response: str):
    """Update summary_last_referenced_turn for all concluded efforts.

    For each concluded effort:
    1. Extract keywords from summary
    2. Check if user_message or assistant_response references it
    3. If yes: set summary_last_referenced_turn[effort_id] = current_turn
    """
    manifest = _load_manifest(session_dir)
    concluded = [e for e in manifest.get("efforts", []) if e.get("status") == "concluded"]

    if not concluded:
        return

    refs = _load_summary_references(session_dir)

    for effort in concluded:
        eid = effort["id"]
        summary = effort.get("summary", "") or ""
        keywords = extract_keywords(summary)

        referenced = (
            is_referenced(user_message, eid, keywords)
            or is_referenced(assistant_response, eid, keywords)
        )

        if referenced:
            refs[eid] = current_turn
        elif eid not in refs:
            # First time seeing this effort — initialize with current turn (grace period)
            refs[eid] = current_turn

    _save_summary_references(session_dir, refs)


def get_evicted_summary_ids(session_dir: Path, current_turn: int) -> set[str]:
    """Return set of concluded effort IDs whose summaries should be excluded from working memory.

    An effort is evicted if:
    - It has a summary_last_referenced_turn entry AND
    - (current_turn - last_ref) >= SUMMARY_EVICTION_THRESHOLD

    Efforts WITHOUT an entry are NOT evicted (grace period).
    """
    refs = _load_summary_references(session_dir)
    evicted = set()

    for eid, last_ref in refs.items():
        if current_turn - last_ref >= SUMMARY_EVICTION_THRESHOLD:
            evicted.add(eid)

    return evicted
