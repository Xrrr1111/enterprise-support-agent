# Enterprise Support Agent Evaluation

Generated: 2026-08-17T13:35:15.382130+00:00

## Metrics

| Metric | Result |
|---|---:|
| Tasks | 38 |
| Task Success Rate | 100.00% |
| Tool Selection Accuracy | 100.00% |
| Tool Call Success Rate | 91.84% |
| Average Turns | 2.237 |
| Failure Rate | 7.89% |
| Average Latency | 0.996 ms |
| RAG Recall@K | 100.00% |

## Per-task results

| ID | Category | Success | Tools | Stop | Turns | Latency ms |
|---|---|---:|---|---|---:|---:|
| order_01 | order_query | yes | query_order | completed | 2 | 1.139 |
| order_02 | order_query | yes | query_order | completed | 2 | 0.478 |
| order_03 | order_query | yes | query_order | completed | 2 | 0.512 |
| order_04 | order_query | yes | query_order | completed | 2 | 0.409 |
| order_05 | order_query | yes | query_order | completed | 2 | 0.454 |
| order_06 | order_query | yes | query_order | completed | 2 | 0.438 |
| order_07 | order_query | yes | query_order | completed | 2 | 0.423 |
| order_08 | order_query | yes | query_order | completed | 2 | 0.438 |
| rag_01 | rag_policy | yes | search_policy | completed | 2 | 0.759 |
| rag_02 | rag_policy | yes | search_policy | completed | 2 | 0.613 |
| rag_03 | rag_policy | yes | search_policy | completed | 2 | 0.572 |
| rag_04 | rag_policy | yes | search_policy | completed | 2 | 1.091 |
| rag_05 | rag_policy | yes | search_policy | completed | 2 | 0.577 |
| rag_06 | rag_policy | yes | search_policy | completed | 2 | 0.593 |
| rag_07 | rag_policy | yes | search_policy | completed | 2 | 0.628 |
| rag_08 | rag_policy | yes | search_policy | completed | 2 | 0.718 |
| combo_01 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.045 |
| combo_02 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 0.948 |
| combo_03 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.018 |
| combo_04 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.091 |
| combo_05 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.101 |
| ticket_01 | ticket | yes | create_ticket | completed | 2 | 0.779 |
| ticket_02 | ticket | yes | create_ticket | completed | 2 | 0.799 |
| ticket_03 | ticket | yes | query_order -> create_ticket | completed | 3 | 1.390 |
| ticket_04 | ticket | yes | search_policy -> create_ticket | completed | 3 | 1.308 |
| calc_01 | calculator | yes | calculator | completed | 2 | 0.356 |
| calc_02 | calculator | yes | calculator | completed | 2 | 0.377 |
| calc_03 | calculator | yes | calculator | completed | 2 | 0.291 |
| missing_01 | no_result | yes | query_order -> create_ticket | completed | 3 | 1.214 |
| missing_02 | no_result | yes | query_order -> create_ticket | completed | 3 | 1.127 |
| reliability_01 | invalid_tool | yes | does_not_exist | completed | 2 | 0.054 |
| reliability_02 | invalid_arguments | yes | query_order | completed | 2 | 0.051 |
| reliability_03 | tool_retry | yes | flaky_tool | completed | 2 | 0.393 |
| reliability_04 | tool_failure | yes | always_fail | completed | 2 | 0.195 |
| reliability_05 | timeout | yes | slow_tool | completed | 2 | 13.015 |
| reliability_06 | loop | yes | query_order | repeated_tool_call | 2 | 0.466 |
| reliability_07 | max_turns | yes | query_order -> query_order | max_turns | 2 | 0.624 |
| reliability_08 | no_progress | yes | constant_tool -> constant_tool | no_progress | 2 | 0.351 |

Metrics above are computed from this run; they are not hand-authored benchmark claims.