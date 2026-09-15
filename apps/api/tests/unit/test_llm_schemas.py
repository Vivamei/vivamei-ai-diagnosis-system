from app.services.llm.base import LLMEvent, LLMRequest


def test_request_defaults():
    req = LLMRequest(task_id="01HW9", image_url="http://x")
    assert req.schema_version == "v1"
    assert req.locale == "zh-CN"
    assert req.user_hints is None


def test_request_with_hints():
    req = LLMRequest(
        task_id="t1",
        image_url="http://x",
        user_hints={"age_range": "25-35"},
        prompt_overrides={"tone": "formal"},
    )
    assert req.user_hints["age_range"] == "25-35"
    assert req.prompt_overrides["tone"] == "formal"


def test_event_phase_done_with_payload():
    e = LLMEvent(type="phase_done", phase="stype", payload={"primary": "bone"})
    assert e.phase == "stype"
    assert e.payload["primary"] == "bone"


def test_event_radar():
    e = LLMEvent(type="radar", radar={"stype": 78, "style": 82, "subzone": 74, "struct": 69})
    assert e.radar["stype"] == 78
