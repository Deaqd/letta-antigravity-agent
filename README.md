# Letta AI Agent Integration for Google Antigravity

A production-grade, stateful AI agent integration providing Letta's hierarchical memory architecture (In-Context Core Memory, Out-of-Context Archival Memory, and Recall Conversation History) inside Google Antigravity.

---

## Architecture Overview

```
               +-------------------------------------------------------+
               |                  Google Antigravity                   |
               |                                                       |
               |  +--------------------+      +---------------------+  |
               |  |  AGENTS.md Rules   |      |  Letta Agent Skill  |  |
               |  |  & Triggers        |      |  (Progressive Disc.)|  |
               |  +---------+----------+      +----------+----------+  |
               |            |                            |             |
               |            +--------------+-------------+             |
               |                           |                           |
               |                           v                           |
               |             +---------------------------+             |
               |             |  Antigravity Tool Engine  |             |
               |             +-------------+-------------+             |
               +---------------------------|---------------------------+
                                           | (JSON-RPC 2.0 / stdio)
                                           v
+----------------------------------------------------------------------+
|                      Letta MCP Server Engine                         |
|                                                                      |
|  Tools:                                                              |
|  - letta_send_message          - letta_get_core_memory               |
|  - letta_update_core_memory    - letta_search_archival_memory        |
|  - letta_insert_archival_memory- letta_list_agents                   |
|  - letta_create_agent          - letta_select_agent                  |
|  - letta_get_recall_messages   - letta_reset_messages                |
+----------------------------------+-----------------------------------+
                                   |
                                   v
             +-------------------------------------------+
             |           Letta Unified Client            |
             +---------------------+---------------------+
                                   |
             +---------------------+---------------------+
             |                                           |
             v (If LETTA_BASE_URL set)                   v (Default / Embedded)
+-------------------------+                 +--------------------------+
|  Remote Letta Server /  |                 |  Embedded Letta Engine   |
|  Letta Cloud (REST API) |                 |  + Google Gemini SDK     |
|                         |                 |  + SQLite Persistent DB  |
+-------------------------+                 +--------------------------+
                                                         |
                                                         v
                                            +--------------------------+
                                            |   Hierarchical Storage   |
                                            |   - Core Memory Blocks   |
                                            |   - Archival Passages    |
                                            |   - Recall Message Logs  |
                                            +--------------------------+
```

---

## Memory Tiers

1. **In-Context Core Memory Blocks**:
   - `persona`: Defines agent persona, behavioral constraints, and instructions.
   - `human`: Dynamic profile of the user, coding styles, preferences, and requirements.
   - `project_context`: Active workspace parameters, constraints, and architecture rules.
   - Memory blocks are kept directly in the prompt context and can be edited via `core_memory_append` and `core_memory_replace`.

2. **Out-of-Context Archival Memory**:
   - Long-term storage of passages, code snippets, project notes, and historical decisions.
   - Searchable via relevance query (`letta_search_archival_memory`).

3. **Recall Memory**:
   - Timestamped message logs and tool execution traces.
   - Searchable via keyword query and resettable without losing core/archival memories.

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Google Antigravity environment

### 2. Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install package and dependencies
pip install -e .
```

### 3. Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Configure parameters in `.env`:
```ini
# Operation mode: 'auto', 'embedded', or 'remote'
LETTA_MODE=auto

# Optional: Remote Letta Server (leave blank for local embedded engine)
LETTA_BASE_URL=http://localhost:8283
LETTA_API_KEY=

# Optional: Google Gemini API Key for model reasoning
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# SQLite storage path
LETTA_STORAGE_PATH=./data/letta_storage.db
LETTA_DEFAULT_AGENT=Antigravity-Letta-Partner
```

---

## Antigravity Integration

### Plugin Registration
The integration is packaged as an Antigravity Plugin located at `.agents/plugins/letta-agent`:
- `plugin.json`: Plugin manifest.
- `mcp_config.json`: MCP Server registration for Antigravity's Language Server.
- `rules/AGENTS.md`: Multi-session memory guidelines injected into Antigravity turns.
- `skills/letta/SKILL.md`: Detailed skill instructions for progressive disclosure.

### Global Configuration (Optional)
To make the Letta agent available across all Antigravity workspaces globally, add the following to `~/.gemini/config/mcp_config.json`:
```json
{
  "mcpServers": {
    "letta-agent": {
      "command": "C:\\Users\\Lapy\\OneDrive\\Documents\\AI Projects\\Letta Ai Ajent\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "letta_integration.server.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\Lapy\\OneDrive\\Documents\\AI Projects\\Letta Ai Ajent\\src",
        "LETTA_MODE": "auto",
        "LETTA_STORAGE_PATH": "C:\\Users\\Lapy\\OneDrive\\Documents\\AI Projects\\Letta Ai Ajent\\data\\letta_storage.db"
      }
    }
  }
}
```

---

## CLI Administration & Diagnostics

You can interact with and inspect the Letta agent directly from the command line:

```powershell
# Check agent status and core memory blocks
letta-admin status

# View all core memory blocks
letta-admin core-memory

# Append fact to the 'human' memory block
letta-admin core-memory --append human "User prefers strict TypeScript and pytest."

# Insert passage into archival memory
letta-admin archival --insert "Architecture RFC: Authentication uses OAuth2 with PKCE."

# Search archival memory
letta-admin archival --search "Authentication"

# Chat directly with the Letta agent
letta-admin chat "Remember that our staging cluster is running in us-central1."
```

---

## Running the Automated Test Suite

```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\pytest -v
```
All 13 unit tests verify:
- SQLite persistence and schema management
- Core memory block appending, replacing, and character limit bounds
- Archival memory passage insertion, token relevance scoring, and deletion
- Recall memory chronological sorting, search, and non-destructive reset
- Embedded Letta engine autonomous preference updates and archival insertion
- Antigravity MCP tool schema and JSON-RPC compliance
