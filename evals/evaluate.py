"""Run the checked-in eval dataset and compute metrics from actual agent traces."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.config import PROJECT_ROOT, Settings
from enterprise_support_agent.llm.base import ModelDecision
from enterprise_support_agent.llm.mock import MockLLM, ScriptedLLM
from enterprise_support_agent.tools.base import ToolDefinition
from enterprise_support_agent.tools.registry import ToolRegistry, build_default_registry


def _scripted_decisions(specifications: list[dict[str, Any]]) -> list[ModelDecision]:
    decisions: list[ModelDecision] = []
    for item in specifications:
        if item["kind"] == "final":
            decisions.append(ModelDecision.final(item["content"]))
        else:
            decisions.append(ModelDecision.call(item["name"], item.get("arguments", {})))
    return decisions


def _scenario_registry(base: ToolRegistry, scenario: str | None) -> ToolRegistry:
    if scenario is None:
        return base
    open_schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    if scenario == "flaky_tool":
        attempts = {"count": 0}

        def flaky(value: int) -> dict[str, Any]:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise OSError("transient simulated dependency failure")
            return {"value": value, "recovered": True}

        base.register(ToolDefinition("flaky_tool", "Eval-only transient tool", open_schema, flaky))
    elif scenario == "always_fail":
        def fail(value: int) -> dict[str, Any]:
            raise ValueError(f"permanent simulated failure for {value}")

        base.register(ToolDefinition("always_fail", "Eval-only failing tool", open_schema, fail))
    elif scenario == "slow_tool":
        def slow(value: int) -> dict[str, Any]:
            time.sleep(0.05)
            return {"value": value}

        base.register(ToolDefinition("slow_tool", "Eval-only slow tool", open_schema, slow))
    elif scenario == "constant_tool":
        def constant(value: int) -> dict[str, Any]:
            del value
            return {"constant": True}

        base.register(ToolDefinition("constant_tool", "Eval-only no-progress tool", open_schema, constant))
    return base


def _rag_documents(state) -> set[str]:  # type: ignore[no-untyped-def]
    documents: set[str] = set()
    for item in state.tool_history:
        if item.tool_name != "search_policy" or not item.ok:
            continue
        for result in item.observation.get("data", {}).get("results", []):
            documents.add(result["document_id"])
    return documents


def _score_task(task: dict[str, Any], state) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    expected_tools = task.get("expected_tools", [])
    actual_tools = [item.tool_name for item in state.tool_history]
    answer = (state.final_answer or "").lower()
    answer_checks = {needle: needle.lower() in answer for needle in task.get("answer_contains", [])}
    expected_errors = set(task.get("expected_error_types", []))
    actual_errors = {error.error_type for error in state.errors}
    expected_documents = set(task.get("relevant_documents", []))
    retrieved_documents = _rag_documents(state)
    recall = (
        len(expected_documents & retrieved_documents) / len(expected_documents)
        if expected_documents
        else None
    )
    tool_selection_correct = actual_tools == expected_tools
    stop_correct = state.stop_reason == task.get("expected_stop_reason", "completed")
    errors_correct = expected_errors.issubset(actual_errors)
    task_success = tool_selection_correct and stop_correct and errors_correct and all(answer_checks.values())
    return {
        "id": task["id"],
        "category": task["category"],
        "success": task_success,
        "tool_selection_correct": tool_selection_correct,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "stop_reason": state.stop_reason,
        "expected_stop_reason": task.get("expected_stop_reason", "completed"),
        "answer_checks": answer_checks,
        "expected_error_types": sorted(expected_errors),
        "actual_error_types": sorted(actual_errors),
        "turns": state.turn_count,
        "latency_ms": round(state.latency_ms, 3),
        "tool_calls": len(state.tool_history),
        "successful_tool_calls": sum(item.ok for item in state.tool_history),
        "rag_recall_at_k": recall,
        "retrieved_documents": sorted(retrieved_documents),
        "trace_id": state.trace_id,
    }


def run_evaluation(
    dataset_path: Path,
    reports_directory: Path,
    trace_enabled: bool = False,
) -> tuple[dict[str, Any], Path, Path]:
    tasks = json.loads(dataset_path.read_text(encoding="utf-8"))
    task_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="esa-eval-") as temporary:
        temporary_path = Path(temporary)
        for task in tasks:
            settings = Settings()
            overrides = task.get("settings", {})
            if overrides:
                settings = replace(settings, **overrides)
            if trace_enabled:
                settings = replace(settings, logs_path=reports_directory / "traces")
            registry = build_default_registry(settings, tickets_path=temporary_path / "tickets.jsonl")
            registry = _scenario_registry(registry, task.get("scenario"))
            if "script" in task:
                model = ScriptedLLM(_scripted_decisions(task["script"]))
            else:
                model = MockLLM()
            state = EnterpriseSupportAgent(
                settings=settings,
                model=model,
                registry=registry,
                trace_enabled=trace_enabled,
            ).run(task["input"])
            task_results.append(_score_task(task, state))

    task_count = len(task_results)
    total_tool_calls = sum(item["tool_calls"] for item in task_results)
    rag_values = [item["rag_recall_at_k"] for item in task_results if item["rag_recall_at_k"] is not None]
    metrics = {
        "task_count": task_count,
        "task_success_rate": sum(item["success"] for item in task_results) / task_count,
        "tool_selection_accuracy": sum(item["tool_selection_correct"] for item in task_results) / task_count,
        "tool_call_success_rate": (
            sum(item["successful_tool_calls"] for item in task_results) / total_tool_calls
            if total_tool_calls
            else 0.0
        ),
        "average_turns": sum(item["turns"] for item in task_results) / task_count,
        "failure_rate": sum(item["stop_reason"] != "completed" for item in task_results) / task_count,
        "average_latency_ms": sum(item["latency_ms"] for item in task_results) / task_count,
        "rag_recall_at_k": sum(rag_values) / len(rag_values) if rag_values else None,
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path.relative_to(PROJECT_ROOT)),
        "model_provider": "mock_and_scripted_offline",
        "metrics": metrics,
        "tasks": task_results,
    }
    reports_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = reports_directory / f"eval_report_{stamp}.json"
    markdown_path = reports_directory / f"eval_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")
    (reports_directory / "example_eval_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (reports_directory / "example_eval_report.md").write_text(_markdown_report(report), encoding="utf-8")
    return report, json_path, markdown_path


def _markdown_report(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Enterprise Support Agent Evaluation",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Tasks | {metrics['task_count']} |",
        f"| Task Success Rate | {metrics['task_success_rate']:.2%} |",
        f"| Tool Selection Accuracy | {metrics['tool_selection_accuracy']:.2%} |",
        f"| Tool Call Success Rate | {metrics['tool_call_success_rate']:.2%} |",
        f"| Average Turns | {metrics['average_turns']:.3f} |",
        f"| Failure Rate | {metrics['failure_rate']:.2%} |",
        f"| Average Latency | {metrics['average_latency_ms']:.3f} ms |",
        f"| RAG Recall@K | {metrics['rag_recall_at_k']:.2%} |",
        "",
        "## Per-task results",
        "",
        "| ID | Category | Success | Tools | Stop | Turns | Latency ms |",
        "|---|---|---:|---|---|---:|---:|",
    ]
    for item in report["tasks"]:
        tools = " -> ".join(item["actual_tools"]) or "none"
        lines.append(
            f"| {item['id']} | {item['category']} | {'yes' if item['success'] else 'no'} | "
            f"{tools} | {item['stop_reason']} | {item['turns']} | {item['latency_ms']:.3f} |"
        )
    lines.append("")
    lines.append("Metrics above are computed from this run; they are not hand-authored benchmark claims.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the Enterprise Support Agent")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "evals" / "dataset.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--traces", action="store_true", help="Persist per-task traces")
    parser.add_argument(
        "--min-task-success",
        type=float,
        default=0.0,
        help="Exit non-zero when task success rate falls below this value (0.0 to 1.0)",
    )
    args = parser.parse_args()
    if not 0.0 <= args.min_task_success <= 1.0:
        parser.error("--min-task-success must be between 0.0 and 1.0")
    report, json_path, markdown_path = run_evaluation(args.dataset, args.output, args.traces)
    print(json.dumps(report["metrics"], indent=2))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0 if report["metrics"]["task_success_rate"] >= args.min_task_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
