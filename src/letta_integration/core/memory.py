"""Persistent SQLite memory engine implementing Letta's hierarchical memory architecture."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from letta_integration.core.models import (
    AgentState,
    ArchivalPassage,
    MemoryBlock,
    Message,
)


class LettaMemoryStore:
    """Manages persistent SQLite storage for Letta agents, core memory blocks, archival passages, and recall logs."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    model TEXT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    system_prompt TEXT,
                    tools_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS core_memory_blocks (
                    agent_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value TEXT NOT NULL,
                    char_limit INTEGER NOT NULL,
                    read_only INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (agent_id, label),
                    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS archival_passages (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    name TEXT,
                    tool_calls_json TEXT,
                    tool_call_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # Create indexes for fast lookup
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_archival_agent ON archival_passages(agent_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id, created_at)")

    # ---------------------------------------------------------
    # Agent State Management
    # ---------------------------------------------------------

    def create_agent(self, agent: AgentState) -> AgentState:
        """Create or register a new agent with initial core memory blocks."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO agents (
                    id, name, description, model, embedding_model, system_prompt, tools_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent.id,
                    agent.name,
                    agent.description,
                    agent.model,
                    agent.embedding_model,
                    agent.system_prompt,
                    json.dumps(agent.tools),
                    agent.created_at,
                    agent.updated_at,
                ),
            )
            for block in agent.core_memory.values():
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO core_memory_blocks (
                        agent_id, label, value, char_limit, read_only
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        agent.id,
                        block.label,
                        block.value,
                        block.limit,
                        1 if block.read_only else 0,
                    ),
                )
        return self.get_agent(agent.id) or agent

    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Retrieve an agent by its ID or Name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (agent_id, agent_id))
        row = cursor.fetchone()
        if not row:
            return None

        # Fetch blocks
        cursor.execute("SELECT * FROM core_memory_blocks WHERE agent_id = ?", (row["id"],))
        blocks = {}
        for b_row in cursor.fetchall():
            blocks[b_row["label"]] = MemoryBlock(
                label=b_row["label"],
                value=b_row["value"],
                limit=b_row["char_limit"],
                read_only=bool(b_row["read_only"]),
            )

        return AgentState(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            model=row["model"],
            embedding_model=row["embedding_model"],
            system_prompt=row["system_prompt"],
            tools=json.loads(row["tools_json"]),
            core_memory=blocks,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_agents(self) -> List[AgentState]:
        """List all agents stored in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM agents ORDER BY created_at ASC")
        rows = cursor.fetchall()
        agents = []
        for r in rows:
            agent = self.get_agent(r["id"])
            if agent:
                agents.append(agent)
        return agents

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and cascade delete all associated data."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            return cursor.rowcount > 0

    def get_active_agent_id(self) -> Optional[str]:
        """Get the ID of the currently active agent."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'active_agent_id'")
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_active_agent_id(self, agent_id: str) -> None:
        """Set the ID of the currently active agent."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('active_agent_id', ?)",
                (agent_id,),
            )

    # ---------------------------------------------------------
    # Core Memory Operations
    # ---------------------------------------------------------

    def get_block(self, agent_id: str, label: str) -> Optional[MemoryBlock]:
        """Retrieve a specific core memory block."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM core_memory_blocks WHERE agent_id = ? AND label = ?",
            (agent_id, label),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return MemoryBlock(
            label=row["label"],
            value=row["value"],
            limit=row["char_limit"],
            read_only=bool(row["read_only"]),
        )

    def set_block(self, agent_id: str, label: str, value: str, limit: int = 4000) -> MemoryBlock:
        """Set or update the content of a core memory block."""
        if len(value) > limit:
            raise ValueError(f"Content length ({len(value)}) exceeds character limit ({limit})")
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO core_memory_blocks (
                    agent_id, label, value, char_limit, read_only
                ) VALUES (?, ?, ?, ?, 0)
                """,
                (agent_id, label, value, limit),
            )
        return MemoryBlock(label=label, value=value, limit=limit, read_only=False)

    def append_block(self, agent_id: str, label: str, content: str) -> Tuple[MemoryBlock, str]:
        """Append content to a core memory block."""
        block = self.get_block(agent_id, label)
        if not block:
            block = MemoryBlock(label=label, value="", limit=4000)

        if block.read_only:
            raise PermissionError(f"Block '{label}' is read-only and cannot be modified.")

        separator = "\n" if block.value and not block.value.endswith("\n") else ""
        new_val = f"{block.value}{separator}{content}".strip()
        if len(new_val) > block.limit:
            raise ValueError(
                f"Append rejected: resulting length ({len(new_val)}) would exceed limit ({block.limit})."
            )

        with self.conn:
            self.conn.execute(
                "UPDATE core_memory_blocks SET value = ? WHERE agent_id = ? AND label = ?",
                (new_val, agent_id, label),
            )
        block.value = new_val
        return block, f"Successfully appended to core memory block '{label}'."

    def replace_block(self, agent_id: str, label: str, old_content: str, new_content: str) -> Tuple[MemoryBlock, str]:
        """Replace a substring inside a core memory block."""
        block = self.get_block(agent_id, label)
        if not block:
            raise KeyError(f"Core memory block '{label}' not found.")

        if block.read_only:
            raise PermissionError(f"Block '{label}' is read-only and cannot be modified.")

        if old_content not in block.value:
            raise ValueError(f"Substring '{old_content}' not found in core memory block '{label}'.")

        updated_val = block.value.replace(old_content, new_content, 1)
        if len(updated_val) > block.limit:
            raise ValueError(
                f"Replacement rejected: resulting length ({len(updated_val)}) would exceed limit ({block.limit})."
            )

        with self.conn:
            self.conn.execute(
                "UPDATE core_memory_blocks SET value = ? WHERE agent_id = ? AND label = ?",
                (updated_val, agent_id, label),
            )
        block.value = updated_val
        return block, f"Successfully updated core memory block '{label}'."

    def list_blocks(self, agent_id: str) -> Dict[str, MemoryBlock]:
        """List all core memory blocks for an agent."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM core_memory_blocks WHERE agent_id = ?", (agent_id,))
        blocks = {}
        for row in cursor.fetchall():
            blocks[row["label"]] = MemoryBlock(
                label=row["label"],
                value=row["value"],
                limit=row["char_limit"],
                read_only=bool(row["read_only"]),
            )
        return blocks

    # ---------------------------------------------------------
    # Archival Memory Operations
    # ---------------------------------------------------------

    def insert_passage(self, agent_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> ArchivalPassage:
        """Insert a long-term memory passage into archival memory."""
        passage_id = str(uuid.uuid4())
        passage = ArchivalPassage(
            id=passage_id,
            text=text.strip(),
            metadata=metadata or {},
        )
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO archival_passages (
                    id, agent_id, text, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    passage.id,
                    agent_id,
                    passage.text,
                    json.dumps(passage.metadata),
                    passage.created_at,
                ),
            )
        return passage

    def search_passages(self, agent_id: str, query: str, limit: int = 5) -> List[ArchivalPassage]:
        """Perform text/token BM25-style relevance search across archival passages."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM archival_passages WHERE agent_id = ?", (agent_id,))
        rows = cursor.fetchall()
        if not rows:
            return []

        # Tokenize query
        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return [
                ArchivalPassage(
                    id=r["id"],
                    text=r["text"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                    created_at=r["created_at"],
                )
                for r in rows[:limit]
            ]

        scored_passages: List[Tuple[float, sqlite3.Row]] = []
        for r in rows:
            passage_text = r["text"].lower()
            passage_tokens = re.findall(r"\w+", passage_text)
            if not passage_tokens:
                continue

            # Calculate token overlap score with term frequency boost
            score = 0.0
            total_tokens = len(passage_tokens)
            for qt in query_tokens:
                count = passage_tokens.count(qt)
                if count > 0:
                    tf = count / total_tokens
                    score += (1.0 + math.log(count + 1)) * (1.0 / (1.0 + math.exp(-tf)))

            # Exact phrase match bonus
            if query.lower() in passage_text:
                score += 5.0

            if score > 0:
                scored_passages.append((score, r))

        # Sort descending by relevance score
        scored_passages.sort(key=lambda x: x[0], reverse=True)

        results = []
        for _, r in scored_passages[:limit]:
            results.append(
                ArchivalPassage(
                    id=r["id"],
                    text=r["text"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                    created_at=r["created_at"],
                )
            )
        return results

    def list_passages(self, agent_id: str, limit: int = 50) -> List[ArchivalPassage]:
        """List archival passages sorted by creation time."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM archival_passages WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        )
        return [
            ArchivalPassage(
                id=r["id"],
                text=r["text"],
                metadata=json.loads(r["metadata_json"] or "{}"),
                created_at=r["created_at"],
            )
            for r in cursor.fetchall()
        ]

    def delete_passage(self, agent_id: str, passage_id: str) -> bool:
        """Delete an archival passage."""
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM archival_passages WHERE id = ? AND agent_id = ?",
                (passage_id, agent_id),
            )
            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # Recall Memory (Message History) Operations
    # ---------------------------------------------------------

    def save_message(self, agent_id: str, message: Message) -> Message:
        """Save a message to recall memory."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO messages (
                    id, agent_id, role, content, name, tool_calls_json, tool_call_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    agent_id,
                    message.role,
                    message.content,
                    message.name,
                    json.dumps(message.tool_calls) if message.tool_calls else None,
                    message.tool_call_id,
                    message.created_at,
                ),
            )
        return message

    def get_messages(self, agent_id: str, limit: int = 20) -> List[Message]:
        """Fetch the most recent recall messages for an agent in chronological order."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM (
                SELECT rowid, * FROM messages WHERE agent_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?
            ) ORDER BY created_at ASC, rowid ASC
            """,
            (agent_id, limit),
        )
        messages = []
        for r in cursor.fetchall():
            messages.append(
                Message(
                    id=r["id"],
                    role=r["role"],
                    content=r["content"],
                    name=r["name"],
                    tool_calls=json.loads(r["tool_calls_json"]) if r["tool_calls_json"] else None,
                    tool_call_id=r["tool_call_id"],
                    created_at=r["created_at"],
                )
            )
        return messages

    def search_messages(self, agent_id: str, query: str, limit: int = 5) -> List[Message]:
        """Search recall conversation logs."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM messages 
            WHERE agent_id = ? AND content LIKE ? 
            ORDER BY created_at DESC LIMIT ?
            """,
            (agent_id, f"%{query}%", limit),
        )
        return [
            Message(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                name=r["name"],
                tool_calls=json.loads(r["tool_calls_json"]) if r["tool_calls_json"] else None,
                tool_call_id=r["tool_call_id"],
                created_at=r["created_at"],
            )
            for r in cursor.fetchall()
        ]

    def reset_messages(self, agent_id: str) -> int:
        """Reset conversation message history while preserving Core and Archival memory."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM messages WHERE agent_id = ?", (agent_id,))
            return cursor.rowcount

    def close(self) -> None:
        """Close SQLite database connection."""
        self.conn.close()
