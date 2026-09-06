import json

from enterprise_support_agent.llm.http_adapters import OllamaLLM


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def test_ollama_json_decision_calls_tool(monkeypatch) -> None:
    response = {"message": {"content": json.dumps({"kind": "tool", "tool_name": "query_order", "arguments": {"order_id": "ORD-1"}, "content": ""})}}
    monkeypatch.setattr("enterprise_support_agent.llm.http_adapters.urlopen", lambda *args, **kwargs: _JsonResponse(response))
    decision = OllamaLLM("local", "http://localhost:11434").decide([], [], "system")
    assert decision.kind == "tool_call"
    assert decision.tool_call.name == "query_order"


class _JsonResponse(_Response):
    def __init__(self, payload):
        self.payload = payload

    def read(self, *args):
        return json.dumps(self.payload).encode()
