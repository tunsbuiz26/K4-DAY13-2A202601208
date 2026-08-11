from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.logging_config import scrub_event
from app.main import app
from app.pii import scrub_text


def test_generated_correlation_id_is_propagated_to_response() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_valid_upstream_correlation_id_is_preserved() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "req-A1B2C3D4"})

    assert response.headers["x-request-id"] == "req-a1b2c3d4"


def test_logging_processor_scrubs_nested_values_and_exception_text() -> None:
    event = {
        "event": "request_failed",
        "payload": {"contacts": ["student@example.com", {"phone": "090 123 4567"}]},
        "exception": "Failed for passport B1234567",
    }

    scrubbed = scrub_event(None, "error", event)

    assert "student@example.com" not in str(scrubbed)
    assert "090 123 4567" not in str(scrubbed)
    assert "B1234567" not in str(scrubbed)


def test_scrub_passport_and_labeled_address() -> None:
    text = "Hộ chiếu: B1234567; Địa chỉ: 12 Nguyễn Trãi, Hà Nội"
    scrubbed = scrub_text(text)

    assert "B1234567" not in scrubbed
    assert "12 Nguyễn Trãi" not in scrubbed
    assert "REDACTED_PASSPORT" in scrubbed
    assert "REDACTED_ADDRESS_VN" in scrubbed
