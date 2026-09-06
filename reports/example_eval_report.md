# Enterprise Support Agent Evaluation

Generated: 2026-09-06T09:18:56.392709+00:00

## Metrics

| Metric | Result |
|---|---:|
| Tasks | 38 |
| Task Success Rate | 100.00% |
| Tool Selection Accuracy | 100.00% |
| Tool Call Success Rate | 91.84% |
| Average Turns | 2.237 |
| Failure Rate | 7.89% |
| Average Latency | 1.505 ms |
| RAG Recall@K | 100.00% |

## Per-task results

| ID | Category | Success | Tools | Stop | Turns | Latency ms |
|---|---|---:|---|---|---:|---:|
| order_01 | order_query | yes | query_order | completed | 2 | 1.140 |
| order_02 | order_query | yes | query_order | completed | 2 | 0.476 |
| order_03 | order_query | yes | query_order | completed | 2 | 0.560 |
| order_04 | order_query | yes | query_order | completed | 2 | 0.438 |
| order_05 | order_query | yes | query_order | completed | 2 | 0.621 |
| order_06 | order_query | yes | query_order | completed | 2 | 0.491 |
| order_07 | order_query | yes | query_order | completed | 2 | 0.480 |
| order_08 | order_query | yes | query_order | completed | 2 | 0.582 |
| rag_01 | rag_policy | yes | search_policy | completed | 2 | 0.965 |
| rag_02 | rag_policy | yes | search_policy | completed | 2 | 0.617 |
| rag_03 | rag_policy | yes | search_policy | completed | 2 | 0.634 |
| rag_04 | rag_policy | yes | search_policy | completed | 2 | 1.214 |
| rag_05 | rag_policy | yes | search_policy | completed | 2 | 0.651 |
| rag_06 | rag_policy | yes | search_policy | completed | 2 | 0.745 |
| rag_07 | rag_policy | yes | search_policy | completed | 2 | 0.658 |
| rag_08 | rag_policy | yes | search_policy | completed | 2 | 0.602 |
| combo_01 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.399 |
| combo_02 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.297 |
| combo_03 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.078 |
| combo_04 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.092 |
| combo_05 | order_and_policy | yes | query_order -> search_policy | completed | 3 | 1.135 |
| ticket_01 | ticket | yes | create_ticket | completed | 2 | 0.841 |
| ticket_02 | ticket | yes | create_ticket | completed | 2 | 6.059 |
| ticket_03 | ticket | yes | query_order -> create_ticket | completed | 3 | 5.963 |
| ticket_04 | ticket | yes | search_policy -> create_ticket | completed | 3 | 6.424 |
| calc_01 | calculator | yes | calculator | completed | 2 | 0.369 |
| calc_02 | calculator | yes | calculator | completed | 2 | 0.356 |
| calc_03 | calculator | yes | calculator | completed | 2 | 0.463 |
| missing_01 | no_result | yes | query_order -> create_ticket | completed | 3 | 6.902 |
| missing_02 | no_result | yes | query_order -> create_ticket | completed | 3 | 5.610 |
| reliability_01 | invalid_tool | yes | does_not_exist | completed | 2 | 0.058 |
| reliability_02 | invalid_arguments | yes | query_order | completed | 2 | 0.059 |
| reliability_03 | tool_retry | yes | flaky_tool | completed | 2 | 0.343 |
| reliability_04 | tool_failure | yes | always_fail | completed | 2 | 0.240 |
| reliability_05 | timeout | yes | slow_tool | completed | 2 | 5.278 |
| reliability_06 | loop | yes | query_order | repeated_tool_call | 2 | 0.412 |
| reliability_07 | max_turns | yes | query_order -> query_order | max_turns | 2 | 0.543 |
| reliability_08 | no_progress | yes | constant_tool -> constant_tool | no_progress | 2 | 0.379 |

Metrics above are computed from this run; they are not hand-authored benchmark claims.