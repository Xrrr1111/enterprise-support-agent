from enterprise_support_agent.web import HTML


def test_web_demo_exposes_upload_source_and_trace_surfaces() -> None:
    assert 'id="file"' in HTML
    assert 'id="sources"' in HTML
    assert 'id="trace"' in HTML
    assert "/api/documents" in HTML
