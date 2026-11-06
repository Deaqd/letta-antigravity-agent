# Workspace Rule: Letta Agent Integration

This workspace is integrated with a persistent Letta AI agent.

- Tools available: `letta_send_message`, `letta_get_core_memory`, `letta_update_core_memory`, `letta_search_archival_memory`, `letta_insert_archival_memory`, `letta_list_agents`, `letta_create_agent`, `letta_select_agent`, `letta_get_recall_messages`, `letta_reset_messages`.
- Persistent storage: SQLite database at `./data/letta_storage.db` or official remote Letta server via `LETTA_BASE_URL`.
- Autonomous memory management: Updates to `<human>`, `<persona>`, and archival passages persist across Antigravity restarts and new conversations.
