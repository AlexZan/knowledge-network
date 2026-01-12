"""Data models for conversation state."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class Message(BaseModel):
    """A single message in a conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Thread(BaseModel):
    """A conversation thread that may be open or concluded."""
    id: str
    messages: list[Message] = Field(default_factory=list)
    context_conclusion_ids: list[str] = Field(default_factory=list)  # Conclusions that provide context
    status: Literal["open", "concluded"] = "open"
    conclusion_id: str | None = None


class Conclusion(BaseModel):
    """A compacted summary of a resolved thread."""
    id: str
    content: str
    source_thread_id: str
    created: datetime = Field(default_factory=datetime.now)


class Artifact(BaseModel):
    """A knowledge artifact created from conversation exchanges.

    Types:
    - effort: Goal-oriented work (open or resolved)
    - conclusion: Resolution/knowledge from an effort
    - fact: Simple Q&A, public knowledge (can expire)
    - event: Casual exchange, context that might matter (expires fast)
    """
    id: str
    artifact_type: Literal["effort", "conclusion", "fact", "event"]
    summary: str
    status: Literal["open", "resolved"] | None = None  # For efforts
    related_to: str | None = None  # ID of related artifact
    tags: list[str] = Field(default_factory=list)
    ref_count: int = 0  # For expiration: how often referenced
    expires: bool = False  # Whether this can expire
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


class ConversationState(BaseModel):
    """Complete state of a conversation."""
    threads: list[Thread] = Field(default_factory=list)
    conclusions: list[Conclusion] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)  # New artifact system
    active_thread_id: str | None = None
    token_stats: TokenStats = Field(default_factory=TokenStats)

    def get_active_thread(self) -> Thread | None:
        """Get the currently active thread."""
        if not self.active_thread_id:
            return None
        for thread in self.threads:
            if thread.id == self.active_thread_id:
                return thread
        return None

    def get_active_conclusions(self) -> list[Conclusion]:
        """Get all active conclusions."""
        return self.conclusions
