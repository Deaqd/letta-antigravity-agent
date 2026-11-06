# Letta AI Agent Integration for Google Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Antigravity Compatible](https://img.shields.io/badge/Antigravity-Compatible-4285F4.svg)](https://deepmind.google/technologies/antigravity/)
[![Letta Architecture](https://img.shields.io/badge/Memory-Letta%20%2F%20MemGPT-purple.svg)](https://letta.com)

A full-fledged, persistent stateful AI agent integration providing Letta's OS-style hierarchical memory architecture (**In-Context Core Memory blocks**, **Out-of-Context Archival Memory database**, and **Recall Conversation History**) directly inside **Google Antigravity**.

Selectable on the fly right from Antigravity's **Agents** dropdown menu or usable via MCP tools across all sessions globally.

---

> [!IMPORTANT]
> ### 🤖 AI Generation & Assistance Disclaimer
> This project, including its codebase, integration architecture, Model Context Protocol (MCP) server, test suites, and documentation, was developed and authored using **AI assistance via Google Antigravity (powered by Gemini models)** in pairing with human direction.
> 
> All code and schemas have undergone rigorous automated testing (`pytest`, JSON-RPC 2.0 handshake validation, and SQLite persistence checks). As with any AI-assisted system, users are encouraged to review configurations and security permissions before deploying in sensitive environments.

---

## ⚡ One-Prompt AI Installation (For Antigravity)

If you are using Google Antigravity, you don't even need to run manual commands. Simply copy and paste the prompt below into your Antigravity chat:

```text
Please install and configure the Letta AI Agent integration from this repository.
1. Create a Python virtual environment in .venv and install the package with 'pip install -e .'.
2. Set up the local SQLite database directory at ./data/.
3. Register the MCP server globally in ~/.gemini/config/mcp_config.json pointing to this project.
4. Copy the agent definition from plugins/letta-agent/agents/letta-agent.md to ~/.gemini/config/plugins/letta-agent/agents/letta-agent.md so that 'letta-agent' appears in the Antigravity UI Agents dropdown.
5. Run the pytest test suite to verify all 13 tests pass.
```

---

## 🚀 One-Command Installation (PowerShell)

Run the included automated installer script in PowerShell:

```powershell
.\install.ps1
```

This single command automatically:
1. Verifies your Python 3.10+ runtime.
2. Creates `.venv` and installs the package in editable mode.
3. Initializes the SQLite storage directory.
4. Registers the `letta-agent` MCP server globally in `~/.gemini/config/mcp_config.json`.
5. Installs the UI agent definition so `letta-agent` appears in Antigravity's **Agents** dropdown menu.
6. Runs the complete test suite to verify 100% test pass rate.

---

## 🧠 Architecture & Memory Hierarchy

```
               ┌───────────────────────────────────────────────────────┐
               │                  Google Antigravity                   │
               │                                                       │
               │  ┌────────────────────┐      ┌─────────────────────┐  │
               │  │  UI Agents Menu    │      │  Letta Agent Skill  │  │
               │  │  (letta-agent)     │      │  (Progressive Disc.)│  │
               │  └─────────┬──────────┘      └──────────┬──────────┘  │
               │            │                            │             │
               │            └──────────────┬─────────────┘             │
               │                           │                           │
               │                           ▼                           │
               │             ┌───────────────────────────┐             │
               │             │  Antigravity Tool Engine  │             │
               │             └─────────────┬─────────────┘             │
               └───────────────────────────│───────────────────────────┘
                                           │ (JSON-RPC 2.0 / stdio)
                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Letta MCP Server Engine                         │
│                                                                      │
│  Tools:                                                              │
│  - letta_send_message          - letta_get_core_memory               │
│  - letta_update_core_memory    - letta_search_archival_memory        │
│  - letta_insert_archival_memory- letta_list_agents                   │
│  - letta_create_agent          - letta_select_agent                  │
│  - letta_get_recall_messages   - letta_reset_messages                │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │           Letta Unified Client            │
             └─────────────────────┬─────────────────────┘
                                   │
             ┌─────────────────────┴─────────────────────┐
             │                                           │
             ▼ (If LETTA_BASE_URL set)                   ▼ (Default / Embedded)
┌─────────────────────────┐                 ┌──────────────────────────┐
│  Remote Letta Server /  │                 │  Embedded Letta Engine   │
│  Letta Cloud (REST API) │                 │  + Google Gemini SDK     │
│  via letta-client 1.12  │                 │  + SQLite Persistent DB  │
└─────────────────────────┘                 └──────────────────────────┘
                                                         │
                                                         ▼
                                            ┌──────────────────────────┐
                                            │   Hierarchical Storage   │
                                            │   - Core Memory Blocks   │
                                            │   - Archival Passages    │
                                            │   - Recall Message Logs  │
                                            └──────────────────────────┘
```

### The Three Memory Tiers

1. **In-Context Core Memory Blocks**:
   - `persona`: Defines agent identity, instructions, and communication rules.
   - `human`: Profile of the user, coding style, framework preferences, and guidelines.
   - `project_context`: Active workspace rules, architecture standards, and constraints.
   - *Self-editing*: The agent modifies its core memory during conversations via `append` or `replace_substring`.
2. **Out-of-Context Archival Memory**:
   - Long-term external database of passages, design notes, and documentation snippets.
   - Searchable via relevance query at any time.
3. **Recall Memory**:
   - Complete history of user and assistant interactions.
   - Resettable non-destructively (clearing conversation logs without losing core or archival memories).

---

## 🎯 Switching to the Agent in the UI

1. Open the model/agent selector at the bottom left of your Antigravity chat bar (e.g. `Gemini 3.8 Flash High`).
2. Hover over **Main Agent >** to expand the **Agents** submenu.
3. Select **`letta-agent`**.
4. The conversation now runs with the stateful Letta persona and autonomous memory persistence!

---

## 🛠️ CLI Administration & Diagnostics

You can inspect and manage your Letta agent directly from the command line:

```powershell
# Check agent status and core memory character budgets
letta-admin status

# View all active core memory blocks
letta-admin core-memory

# Append persistent facts about the human user
letta-admin core-memory --append human "User prefers Go for microservices and React for web."

# Insert documentation or architecture rules into archival memory
letta-admin archival --insert "Architecture RFC: Auth tokens use RS256 with 15-minute expiration."

# Search archival memory
letta-admin archival --search "Auth tokens"

# Direct conversation turn with inner-thought inspection
letta-admin chat "Remember that our staging cluster is hosted in us-central1."
```

---

## 🧪 Automated Tests

Run the full pytest test suite:

```powershell
$env:PYTHONPATH = "src"
pytest -v
```

All 13 unit tests verify:
- SQLite persistence and table schema initialization
- Core memory block CRUD, character limits, and read-only protection
- Archival memory passage insertion, token relevance scoring, and deletion
- Recall memory chronological sorting, search, and non-destructive reset
- Embedded Letta engine autonomous preference updates and archival insertion
- Antigravity MCP tool schema and JSON-RPC compliance

---

## ⚙️ Configuration (.env)

Copy `.env.example` to `.env`:

```ini
# Operation mode: 'auto', 'embedded', or 'remote'
LETTA_MODE=auto

# Optional: Remote Letta Server or Letta Cloud
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

## 📄 License

This project is licensed under the [MIT License](LICENSE).
