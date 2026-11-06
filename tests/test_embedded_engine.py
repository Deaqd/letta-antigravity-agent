"""Unit tests for the EmbeddedLettaEngine."""

import pytest
from letta_integration.core.engine import EmbeddedLettaEngine
from letta_integration.core.memory import LettaMemoryStore
from letta_integration.core.models import AgentState, MemoryBlock


@pytest.fixture
def engine():
    store = LettaMemoryStore(":memory:")
    agent = AgentState(
        id="engine-test-agent",
        name="EngineTester",
        core_memory={
            "persona": MemoryBlock(label="persona", value="Helpful assistant."),
            "human": MemoryBlock(label="human", value="Alice is a Python engineer."),
        },
    )
    store.create_agent(agent)
    eng = EmbeddedLettaEngine(store, gemini_api_key=None)
    return eng, store


def test_system_prompt_rendering(engine):
    eng, store = engine
    agent = store.get_agent("engine-test-agent")
    prompt = eng.build_system_prompt(agent)

    assert "<persona>" in prompt
    assert "Helpful assistant." in prompt
    assert "<human>" in prompt
    assert "Alice is a Python engineer." in prompt


def test_turn_execution_preference_update(engine):
    eng, store = engine

    # Send preference update turn
    response = eng.execute_turn("engine-test-agent", "I prefer using TypeScript for frontend code.")

    assert response.agent_id == "engine-test-agent"
    assert len(response.messages) == 2
    assert len(response.memory_updates) == 1
    assert response.memory_updates[0]["label"] == "human"

    # Verify block updated in store
    block = store.get_block("engine-test-agent", "human")
    assert "TypeScript" in block.value


def test_turn_execution_archival_save(engine):
    eng, store = engine

    response = eng.execute_turn("engine-test-agent", "Remember that the database port is 5432.")

    assert response.agent_id == "engine-test-agent"
    assert len(response.memory_updates) == 1
    assert response.memory_updates[0]["action"] == "archival_insert"

    # Search archival memory
    passages = store.search_passages("engine-test-agent", "database port")
    assert len(passages) >= 1
    assert "5432" in passages[0].text
