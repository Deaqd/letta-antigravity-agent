"""Embedded Letta-compatible stateful agent execution engine powered by Google Gemini and SQLite."""

from __future__ import annotations

import os
import uuid
from typing import Any, Callable, Dict, List, Optional

from letta_integration.core.memory import LettaMemoryStore
from letta_integration.core.models import (
    AgentResponse,
    AgentState,
    ArchivalPassage,
    MemoryBlock,
    Message,
)


class EmbeddedLettaEngine:
    """Executes stateful Letta agents locally using SQLite persistence and Google Gemini."""

    def __init__(
        self,
        store: LettaMemoryStore,
        gemini_api_key: Optional[str] = None,
        default_model: str = "gemini-2.5-flash",
    ):
        self.store = store
        self.gemini_api_key = (
            gemini_api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self.default_model = default_model
        self._genai_client = None

    def _get_genai_client(self):
        """Lazily initialize Google GenAI client if API key is present."""
        if self._genai_client is None and self.gemini_api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                # Fallback to offline / mock engine if client fails to init
                self._genai_client = None
        return self._genai_client

    def build_system_prompt(self, agent: AgentState) -> str:
        """Render the system instructions and core memory blocks into the Letta in-context format."""
        blocks = self.store.list_blocks(agent.id)
        block_text = ""
        for label, block in blocks.items():
            block_text += f"\n<{label}>\n{block.value}\n</{label}>\n"

        base_prompt = agent.system_prompt or (
            "You are a stateful AI agent built on the Letta (formerly MemGPT) memory architecture.\n"
            "You have hierarchical memory composed of:\n"
            "1. In-context Core Memory (editable blocks below).\n"
            "2. Out-of-context Archival Memory (unlimited long-term database for passages).\n"
            "3. Recall Memory (conversation history).\n\n"
            "You must manage your memory autonomously:\n"
            "- When you learn new persistent facts about the user or project, update the <human> or other core memory blocks.\n"
            "- When significant knowledge, code, or context should be saved permanently, insert it into archival memory.\n"
            "- Before answering questions about past sessions, search archival memory.\n"
        )

        return f"{base_prompt}\n\n### ACTIVE CORE MEMORY:\n{block_text}"

    def execute_turn(
        self,
        agent_id: str,
        user_input: str,
        override_model: Optional[str] = None,
    ) -> AgentResponse:
        """Process a conversational turn, invoke memory tools, update state, and return response."""
        agent = self.store.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent '{agent_id}' does not exist.")

        # 1. Save user input to recall memory
        user_msg = Message(
            id=str(uuid.uuid4()),
            role="user",
            content=user_input,
        )
        self.store.save_message(agent.id, user_msg)

        memory_updates: List[Dict[str, Any]] = []
        tool_calls_record: List[Dict[str, Any]] = []
        inner_thoughts: List[str] = []

        # Tool dispatcher definitions
        def tool_core_memory_append(label: str, content: str) -> str:
            block, msg = self.store.append_block(agent.id, label, content)
            memory_updates.append({"action": "append", "label": label, "content": content})
            return msg

        def tool_core_memory_replace(label: str, old_content: str, new_content: str) -> str:
            block, msg = self.store.replace_block(agent.id, label, old_content, new_content)
            memory_updates.append({"action": "replace", "label": label, "new_content": new_content})
            return msg

        def tool_archival_memory_insert(content: str) -> str:
            passage = self.store.insert_passage(agent.id, content)
            memory_updates.append({"action": "archival_insert", "passage_id": passage.id, "text": content})
            return f"Passage saved to archival memory with ID: {passage.id}"

        def tool_archival_memory_search(query: str, limit: int = 5) -> str:
            passages = self.store.search_passages(agent.id, query, limit=limit)
            if not passages:
                return f"No archival passages found matching query: '{query}'."
            formatted = [f"[{p.id}] {p.text}" for p in passages]
            return "\n\n".join(formatted)

        def tool_conversation_search(query: str, limit: int = 5) -> str:
            msgs = self.store.search_messages(agent.id, query, limit=limit)
            if not msgs:
                return f"No past messages found matching: '{query}'."
            formatted = [f"[{m.role}]: {m.content}" for m in msgs]
            return "\n".join(formatted)

        tool_registry: Dict[str, Callable[..., Any]] = {
            "core_memory_append": tool_core_memory_append,
            "core_memory_replace": tool_core_memory_replace,
            "archival_memory_insert": tool_archival_memory_insert,
            "archival_memory_search": tool_archival_memory_search,
            "conversation_search": tool_conversation_search,
        }

        client = self._get_genai_client()

        if client:
            try:
                # Use Google GenAI SDK for inference with tool calling
                model_name = override_model or agent.model or self.default_model
                system_instruction = self.build_system_prompt(agent)

                # Fetch recent messages for context
                recent_msgs = self.store.get_messages(agent.id, limit=10)
                contents = []
                for m in recent_msgs:
                    if m.content:
                        contents.append({"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content}]})

                # Letta tool declarations for Gemini
                declared_tools = [
                    tool_core_memory_append,
                    tool_core_memory_replace,
                    tool_archival_memory_insert,
                    tool_archival_memory_search,
                    tool_conversation_search,
                ]

                # Generate content
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={
                        "system_instruction": system_instruction,
                        "tools": declared_tools,
                        "temperature": 0.7,
                    },
                )

                # Process tool calls if any
                reply_text = ""
                if response.function_calls:
                    for call in response.function_calls:
                        func_name = call.name
                        func_args = call.args or {}
                        tool_calls_record.append({"tool": func_name, "args": func_args})
                        if func_name in tool_registry:
                            func = tool_registry[func_name]
                            tool_result = func(**func_args)
                            inner_thoughts.append(f"Executed tool {func_name}: {tool_result}")

                    # Run follow-up turn to produce final text after tool execution
                    follow_up = client.models.generate_content(
                        model=model_name,
                        contents=[
                            {"role": "user", "parts": [{"text": user_input}]},
                            {"role": "model", "parts": [{"text": f"Tools executed: {inner_thoughts}. Now replying."}]},
                        ],
                        config={"system_instruction": system_instruction},
                    )
                    reply_text = follow_up.text or "Memory updated."
                else:
                    reply_text = response.text or ""

            except Exception as e:
                inner_thoughts.append(f"GenAI Execution Error (falling back to deterministic memory processing): {str(e)}")
                reply_text = self._fallback_deterministic_processing(
                    agent.id, user_input, tool_registry, memory_updates, tool_calls_record, inner_thoughts
                )
        else:
            # Deterministic processing when running offline or without external Gemini API key
            reply_text = self._fallback_deterministic_processing(
                agent.id, user_input, tool_registry, memory_updates, tool_calls_record, inner_thoughts
            )

        # Save assistant reply to recall memory
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            role="assistant",
            content=reply_text,
            tool_calls=tool_calls_record if tool_calls_record else None,
        )
        self.store.save_message(agent.id, assistant_msg)

        return AgentResponse(
            agent_id=agent.id,
            messages=[user_msg, assistant_msg],
            inner_thoughts=inner_thoughts,
            memory_updates=memory_updates,
            tool_calls=tool_calls_record,
        )

    def _fallback_deterministic_processing(
        self,
        agent_id: str,
        user_input: str,
        tool_registry: Dict[str, Callable[..., Any]],
        memory_updates: List[Dict[str, Any]],
        tool_calls_record: List[Dict[str, Any]],
        inner_thoughts: List[str],
    ) -> str:
        """Autonomous heuristic processing for local environments without an active API key."""
        lower_input = user_input.lower()
        thought = "Analyzing user statement for persistent facts..."
        inner_thoughts.append(thought)

        # Detect user preferences or facts (e.g. "my name is...", "remember that...", "I prefer...")
        if any(kw in lower_input for kw in ["remember that", "remember:", "note that", "save this"]):
            fact = user_input
            for kw in ["remember that", "remember:", "note that", "save this"]:
                if kw in lower_input:
                    idx = lower_input.index(kw) + len(kw)
                    fact = user_input[idx:].strip(" :,\n")
                    break
            tool_registry["archival_memory_insert"](content=fact)
            tool_calls_record.append({"tool": "archival_memory_insert", "args": {"content": fact}})
            inner_thoughts.append(f"Autonomous memory: saved fact '{fact}' to archival memory.")
            return f"I have committed this to my long-term archival memory: \"{fact}\"."

        elif any(kw in lower_input for kw in ["my name is", "i am", "call me", "i prefer", "my goal is"]):
            # Update human core memory block
            fact = user_input.strip()
            tool_registry["core_memory_append"](label="human", content=fact)
            tool_calls_record.append({"tool": "core_memory_append", "args": {"label": "human", "content": fact}})
            inner_thoughts.append(f"Autonomous memory: updated <human> block with '{fact}'.")
            return f"I've updated my core memory about you: \"{fact}\"."

        elif any(kw in lower_input for kw in ["what do you know about me", "who am i", "what are my preferences"]):
            human_block = self.store.get_block(agent_id, "human")
            val = human_block.value if human_block else "No details recorded yet."
            return f"Here is what is currently stored in my core memory about you:\n\n{val}"

        elif any(kw in lower_input for kw in ["who are you", "what is your persona"]):
            persona_block = self.store.get_block(agent_id, "persona")
            val = persona_block.value if persona_block else "Stateful Letta Agent in Antigravity."
            return f"Here is my active persona in core memory:\n\n{val}"

        elif any(kw in lower_input for kw in ["search archival", "search memory", "recall"]):
            query = user_input
            for kw in ["search archival", "search memory", "recall"]:
                if kw in lower_input:
                    idx = lower_input.index(kw) + len(kw)
                    query = user_input[idx:].strip(" :,\n")
                    break
            results = tool_registry["archival_memory_search"](query=query)
            tool_calls_record.append({"tool": "archival_memory_search", "args": {"query": query}})
            return f"Archival search results for '{query}':\n\n{results}"

        return (
            f"Acknowledged. I've processed your message ('{user_input}'). "
            "My persistent core and recall memory logs are active and preserved across your Antigravity sessions."
        )
