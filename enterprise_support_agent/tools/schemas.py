"""Canonical schemas sent to the model and enforced by the harness."""

QUERY_ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "Enterprise order identifier, for example ORD-1001.",
            "minLength": 1,
            "maxLength": 64,
        }
    },
    "required": ["order_id"],
    "additionalProperties": False,
}

SEARCH_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 2, "maxLength": 500},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
        "category": {
            "type": "string",
            "enum": ["refund", "return", "shipping", "after_sales"],
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

CREATE_TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "user_request": {"type": "string", "minLength": 2, "maxLength": 2000},
        "reason": {"type": "string", "minLength": 2, "maxLength": 500},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "idempotency_key": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128,
            "description": "Stable unique key for this escalation request; reuse it only when retrying the same operation.",
        },
    },
    "required": ["user_request", "reason", "priority", "idempotency_key"],
    "additionalProperties": False,
}

CALCULATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "expression": {"type": "string", "minLength": 1, "maxLength": 200},
    },
    "required": ["expression"],
    "additionalProperties": False,
}
