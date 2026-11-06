"""Data models for Letta agent state, memory blocks, passages, and messages."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryBlock(BaseModel):
    """An editable in-context core memory block (e.g., 'persona', 'human')."""

    label: str = Field(..., description="Unique label identifying the memory block (e.g., 'human', 'persona')")
    value: str = Field("", description="The text content stored within the block")
    limit: int = Field(4000, description="Maximum character limit for the block")
    read_only: bool = Field(False, description="Whether this block is protected from agent self-editing")


class ArchivalPassage(BaseModel):
    """A long-term memory entry stored in out-of-context archival memory."""

    id: str = Field(..., description="Unique passage identifier")
    text: str = Field(..., description="The textual passage content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata attached to the passage")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Timestamp of creation",
    )


class Message(BaseModel):
    """A single conversational or system message in recall memory."""

    id: str = Field(..., description="Unique message ID")
    role: str = Field(..., description="Role: 'user', 'assistant', 'system', 'tool'")
    content: Optional[str] = Field(None, description="Textual content of the message")
    name: Optional[str] = Field(None, description="Optional name of the tool or sender")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls triggered in this turn")
    tool_call_id: Optional[str] = Field(None, description="Tool call reference ID if this is a tool result")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Timestamp of creation",
    )


class AgentState(BaseModel):
    """Full representation of a Letta stateful agent."""

    id: str = Field(..., description="Unique agent identifier (UUID or slug)")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field("", description="Description of the agent's purpose")
    model: str = Field("gemini-2.5-flash", description="Model used for agent reasoning")
    embedding_model: str = Field("text-embedding-004", description="Model used for semantic indexing")
    core_memory: Dict[str, MemoryBlock] = Field(
        default_factory=dict, description="Active in-context memory blocks"
    )
    tools: List[str] = Field(
        default_factory=lambda: [
            "core_memory_append",
            "core_memory_replace",
            "archival_memory_insert",
            "archival_memory_search",
            "conversation_search",
        ],
        description="List of tools attached to the agent",
    )
    system_prompt: Optional[str] = Field(None, description="Base system instructions")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class AgentResponse(BaseModel):
    """Structured response from sending a message to a Letta agent."""

    agent_id: str
    messages: List[Message] = Field(default_factory=list)
    inner_thoughts: List[str] = Field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class LettaConfig(BaseModel):
    """Configuration settings for the Letta integration."""

    mode: str = Field("auto", description="Operating mode: 'auto', 'remote', or 'embedded'")
    base_url: str = Field("http://localhost:8283", description="Letta server URL")
    api_key: Optional[str] = Field(None, description="Letta server/cloud API key")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API Key for embedded execution")
    gemini_model: str = Field("gemini-2.5-flash", description="Gemini model for embedded execution")
    storage_path: str = Field("./data/letta_storage.db", description="Path to local persistent SQLite store")
    default_agent_name: str = Field("Antigravity-Letta-Partner", description="Default agent identifier")
