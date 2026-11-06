"""CLI administration and diagnostics tool for the Letta Antigravity integration."""

from __future__ import annotations

import argparse
import json
import sys

from letta_integration.core.client import LettaUnifiedClient


def main():
    parser = argparse.ArgumentParser(description="Letta AI Agent Admin & Diagnostics Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Status / Info
    subparsers.add_parser("status", help="Show current Letta configuration and active agent status")

    # List agents
    subparsers.add_parser("list-agents", help="List all stored Letta agents")

    # Core memory
    parser_cm = subparsers.add_parser("core-memory", help="View or edit core memory blocks")
    parser_cm.add_argument("--set", nargs=2, metavar=("LABEL", "VALUE"), help="Set content of a block")
    parser_cm.add_argument("--append", nargs=2, metavar=("LABEL", "CONTENT"), help="Append content to a block")

    # Archival memory
    parser_am = subparsers.add_parser("archival", help="View, insert, or search archival memory")
    parser_am.add_argument("--insert", metavar="TEXT", help="Insert a passage into archival memory")
    parser_am.add_argument("--search", metavar="QUERY", help="Search archival passages")

    # Chat turn
    parser_chat = subparsers.add_parser("chat", help="Send a message to the active Letta agent")
    parser_chat.add_argument("message", help="Message text")

    args = parser.parse_args()
    client = LettaUnifiedClient()

    if args.command == "status" or not args.command:
        active = client.get_active_agent()
        print("========================================")
        print("  LETTA AI AGENT - ANTIGRAVITY ENGINE   ")
        print("========================================")
        print(f"Mode:          {client.mode.upper()}")
        print(f"Active Agent:  {active.name} ({active.id})")
        print(f"Model:         {active.model}")
        print(f"Database Path: {client.config.storage_path}")
        print("----------------------------------------")
        print("Core Memory Blocks:")
        blocks = client.get_core_memory()
        for k, b in blocks.items():
            print(f"  [{k}] ({len(b.value)}/{b.limit} chars)")
        print("========================================")

    elif args.command == "list-agents":
        agents = client.list_agents()
        active = client.get_active_agent()
        print(f"Total Agents: {len(agents)}")
        for a in agents:
            prefix = "-> [ACTIVE]" if a.id == active.id else "  "
            print(f"{prefix} {a.name} (ID: {a.id}, Model: {a.model})")

    elif args.command == "core-memory":
        if args.set:
            label, val = args.set
            client.update_core_memory(label=label, value=val, action="replace_all")
            print(f"Updated core memory block '{label}'.")
        elif args.append:
            label, content = args.append
            client.update_core_memory(label=label, value=content, action="append")
            print(f"Appended to core memory block '{label}'.")
        else:
            blocks = client.get_core_memory()
            for k, b in blocks.items():
                print(f"[{k}]:\n{b.value}\n")

    elif args.command == "archival":
        if args.insert:
            passage = client.insert_archival_memory(args.insert)
            print(f"Saved passage (ID: {passage.id})")
        elif args.search:
            passages = client.search_archival_memory(args.search)
            print(f"Found {len(passages)} passages matching '{args.search}':")
            for p in passages:
                print(f"- [{p.id}] {p.text}")
        else:
            passages = client.store.list_passages(client.get_active_agent().id)
            print(f"Stored Passages ({len(passages)}):")
            for p in passages:
                print(f"- [{p.id}] {p.text}")

    elif args.command == "chat":
        print(f"Sending to active agent...")
        resp = client.send_message(args.message)
        if resp.inner_thoughts:
            print("\n[Inner Thoughts]:")
            for t in resp.inner_thoughts:
                print(f"  * {t}")
        if resp.memory_updates:
            print("\n[Memory Updates]:")
            for u in resp.memory_updates:
                print(f"  * {u}")
        print("\n[Agent Response]:")
        for m in resp.messages:
            if m.role == "assistant":
                print(m.content)


if __name__ == "__main__":
    main()
