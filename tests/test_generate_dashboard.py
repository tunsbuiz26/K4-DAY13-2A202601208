from __future__ import annotations

from scripts.generate_dashboard import (
    aggregate_dashboard,
    render_dashboard_html,
    render_dashboard_png,
)


def test_dashboard_aggregates_all_six_signal_groups() -> None:
    records = [
        {"ts": "2026-08-11T07:00:00Z", "event": "request_received"},
        {"ts": "2026-08-11T07:00:01Z", "event": "request_received"},
        {
            "ts": "2026-08-11T07:00:02Z",
            "event": "response_sent",
            "latency_ms": 200,
            "cost_usd": 0.01,
            "tokens_in": 100,
            "tokens_out": 50,
            "quality_score": 0.8,
        },
        {
            "ts": "2026-08-11T07:00:03Z",
            "event": "request_failed",
            "error_type": "TimeoutError",
        },
    ]

    metrics = aggregate_dashboard(records)

    assert metrics["traffic"]["count"] == 2
    assert metrics["errors"]["rate_pct"] == 50.0
    assert metrics["latency"]["p95"] == 200.0
    assert metrics["cost"]["total_usd"] == 0.01
    assert metrics["tokens"] == {"input": 100, "output": 50}
    assert metrics["quality"]["mean"] == 0.8


def test_dashboard_html_names_time_range_units_and_slo_lines() -> None:
    from scripts.validate_dashboard import load_dashboard_config
    from pathlib import Path
    from datetime import datetime, timezone

    contract = load_dashboard_config(Path("config/dashboard.yaml"))
    rendered = render_dashboard_html(aggregate_dashboard([]), contract, datetime.now(timezone.utc))

    assert "Time range: 60 phút" in rendered
    assert "6/6 panel" in rendered
    assert "Latency percentiles" in rendered
    assert "SLO" in rendered


def test_dashboard_png_is_rendered(tmp_path) -> None:
    from scripts.validate_dashboard import load_dashboard_config
    from pathlib import Path
    from datetime import datetime, timezone

    output = tmp_path / "dashboard.png"
    contract = load_dashboard_config(Path("config/dashboard.yaml"))
    render_dashboard_png(aggregate_dashboard([]), contract, datetime.now(timezone.utc), output)

    assert output.exists()
    assert output.stat().st_size > 10_000
