import io
import json

from loguru import logger

from app.core.logging import configure_logging


def test_json_log_has_required_fields():
    sink = io.StringIO()
    configure_logging(sink=sink, level="INFO")
    logger.bind(trace_id="abc123", user_id=42).info("hello")
    line = sink.getvalue().strip().splitlines()[-1]
    record = json.loads(line)
    assert record["message"] == "hello"
    assert record["trace_id"] == "abc123"
    assert record["user_id"] == 42
    assert record["level"] == "INFO"
