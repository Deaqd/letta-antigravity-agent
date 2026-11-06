"""Unit tests for the SQLite LettaMemoryStore."""

import pytest
from letta_integration.core.memory import LettaMemoryStore
from letta_integration.core.models import AgentState, MemoryBlock, Message


@pytest.fixture
def memory_store():
    store = LettaMemoryStore(":memory:")
    yield store
    store.close()


def test_agent_lifecycle(memory_store):
    agent = AgentState(
        id="test-agent-1",
        name="TestAgent",
        description="A test agent",
        model="gemini-2.5-flash",
        embedding_model="text-embedding-004",
        core_memory={
            "persona": MemoryBlock(label="persona", value="I am a tester."),
            "human": MemoryBlock(label="human", value="The user is testing."),
        },
    )

    created = memory_store.create_agent(agent)
    assert created.id == "test-agent-1"
    assert created.name == "TestAgent"

    fetched = memory_store.get_agent("test-agent-1")
    assert fetched is not None
    assert fetched.name == "TestAgent"
    assert "persona" in fetched.core_memory
    assert fetched.core_memory["persona"].value == "I am a tester."

    agents_list = memory_store.list_agents()
    assert len(agents_list) == 1
    assert agents_list[0].id == "test-agent-1"


def test_core_memory_operations(memory_store):
    agent = AgentState(
        id="test-agent-2",
        name="TestAgent2",
        core_memory={
            "persona": MemoryBlock(label="persona", value="Initial persona."),
            "human": MemoryBlock(label="human", value="Alice is a dev.", limit=100),
        },
    )
    memory_store.create_agent(agent)

    # Append
    block, msg = memory_store.append_block("test-agent-2", "human", "She likes Python.")
    assert "Alice is a dev." in block.value
    assert "She likes Python." in block.value

    # Replace
    block, msg = memory_store.replace_block(
        "test-agent-2", "human", "Alice is a dev.", "Alice is a senior dev."
    )
    assert "Alice is a senior dev." in block.value

    # Exceed limit
    with pytest.raises(ValueError):
        memory_store.append_block("test-agent-2", "human", "X" * 150)


def test_archival_memory(memory_store):
    agent = AgentState(id="test-agent-3", name="TestAgent3")
    memory_store.create_agent(agent)

    p1 = memory_store.insert_passage("test-agent-3", "The project uses FastAPI and PostgreSQL.")
    p2 = memory_store.insert_passage("test-agent-3", "Deployment runs on Google Kubernetes Engine.")

    assert p1.id is not None
    assert p2.id is not None

    # Search
    search_results = memory_store.search_passages("test-agent-3", "PostgreSQL database")
    assert len(search_results) >= 1
    assert "PostgreSQL" in search_results[0].text

    # Search with no match
    no_results = memory_store.search_passages("test-agent-3", "Quantum gravity physics")
    assert len(no_results) == 0

    # List & Delete
    passages = memory_store.list_passages("test-agent-3")
    assert len(passages) == 2

    deleted = memory_store.delete_passage("test-agent-3", p1.id)
    assert deleted is True
    assert len(memory_store.list_passages("test-agent-3")) == 1


def test_recall_memory(memory_store):
    agent = AgentState(id="test-agent-4", name="TestAgent4")
    memory_store.create_agent(agent)

    m1 = Message(id="m1", role="user", content="Hello agent!")
    m2 = Message(id="m2", role="assistant", content="Hello Alice!")

    memory_store.save_message("test-agent-4", m1)
    memory_store.save_message("test-agent-4", m2)

    msgs = memory_store.get_messages("test-agent-4")
    assert len(msgs) == 2
    assert msgs[0].content == "Hello agent!"
    assert msgs[1].content == "Hello Alice!"

    # Search
    search_res = memory_store.search_messages("test-agent-4", "Alice")
    assert len(search_res) == 1
    assert search_res[0].id == "m2"

    # Reset
    cleared = memory_store.reset_messages("test-agent-4")
    assert cleared == 2
    assert len(memory_store.get_messages("test-agent-4")) == 0
