"""Unit tests for the MCP Server tools."""

import json
import pytest
from letta_integration.server import mcp_server


def test_mcp_letta_list_and_get_memory():
    # List agents tool
    list_res = json.loads(mcp_server.letta_list_agents())
    assert "active_agent_id" in list_res
    assert len(list_res["agents"]) >= 1

    # Get core memory tool
    mem_res = json.loads(mcp_server.letta_get_core_memory())
    assert "persona" in mem_res
    assert "human" in mem_res


def test_mcp_letta_update_and_archive():
    # Update core memory
    up_res = json.loads(
        mcp_server.letta_update_core_memory(
            label="human",
            value="User prefers unit tests with pytest.",
            action="append",
        )
    )
    assert up_res["status"] == "success"
    assert "pytest" in up_res["new_value"]

    # Insert archival memory
    arch_res = json.loads(
        mcp_server.letta_insert_archival_memory(
            text="Server runs on port 8080 with SSL enabled.",
            category="infra",
        )
    )
    assert arch_res["status"] == "success"
    assert "passage_id" in arch_res

    # Search archival memory
    search_res = json.loads(
        mcp_server.letta_search_archival_memory(query="SSL enabled", limit=3)
    )
    assert search_res["count"] >= 1
    assert any("port 8080" in p["text"] for p in search_res["passages"])


def test_mcp_letta_send_message_and_recall():
    send_res = json.loads(
        mcp_server.letta_send_message(message="Remember that our production environment is named Prod-GCP.")
    )
    assert "agent_id" in send_res
    assert "response" in send_res

    # Check recall messages
    recall_res = json.loads(mcp_server.letta_get_recall_messages(limit=5))
    assert recall_res["count"] >= 2

    # Reset recall messages
    reset_res = json.loads(mcp_server.letta_reset_messages())
    assert reset_res["status"] == "success"
