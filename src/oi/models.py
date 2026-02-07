"""Data models for conversation state."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class Artifact(BaseModel):
    """A knowledge artifact created from conversation exchanges.

    Types are defined in schemas/artifact_types.yaml and can be customized.
    Default types: effort, fact, event

    When an effort is resolved, the resolution field captures the outcome.

    States:
    - open: Actively working on this
    - resolved: Concluded with a resolution
    - archived: Inactive after period of no activity (can be reopened)
    """
    id: str
    artifact_type: str  # Dynamic - loaded from schema config
    summary: str
    status: Literal["open", "resolved", "archived"] | None = None  # For types with has_status
    resolution: str | None = None  # What was decided/concluded (for resolved)
    parent_id: str | None = None  # ID of parent artifact (for hierarchy)
    related_to: str | None = None  # ID of related artifact
    tags: list[str] = Field(default_factory=list)
    ref_count: int = 0  # For expiration: how often referenced
    expires: bool = False  # Whether this can expire
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)  # Last activity


class ConversationState(BaseModel):
    """Complete state of a conversation.

    Raw chat history is stored separately in chatlog.jsonl.
    This state contains only the extracted artifacts.
    """
    artifacts: list[Artifact] = Field(default_factory=list)

    def get_open_efforts(self) -> list[Artifact]:
        """Get all open efforts (actively working)."""
        return [a for a in self.artifacts if a.artifact_type == "effort" and a.status == "open"]

    def get_resolved_efforts(self) -> list[Artifact]:
        """Get all resolved efforts (completed work with conclusions)."""
        return [a for a in self.artifacts if a.artifact_type == "effort" and a.status == "resolved"]

    def get_archived_efforts(self) -> list[Artifact]:
        """Get all archived efforts (inactive, can be reopened)."""
        return [a for a in self.artifacts if a.artifact_type == "effort" and a.status == "archived"]

    def get_recent_efforts(self, limit: int = 5) -> list[Artifact]:
        """Get most recently updated efforts (any status), sorted by updated time."""
        efforts = [a for a in self.artifacts if a.artifact_type == "effort"]
        return sorted(efforts, key=lambda a: a.updated, reverse=True)[:limit]

    def get_facts(self) -> list[Artifact]:
        """Get all fact artifacts."""
        return [a for a in self.artifacts if a.artifact_type == "fact"]


# Legacy models kept for migration compatibility
# TODO: Remove after full migration

class Message(BaseModel):
    """A single message in a conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Thread(BaseModel):
    """LEGACY: A conversation thread that may be open or concluded."""
    id: str
    messages: list[Message] = Field(default_factory=list)
    context_conclusion_ids: list[str] = Field(default_factory=list)
    status: Literal["open", "concluded"] = "open"
    conclusion_id: str | None = None


class Conclusion(BaseModel):
    """LEGACY: A compacted summary of a resolved thread."""
    id: str
    content: str
    source_thread_id: str
    created: datetime = Field(default_factory=datetime.now)


class TokenStats(BaseModel):
    """Token usage statistics."""
    total_raw: int = 0
    total_compacted: int = 0

    @property
    def savings_percent(self) -> float:
        if self.total_raw == 0:
            return 0.0
        return (1 - self.total_compacted / self.total_raw) * 100


# Full legacy state for backwards compatibility during migration
class LegacyConversationState(BaseModel):
    """LEGACY: Full state including threads/conclusions. Use ConversationState instead."""
    threads: list[Thread] = Field(default_factory=list)
    conclusions: list[Conclusion] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    active_thread_id: str | None = None
    token_stats: TokenStats = Field(default_factory=TokenStats)

    def get_active_thread(self) -> Thread | None:
        if not self.active_thread_id:
            return None
        for thread in self.threads:
            if thread.id == self.active_thread_id:
                return thread
        return None

    def get_active_conclusions(self) -> list[Conclusion]:
        return self.conclusions
