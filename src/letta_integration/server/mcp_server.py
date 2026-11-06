"""Antigravity-compliant Model Context Protocol (MCP) Server for Letta AI Agent."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

from mcp.server.mcpserver import MCPServer
from letta_integration.core.client import LettaUnifiedClient

# Configure clean logging to stderr to keep stdout pure for JSON-RPC MCP transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("letta-mcp")

# Initialize Letta client
client = LettaUnifiedClient()

# Initialize MCPServer
server = MCPServer("letta-agent")


@server.tool()
def letta_send_message(message: str, agent_id: Optional[str] = None) -> str:
    """Send a user prompt to the active Letta agent, execute memory tools, and receive the response.

    Args:
        message: The message or instruction to send to the Letta agent.
        agent_id: Optional specific agent ID or name (defaults to active agent).
    """
    try:
        response = client.send_message(message=message, agent_id=agent_id if agent_id else None)
        out = {
            "agent_id": response.agent_id,
            "response": response.messages[-1].content if response.messages else "",
            "inner_thoughts": response.inner_thoughts,
            "memory_updates": response.memory_updates,
            "tool_calls": response.tool_calls,
        }
        return json.dumps(out, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_send_message: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


@server.tool()
def letta_get_core_memory(agent_id: Optional[str] = None) -> str:
    """Retrieve all in-context Core Memory blocks (e.g., 'persona', 'human', 'project_context').

    Args:
        agent_id: Optional specific agent ID or name (defaults to active agent).
    """
    try:
        blocks = client.get_core_memory(agent_id=agent_id if agent_id else None)
        result = {
            k: {
                "label": b.label,
                "value": b.value,
                "limit": b.limit,
                "read_only": b.read_only,
            }
            for k, b in blocks.items()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_get_core_memory: {e}")
        return json.dumps({"error": str(e)})


@server.tool()
def letta_update_core_memory(
    label: str,
    value: str,
    action: str = "append",
    old_content: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> str:
    """Update or append to an in-context core memory block (e.g., recording user preferences or persona edits).

    Args:
        label: The block label (e.g. 'human', 'persona', 'project_context').
        value: The new content or content to append.
        action: 'append' (default), 'replace_all', or 'replace_substring'.
        old_content: Required if action is 'replace_substring'.
        agent_id: Optional specific agent ID or name.
    """
    try:
        updated = client.update_core_memory(
            label=label,
            value=value,
            action=action,
            old_content=old_content if old_content else None,
            agent_id=agent_id if agent_id else None,
        )
        return json.dumps(
            {
                "status": "success",
                "label": updated.label,
                "new_value": updated.value,
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in letta_update_core_memory: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


@server.tool()
def letta_search_archival_memory(
    query: str, limit: int = 5, agent_id: Optional[str] = None
) -> str:
    """Semantically search the agent's out-of-context long-term archival memory.

    Args:
        query: The search keywords or natural language query.
        limit: Maximum number of passages to return (default 5).
        agent_id: Optional specific agent ID.
    """
    try:
        passages = client.search_archival_memory(
            query=query, limit=limit, agent_id=agent_id if agent_id else None
        )
        result = [
            {"id": p.id, "text": p.text, "created_at": p.created_at, "metadata": p.metadata}
            for p in passages
        ]
        return json.dumps({"query": query, "count": len(result), "passages": result}, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_search_archival_memory: {e}")
        return json.dumps({"error": str(e)})


@server.tool()
def letta_insert_archival_memory(
    text: str, category: str = "general", agent_id: Optional[str] = None
) -> str:
    """Permanently store a text passage into the agent's out-of-context archival memory.

    Args:
        text: The text passage or knowledge to archive.
        category: Optional metadata category tag.
        agent_id: Optional specific agent ID.
    """
    try:
        passage = client.insert_archival_memory(
            text=text,
            metadata={"category": category},
            agent_id=agent_id if agent_id else None,
        )
        return json.dumps(
            {
                "status": "success",
                "passage_id": passage.id,
                "created_at": passage.created_at,
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in letta_insert_archival_memory: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


@server.tool()
def letta_list_agents() -> str:
    """List all available Letta agents and identify the currently active agent."""
    try:
        agents = client.list_agents()
        active = client.get_active_agent()
        result = [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "model": a.model,
                "is_active": a.id == active.id,
            }
            for a in agents
        ]
        return json.dumps({"active_agent_id": active.id, "agents": result}, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_list_agents: {e}")
        return json.dumps({"error": str(e)})


@server.tool()
def letta_select_agent(agent_id_or_name: str) -> str:
    """Select the active Letta agent context for current and future sessions.

    Args:
        agent_id_or_name: The ID or Name of the agent to activate.
    """
    try:
        agent = client.select_agent(agent_id_or_name)
        return json.dumps(
            {
                "status": "success",
                "active_agent_id": agent.id,
                "active_agent_name": agent.name,
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in letta_select_agent: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


@server.tool()
def letta_create_agent(
    name: str,
    persona: str,
    human: str,
    model: Optional[str] = None,
) -> str:
    """Create a new stateful Letta agent with custom persona and human core memory blocks.

    Args:
        name: Name of the new agent.
        persona: Text describing the agent's identity, behavior, and tone.
        human: Initial facts and context about the human user.
        model: Model name (defaults to configured model, e.g. gemini-2.5-flash).
    """
    try:
        agent = client.create_agent(
            name=name,
            persona=persona,
            human=human,
            model=model if model else None,
        )
        return json.dumps(
            {
                "status": "success",
                "agent_id": agent.id,
                "name": agent.name,
                "model": agent.model,
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in letta_create_agent: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


@server.tool()
def letta_get_recall_messages(limit: int = 15, agent_id: Optional[str] = None) -> str:
    """Retrieve recent conversational message history (recall memory).

    Args:
        limit: Number of recent messages to return (default 15).
        agent_id: Optional specific agent ID.
    """
    try:
        msgs = client.get_messages(limit=limit, agent_id=agent_id if agent_id else None)
        result = [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in msgs
        ]
        return json.dumps({"count": len(result), "messages": result}, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_get_recall_messages: {e}")
        return json.dumps({"error": str(e)})


@server.tool()
def letta_reset_messages(agent_id: Optional[str] = None) -> str:
    """Clear conversation history (recall memory) while preserving Core and Archival memory.

    Args:
        agent_id: Optional specific agent ID.
    """
    try:
        count = client.reset_messages(agent_id=agent_id if agent_id else None)
        return json.dumps({"status": "success", "cleared_messages_count": count}, indent=2)
    except Exception as e:
        logger.error(f"Error in letta_reset_messages: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


def main():
    """Run the MCP server over stdio transport."""
    logger.info("Starting Letta MCP Server on stdio transport...")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
