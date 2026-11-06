# Letta Agent Persistent Memory Guidelines for Antigravity

When interacting with the user inside Google Antigravity, you have access to a stateful Letta AI Agent via the `letta-agent` toolset. Follow these rules to ensure true multi-session persistence:

1. **Memory Consultation**:
   - At the beginning of complex sessions, or when asked about user preferences, previous decisions, coding styles, or past discussions, call `letta_get_core_memory` to inspect the `<human>`, `<persona>`, and `<project_context>` memory blocks.
   - For historical, archival, or documentation lookups, use `letta_search_archival_memory`.

2. **Continuous Memory Ingestion**:
   - Whenever the user states a new durable preference (e.g. language preferences, framework choices, formatting rules), call `letta_update_core_memory` with label `human` (action: `append`).
   - Whenever key project design decisions, architecture choices, or domain knowledge are established, archive them using `letta_insert_archival_memory`.

3. **Direct Stateful Dialog**:
   - If the user explicitly asks to chat with, delegate to, or prompt the Letta agent, route the message through `letta_send_message`.
   - The Letta agent will reason over its memory hierarchy, invoke autonomous memory tools, and preserve recall logs.

4. **Zero Silent Data Loss**:
   - Never reset messages or overwrite core memory blocks without explicit user intent.
   - Use `letta_update_core_memory(action='append')` rather than destructive rewrites unless replacing specific outdated facts.
