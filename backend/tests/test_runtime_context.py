import json

from app.services.runtime_context import read_logs


def test_log_parsing_assigns_stable_evidence_ids(tmp_path):
    payload = {
        "log_sequence": 17,
        "timestamp": "2026-08-15T10:00:00Z",
        "level": "ERROR",
        "service": "payment-service",
        "request_id": "req-1",
        "event": "payment.charge.failed",
        "duration_ms": 42.0,
        "status_code": 503,
        "error_type": "ConnectionPoolExhausted",
        "deployment_version": "2.4.1",
    }
    (tmp_path / "payment-service.jsonl").write_text(json.dumps(payload) + "\n")
    logs = read_logs(tmp_path)
    assert logs[0].evidence_id == "log:payment-service:17"
    assert logs[0].error_type == "ConnectionPoolExhausted"

