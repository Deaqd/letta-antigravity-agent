"""Unified client adapter supporting official remote Letta servers and local embedded execution."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from letta_integration.core.engine import EmbeddedLettaEngine
from letta_integration.core.memory import LettaMemoryStore
from letta_integration.core.models import (
    AgentResponse,
    AgentState,
    ArchivalPassage,
    LettaConfig,
    MemoryBlock,
    Message,
)


class LettaUnifiedClient:
    """Provides a seamless, fault-tolerant interface for Letta operations in Antigravity."""

    def __init__(self, config: Optional[LettaConfig] = None):
        self.config = config or self._load_config_from_env()
        self.mode = self._resolve_mode(self.config)
        self.store = LettaMemoryStore(self.config.storage_path)
        self.engine = EmbeddedLettaEngine(
            self.store,
            gemini_api_key=self.config.gemini_api_key,
            default_model=self.config.gemini_model,
        )
        self._remote_client = None

        # Ensure default agent exists in local store
        self._ensure_default_agent()

    @classmethod
    def _load_config_from_env(cls) -> LettaConfig:
        """Load configuration from environment variables with sensible defaults."""
        return LettaConfig(
            mode=os.environ.get("LETTA_MODE", "auto"),
            base_url=os.environ.get("LETTA_BASE_URL", "http://localhost:8283"),
            api_key=os.environ.get("LETTA_API_KEY"),
            gemini_api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            storage_path=os.environ.get("LETTA_STORAGE_PATH", "./data/letta_storage.db"),
            default_agent_name=os.environ.get("LETTA_DEFAULT_AGENT", "Antigravity-Letta-Partner"),
        )

    def _resolve_mode(self, config: LettaConfig) -> str:
        """Resolve whether to run in 'remote' or 'embedded' mode."""
        requested = config.mode.lower()
        if requested == "remote":
            return "remote"
        if requested == "embedded":
            return "embedded"

        # In 'auto' mode, check if a remote Letta server is configured & reachable
        if config.api_key or config.base_url != "http://localhost:8283":
            try:
                import requests
                health_url = f"{config.base_url.rstrip('/')}/v1/health"
                resp = requests.get(health_url, timeout=1.5)
                if resp.status_code == 200:
                    return "remote"
            except Exception:
                pass

        # Default to high-fidelity embedded mode
        return "embedded"

    def _get_remote_client(self):
        """Initialize official letta-client if in remote mode."""
        if self._remote_client is None:
            try:
                from letta_client import Letta
                self._remote_client = Letta(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                )
            except Exception as e:
                # If remote fails, fallback gracefully to embedded mode
                self.mode = "embedded"
        return self._remote_client

    def _ensure_default_agent(self) -> AgentState:
        """Ensure that a primary stateful Letta agent exists in the memory store."""
        active_id = self.store.get_active_agent_id()
        if active_id:
            agent = self.store.get_agent(active_id)
            if agent:
                return agent

        # Check by default name
        agent = self.store.get_agent(self.config.default_agent_name)
        if agent:
            self.store.set_active_agent_id(agent.id)
            return agent

        # Create fresh default agent with full Letta core memory blocks
        agent_id = str(uuid.uuid4())
        default_agent = AgentState(
            id=agent_id,
            name=self.config.default_agent_name,
            description="Persistent stateful Letta AI partner inside Google Antigravity",
            model=self.config.gemini_model,
            embedding_model="text-embedding-004",
            core_memory={
                "persona": MemoryBlock(
                    label="persona",
                    value=(
                        "I am an intelligent, stateful AI agent running inside Google Antigravity. "
                        "I utilize Letta's memory architecture (in-context core memory blocks, out-of-context "
                        "archival memory, and recall message history). I preserve facts, code structures, "
                        "and context across sessions."
                    ),
                    limit=4000,
                ),
                "human": MemoryBlock(
                    label="human",
                    value=(
                        "The human is a software engineer developing inside Google Antigravity. "
                        "I track their preferences, workflows, technical stack, and design standards."
                    ),
                    limit=4000,
                ),
                "project_context": MemoryBlock(
                    label="project_context",
                    value="Active environment: Google Antigravity pair-programming workspace with Letta integration.",
                    limit=4000,
                ),
            },
            tools=[
                "core_memory_append",
                "core_memory_replace",
                "archival_memory_insert",
                "archival_memory_search",
                "conversation_search",
            ],
        )
        self.store.create_agent(default_agent)
        self.store.set_active_agent_id(default_agent.id)
        return default_agent

    # ---------------------------------------------------------
    # Unified Public Agent API
    # ---------------------------------------------------------

    def get_active_agent(self) -> AgentState:
        """Return the currently selected active agent."""
        agent = self._ensure_default_agent()
        return agent

    def select_agent(self, agent_id_or_name: str) -> AgentState:
        """Select the active agent by ID or name."""
        agent = self.store.get_agent(agent_id_or_name)
        if not agent:
            raise KeyError(f"Agent '{agent_id_or_name}' not found.")
        self.store.set_active_agent_id(agent.id)
        return agent

    def list_agents(self) -> List[AgentState]:
        """List all available agents."""
        if self.mode == "remote":
            try:
                client = self._get_remote_client()
                remote_agents = client.agents.list()
                result = []
                for ra in remote_agents:
                    result.append(
                        AgentState(
                            id=ra.id,
                            name=ra.name,
                            description=ra.description or "",
                            model=getattr(ra, "model", "remote"),
                            embedding_model=getattr(ra, "embedding", "remote"),
                            tools=[],
                        )
                    )
                return result
            except Exception:
                pass
        return self.store.list_agents()

    def create_agent(
        self,
        name: str,
        persona: str,
        human: str,
        model: Optional[str] = None,
        tools: Optional[List[str]] = None,
    ) -> AgentState:
        """Create a new agent with defined core memory blocks."""
        agent_id = str(uuid.uuid4())
        agent = AgentState(
            id=agent_id,
            name=name,
            description=f"Letta agent created for {name}",
            model=model or self.config.gemini_model,
            embedding_model="text-embedding-004",
            core_memory={
                "persona": MemoryBlock(label="persona", value=persona),
                "human": MemoryBlock(label="human", value=human),
            },
            tools=tools or [
                "core_memory_append",
                "core_memory_replace",
                "archival_memory_insert",
                "archival_memory_search",
                "conversation_search",
            ],
        )
        self.store.create_agent(agent)
        self.store.set_active_agent_id(agent.id)
        return agent

    def send_message(self, message: str, agent_id: Optional[str] = None) -> AgentResponse:
        """Send a message to the active or specified Letta agent."""
        target_agent = self.get_active_agent() if not agent_id else self.store.get_agent(agent_id)
        if not target_agent:
            raise KeyError(f"Target agent '{agent_id}' does not exist.")

        if self.mode == "remote":
            try:
                client = self._get_remote_client()
                response = client.agents.messages.create(
                    agent_id=target_agent.id,
                    messages=[{"role": "user", "content": message}],
                )
                assistant_msgs = []
                for m in getattr(response, "messages", []):
                    role = getattr(m, "role", "assistant")
                    text = getattr(m, "content", "")
                    assistant_msgs.append(Message(id=str(uuid.uuid4()), role=role, content=text))
                return AgentResponse(
                    agent_id=target_agent.id,
                    messages=assistant_msgs,
                )
            except Exception as e:
                # Log and fallback to embedded engine
                pass

        # Embedded execution
        return self.engine.execute_turn(target_agent.id, message)

    def get_core_memory(self, agent_id: Optional[str] = None) -> Dict[str, MemoryBlock]:
        """Fetch all core memory blocks for the active agent."""
        target_id = agent_id or self.get_active_agent().id
        return self.store.list_blocks(target_id)

    def update_core_memory(
        self,
        label: str,
        value: str,
        action: str = "replace_all",
        old_content: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> MemoryBlock:
        """Explicitly update or append to a core memory block."""
        target_id = agent_id or self.get_active_agent().id
        if action == "append":
            block, _ = self.store.append_block(target_id, label, value)
            return block
        elif action == "replace_substring" and old_content:
            block, _ = self.store.replace_block(target_id, label, old_content, value)
            return block
        else:
            return self.store.set_block(target_id, label, value)

    def insert_archival_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> ArchivalPassage:
        """Insert knowledge into archival memory."""
        target_id = agent_id or self.get_active_agent().id
        return self.store.insert_passage(target_id, text, metadata)

    def search_archival_memory(
        self,
        query: str,
        limit: int = 5,
        agent_id: Optional[str] = None,
    ) -> List[ArchivalPassage]:
        """Search the agent's archival memory database."""
        target_id = agent_id or self.get_active_agent().id
        return self.store.search_passages(target_id, query, limit=limit)

    def get_messages(self, limit: int = 20, agent_id: Optional[str] = None) -> List[Message]:
        """Retrieve conversation history (recall memory)."""
        target_id = agent_id or self.get_active_agent().id
        return self.store.get_messages(target_id, limit=limit)

    def reset_messages(self, agent_id: Optional[str] = None) -> int:
        """Reset conversation recall memory while preserving core and archival memory."""
        target_id = agent_id or self.get_active_agent().id
        return self.store.reset_messages(target_id)
