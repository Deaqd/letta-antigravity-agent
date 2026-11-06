"""Unit tests for the LettaUnifiedClient."""

import os
import pytest
from letta_integration.core.client import LettaUnifiedClient
from letta_integration.core.models import LettaConfig


@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test_client.db")
    config = LettaConfig(
        mode="embedded",
        storage_path=db_file,
        default_agent_name="Test-Antigravity-Agent",
    )
    return LettaUnifiedClient(config=config)


def test_default_agent_initialization(client):
    agent = client.get_active_agent()
    assert agent is not None
    assert agent.name == "Test-Antigravity-Agent"
    assert "persona" in agent.core_memory
    assert "human" in agent.core_memory


def test_client_crud_and_memory(client):
    # Test core memory read/write
    blocks = client.get_core_memory()
    assert "persona" in blocks

    updated = client.update_core_memory(label="human", value="Test User specializes in AI.", action="append")
    assert "specializes in AI" in updated.value

    # Test archival insert & search
    passage = client.insert_archival_memory("The API gateway is hosted on cloud.google.com")
    assert passage.id is not None

    found = client.search_archival_memory("API gateway")
    assert len(found) >= 1
    assert "cloud.google.com" in found[0].text

    # Test create new agent
    new_agent = client.create_agent(
        name="SecurityReviewer",
        persona="Security specialist analyzing vulnerabilities",
        human="Security engineer",
    )
    assert new_agent.name == "SecurityReviewer"

    # List agents
    all_agents = client.list_agents()
    assert len(all_agents) == 2


def test_client_send_and_recall(client):
    resp = client.send_message("My name is Charlie and I like Go.")
    assert resp.agent_id is not None

    # Verify recall messages
    msgs = client.get_messages(limit=10)
    assert len(msgs) >= 2
    assert any("Charlie" in (m.content or "") for m in msgs)

    # Reset recall messages
    cleared = client.reset_messages()
    assert cleared >= 2
    assert len(client.get_messages(limit=10)) == 0

    # Verify core memory was preserved after recall reset
    blocks = client.get_core_memory()
    assert "Charlie" in blocks["human"].value
