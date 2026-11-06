---
name: letta
description: Full-fledged Letta (MemGPT) stateful agent integration for Google Antigravity. Use when managing persistent long-term memory, retrieving past conversational knowledge, querying or editing core memory blocks (human, persona, project), or routing complex tasks through a self-editing stateful Letta agent.
---

# Letta Agent Skill for Google Antigravity

This skill teaches the Antigravity agent how to operate the stateful Letta (formerly MemGPT) memory architecture.

## Overview

Letta agents maintain three tiers of persistent memory:
1. **Core Memory (In-Context)**: Editable text blocks (`persona`, `human`, `project_context`) that stay directly in the model's active context window.
2. **Archival Memory (Out-of-Context)**: An unlimited external database of searchable text passages and facts.
3. **Recall Memory (Conversational Log)**: A timestamped history of user, assistant, and tool interactions.

## When to Use Letta Tools

- **When the user mentions personal preferences or guidelines**:
  Call `letta_update_core_memory(label="human", value="User prefers...", action="append")`.
- **When user asks 'What do you remember about me?' or 'Check my preferences'**:
  Call `letta_get_core_memory()`.
- **When saving permanent knowledge, architectural decisions, or documentation**:
  Call `letta_insert_archival_memory(text="...", category="architecture")`.
- **When answering questions about past sessions or previously saved notes**:
  Call `letta_search_archival_memory(query="...")`.
- **When delegating a turn to the autonomous Letta agent**:
  Call `letta_send_message(message="...")`.

## Available MCP Tools

| Tool Name | Purpose | Key Arguments |
|---|---|---|
| `letta_send_message` | Send message to active Letta agent and trigger reasoning loop | `message` (str), `agent_id` (optional str) |
| `letta_get_core_memory` | Inspect all core memory blocks | `agent_id` (optional str) |
| `letta_update_core_memory` | Edit or append to a core memory block | `label` (str), `value` (str), `action` (str) |
| `letta_search_archival_memory` | Query archival memory passages | `query` (str), `limit` (int) |
| `letta_insert_archival_memory` | Save text into archival memory | `text` (str), `category` (str) |
| `letta_list_agents` | List all available Letta agents | None |
| `letta_create_agent` | Spin up a new Letta agent | `name` (str), `persona` (str), `human` (str) |
| `letta_select_agent` | Switch active agent | `agent_id_or_name` (str) |
| `letta_get_recall_messages` | Inspect recent conversation history | `limit` (int) |
| `letta_reset_messages` | Clear recall messages (retains core & archival memory) | `agent_id` (optional str) |

## Troubleshooting & Diagnostics

- **Database Location**: Persistent SQLite store default is at `./data/letta_storage.db`.
- **Admin CLI**: Run `python -m letta_integration.cli status` for terminal inspection.
- **Switching to Remote Server**: Set `LETTA_BASE_URL` (e.g. `http://localhost:8283`) and `LETTA_MODE=remote` in `.env`.
