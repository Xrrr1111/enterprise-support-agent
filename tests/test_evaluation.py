from __future__ import annotations

import json

from enterprise_support_agent.config import PROJECT_ROOT
from evals.evaluate import run_evaluation


def test_eval_dataset_has_at_least_30_diverse_tasks() -> None:
    tasks = json.loads((PROJECT_ROOT / "evals" / "dataset.json").read_text(encoding="utf-8"))
    assert len(tasks) >= 30
    categories = {task["category"] for task in tasks}
    assert {"order_query", "rag_policy", "order_and_policy", "tool_failure", "loop"} <= categories


def test_evaluation_computes_and_writes_reports(tmp_path) -> None:
    report, json_path, markdown_path = run_evaluation(
        PROJECT_ROOT / "evals" / "dataset.json", tmp_path, trace_enabled=False
    )
    metrics = report["metrics"]
    assert metrics["task_count"] >= 30
    assert 0 <= metrics["task_success_rate"] <= 1
    assert 0 <= metrics["tool_call_success_rate"] <= 1
    assert 0 <= metrics["rag_recall_at_k"] <= 1
    assert json_path.is_file()
    assert markdown_path.is_file()
    assert (tmp_path / "example_eval_report.json").is_file()
    assert "Task Success Rate" in markdown_path.read_text(encoding="utf-8")


def test_failure_rate_is_derived_from_task_results(tmp_path) -> None:
    report, _, _ = run_evaluation(PROJECT_ROOT / "evals" / "dataset.json", tmp_path)
    expected = sum(item["stop_reason"] != "completed" for item in report["tasks"]) / len(report["tasks"])
    assert report["metrics"]["failure_rate"] == expected
