# Demo transcripts

These transcripts use the default offline `MockLLM`. Each result came through the same model-decision and tool-observation loop used by provider adapters.

## Order plus policy

```console
$ python main.py "For ORD-1002, explain the shipping policy"
Order ORD-1002 is shipped; payment is paid, shipping is in_transit, refund is not_requested, and the amount is USD 249.00. Policy guidance: Paid in-stock orders are normally handed to the carrier within 2 business days. Standard delivery usually takes 3-7 business days after dispatch. ... Sources: shipping_policy.

trace_id=<generated> stop_reason=completed turns=3
```

Expected tool path: `query_order -> search_policy -> final`.

## Human escalation

```console
$ python main.py "This is urgent: I need a human to review my complaint"
I created support ticket TKT-<generated> with high priority.

trace_id=<generated> stop_reason=completed turns=2
```

Expected tool path: `create_ticket -> final`. The ticket is appended to `data/tickets.jsonl`, which is intentionally ignored by Git.

## Safe calculation

```console
$ python main.py "Calculate: (19.99 * 2) + 5"
The calculated result is 44.98.

trace_id=<generated> stop_reason=completed turns=2
```

The calculator parses a restricted Python AST. It does not use `eval()` and rejects names, calls, containers, excessive powers, overly complex trees, and non-finite results.

## Inspecting a trace

Pass `--json` to display the complete state. Every normal CLI run also creates:

- `logs/trace_<trace_id>.jsonl`: chronological events such as model decisions, tool calls, retry attempts, observations, and the stop event.
- `logs/trace_<trace_id>.json`: the complete final state for that run.
- `logs/application.log`: a rotating operational log.
