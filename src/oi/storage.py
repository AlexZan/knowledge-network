"""Persistence layer using SQLite."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from .models import ConversationState, Thread, Message, Conclusion, TokenStats


DEFAULT_STATE_DIR = Path.home() / ".oi"


def get_db_path(state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    """Get the path to the SQLite database."""
    return state_dir / "oi.db"


def ensure_state_dir(state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Ensure the state directory exists."""
    state_dir.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection(state_dir: Path = DEFAULT_STATE_DIR):
    """Get a database connection with proper cleanup."""
    ensure_state_dir(state_dir)
    db_path = get_db_path(state_dir)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Initialize the database schema."""
    with get_connection(state_dir) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conclusions (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source_thread_id TEXT NOT NULL,
                created TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'open',
                conclusion_id TEXT,
                created TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS thread_context (
                thread_id TEXT NOT NULL,
                conclusion_id TEXT NOT NULL,
                PRIMARY KEY (thread_id, conclusion_id),
                FOREIGN KEY (thread_id) REFERENCES threads(id),
                FOREIGN KEY (conclusion_id) REFERENCES conclusions(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                label TEXT,
                thread_id TEXT,
                conclusion_id TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id),
                FOREIGN KEY (conclusion_id) REFERENCES conclusions(id)
            );

            CREATE TABLE IF NOT EXISTS token_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_raw INTEGER NOT NULL DEFAULT 0,
                total_compacted INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                active_thread_id TEXT
            );

            -- Initialize singleton rows if not exist
            INSERT OR IGNORE INTO token_stats (id, total_raw, total_compacted) VALUES (1, 0, 0);
            INSERT OR IGNORE INTO state (id, active_thread_id) VALUES (1, NULL);

            -- Indexes for common queries
            CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);
        """)


# --- Conclusion operations ---

def save_conclusion(conclusion: Conclusion, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Save a conclusion to the database."""
    with get_connection(state_dir) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO conclusions (id, content, source_thread_id, created)
            VALUES (?, ?, ?, ?)
        """, (conclusion.id, conclusion.content, conclusion.source_thread_id,
              conclusion.created.isoformat()))


def load_conclusion(conclusion_id: str, state_dir: Path = DEFAULT_STATE_DIR) -> Conclusion | None:
    """Load a single conclusion by ID."""
    with get_connection(state_dir) as conn:
        row = conn.execute(
            "SELECT * FROM conclusions WHERE id = ?", (conclusion_id,)
        ).fetchone()
        if row:
            return Conclusion(
                id=row["id"],
                content=row["content"],
                source_thread_id=row["source_thread_id"],
                created=datetime.fromisoformat(row["created"])
            )
    return None


def load_all_conclusions(state_dir: Path = DEFAULT_STATE_DIR) -> list[Conclusion]:
    """Load all conclusions."""
    with get_connection(state_dir) as conn:
        rows = conn.execute("SELECT * FROM conclusions ORDER BY created").fetchall()
        return [
            Conclusion(
                id=row["id"],
                content=row["content"],
                source_thread_id=row["source_thread_id"],
                created=datetime.fromisoformat(row["created"])
            )
            for row in rows
        ]


# --- Thread operations ---

def save_thread(thread: Thread, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Save a thread and its messages to the database."""
    with get_connection(state_dir) as conn:
        # Save thread
        conn.execute("""
            INSERT OR REPLACE INTO threads (id, status, conclusion_id, created)
            VALUES (?, ?, ?, ?)
        """, (thread.id, thread.status, thread.conclusion_id,
              thread.messages[0].timestamp.isoformat() if thread.messages else datetime.now().isoformat()))

        # Save context conclusion links
        conn.execute("DELETE FROM thread_context WHERE thread_id = ?", (thread.id,))
        for conclusion_id in thread.context_conclusion_ids:
            conn.execute("""
                INSERT OR IGNORE INTO thread_context (thread_id, conclusion_id)
                VALUES (?, ?)
            """, (thread.id, conclusion_id))

        # Save messages (delete and re-insert to handle updates)
        conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread.id,))
        for msg in thread.messages:
            conn.execute("""
                INSERT INTO messages (thread_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (thread.id, msg.role, msg.content, msg.timestamp.isoformat()))


def load_thread(thread_id: str, state_dir: Path = DEFAULT_STATE_DIR) -> Thread | None:
    """Load a single thread by ID with all its messages."""
    with get_connection(state_dir) as conn:
        # Load thread
        thread_row = conn.execute(
            "SELECT * FROM threads WHERE id = ?", (thread_id,)
        ).fetchone()
        if not thread_row:
            return None

        # Load messages
        msg_rows = conn.execute(
            "SELECT * FROM messages WHERE thread_id = ? ORDER BY timestamp",
            (thread_id,)
        ).fetchall()
        messages = [
            Message(
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"])
            )
            for row in msg_rows
        ]

        # Load context conclusion IDs
        context_rows = conn.execute(
            "SELECT conclusion_id FROM thread_context WHERE thread_id = ?",
            (thread_id,)
        ).fetchall()
        context_ids = [row["conclusion_id"] for row in context_rows]

        return Thread(
            id=thread_row["id"],
            messages=messages,
            context_conclusion_ids=context_ids,
            status=thread_row["status"],
            conclusion_id=thread_row["conclusion_id"]
        )


# --- History operations ---

def add_history_entry(
    entry_type: str,
    thread_id: str | None = None,
    conclusion_id: str | None = None,
    label: str | None = None,
    state_dir: Path = DEFAULT_STATE_DIR
) -> None:
    """Add an entry to the history log."""
    with get_connection(state_dir) as conn:
        conn.execute("""
            INSERT INTO history (type, label, thread_id, conclusion_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (entry_type, label, thread_id, conclusion_id, datetime.now().isoformat()))


def load_recent_history(limit: int = 10, state_dir: Path = DEFAULT_STATE_DIR) -> list[dict]:
    """Load recent history entries (newest first)."""
    with get_connection(state_dir) as conn:
        rows = conn.execute("""
            SELECT * FROM history ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]


# --- Token stats operations ---

def get_token_stats(state_dir: Path = DEFAULT_STATE_DIR) -> TokenStats:
    """Get current token statistics."""
    with get_connection(state_dir) as conn:
        row = conn.execute("SELECT * FROM token_stats WHERE id = 1").fetchone()
        return TokenStats(
            total_raw=row["total_raw"],
            total_compacted=row["total_compacted"]
        )


def update_token_stats(raw: int, compacted: int, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Add to token statistics."""
    with get_connection(state_dir) as conn:
        conn.execute("""
            UPDATE token_stats
            SET total_raw = total_raw + ?, total_compacted = total_compacted + ?
            WHERE id = 1
        """, (raw, compacted))


# --- Active thread state ---

def get_active_thread_id(state_dir: Path = DEFAULT_STATE_DIR) -> str | None:
    """Get the active thread ID."""
    with get_connection(state_dir) as conn:
        row = conn.execute("SELECT active_thread_id FROM state WHERE id = 1").fetchone()
        return row["active_thread_id"] if row else None


def set_active_thread_id(thread_id: str | None, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Set the active thread ID."""
    with get_connection(state_dir) as conn:
        conn.execute(
            "UPDATE state SET active_thread_id = ? WHERE id = 1",
            (thread_id,)
        )


# --- High-level state operations (for compatibility) ---

def save_state(state: ConversationState, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Save conversation state to database."""
    init_db(state_dir)

    # Save threads
    for thread in state.threads:
        save_thread(thread, state_dir)

    # Save conclusions
    for conclusion in state.conclusions:
        save_conclusion(conclusion, state_dir)

    # Update token stats (replace, not add)
    with get_connection(state_dir) as conn:
        conn.execute("""
            UPDATE token_stats
            SET total_raw = ?, total_compacted = ?
            WHERE id = 1
        """, (state.token_stats.total_raw, state.token_stats.total_compacted))

    # Set active thread
    set_active_thread_id(state.active_thread_id, state_dir)


def load_state(state_dir: Path = DEFAULT_STATE_DIR) -> ConversationState:
    """Load conversation state from database.

    Only loads conclusions and the active thread (if any).
    """
    init_db(state_dir)

    # Load conclusions
    conclusions = load_all_conclusions(state_dir)

    # Load token stats
    token_stats = get_token_stats(state_dir)

    # Load active thread
    active_thread_id = get_active_thread_id(state_dir)
    threads = []
    if active_thread_id:
        active_thread = load_thread(active_thread_id, state_dir)
        if active_thread:
            threads.append(active_thread)

    return ConversationState(
        threads=threads,
        conclusions=conclusions,
        active_thread_id=active_thread_id,
        token_stats=token_stats
    )
