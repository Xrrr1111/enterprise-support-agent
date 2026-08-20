"""Installable command-line interface."""

from __future__ import annotations

import argparse
import json

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Enterprise Support Agent")
    parser.add_argument("task", nargs="*", help="Customer support request")
    parser.add_argument("--json", action="store_true", help="Print complete final state as JSON")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    task = " ".join(arguments.task).strip() or "Check order ORD-1002 and explain the refund policy."
    state = EnterpriseSupportAgent(Settings()).run(task)
    if arguments.json:
        print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(state.final_answer)
        print(f"\ntrace_id={state.trace_id} stop_reason={state.stop_reason} turns={state.turn_count}")
    return 0 if state.stop_reason == "completed" else 1
