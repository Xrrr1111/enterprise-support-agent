from dataclasses import replace

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.rag.knowledge_store import MultimodalKnowledgeStore


def test_agent_answer_uses_uploaded_knowledge_and_exposes_source(settings, tmp_path) -> None:
    configured = replace(settings, knowledge_uploads_path=tmp_path / "knowledge")
    MultimodalKnowledgeStore(configured.knowledge_uploads_path).ingest(
        "member-note.md",
        "星云会员的礼盒每月一日生成订单，三个工作日内发出。".encode("utf-8"),
    )
    state = EnterpriseSupportAgent(configured, trace_enabled=False).run("请查询知识库里的星云会员礼盒安排")
    payload = state.to_dict()
    assert state.stop_reason == "completed"
    assert "星云会员" in state.final_answer
    assert payload["sources"][0]["source"] == "member-note.md"
