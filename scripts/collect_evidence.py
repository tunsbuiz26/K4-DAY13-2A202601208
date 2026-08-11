from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.challenge import load_challenge
from app.cli import configure_utf8_stdio
from scripts.generate_dashboard import load_records, percentile


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _incident_windows(records: list[dict[str, Any]], incident: str) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    active_index: int | None = None
    for index, record in enumerate(records):
        name = (record.get("payload") or {}).get("name") if isinstance(record.get("payload"), dict) else None
        if record.get("event") == "incident_enabled" and name == incident:
            active_index = index
        elif record.get("event") == "incident_disabled" and name == incident and active_index is not None:
            windows.append((active_index, index))
            active_index = None
    return windows


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect(log_path: Path, evidence_dir: Path, with_tests: bool) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(log_path)
    challenge = load_challenge(REPO_ROOT / "config" / "challenge.json")
    windows = _incident_windows(records, challenge.incident)
    if not windows:
        raise RuntimeError(f"Không tìm thấy cửa sổ incident {challenge.incident} trong log")
    start, end = windows[-1]
    incident_records = records[start : end + 1]

    incident_indexes = {
        index
        for window_start, window_end in windows
        for index in range(window_start, window_end + 1)
    }
    baseline_latencies = [
        float(record.get("latency_ms", 0) or 0)
        for index, record in enumerate(records[:start])
        if index not in incident_indexes and record.get("event") == "response_sent"
    ]
    challenge_responses = [
        record
        for record in incident_records
        if record.get("event") == "response_sent"
        and record.get("feature") == challenge.affected_feature
    ]
    incident_latencies = [float(record.get("latency_ms", 0) or 0) for record in challenge_responses]
    retrieval_records = [
        record for record in incident_records if record.get("event") == "retrieval_completed"
    ]
    generation_records = [
        record for record in incident_records if record.get("event") == "generation_completed"
    ]
    representative = max(challenge_responses, key=lambda record: record.get("latency_ms", 0))
    correlation_id = representative["correlation_id"]
    correlated_records = [
        record for record in incident_records if record.get("correlation_id") == correlation_id
    ]

    pii_record = next(
        (
            record
            for record in records
            if "[REDACTED_" in json.dumps(record, ensure_ascii=False)
            and record.get("event") == "request_received"
        ),
        None,
    )
    if pii_record is not None:
        _write_json(evidence_dir / "pii-redaction.json", pii_record)
    _write_json(evidence_dir / "correlation-chain.json", correlated_records)

    validate_logs = _run([sys.executable, "scripts/validate_logs.py"])
    (evidence_dir / "validate-logs.txt").write_text(
        validate_logs.stdout + validate_logs.stderr, encoding="utf-8"
    )
    validate_dashboard = _run([sys.executable, "scripts/validate_dashboard.py"])
    (evidence_dir / "validate-dashboard.txt").write_text(
        validate_dashboard.stdout + validate_dashboard.stderr, encoding="utf-8"
    )
    if with_tests:
        tests = _run([sys.executable, "-m", "pytest", "-q"])
        (evidence_dir / "pytest.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")

    baseline_p95 = percentile(baseline_latencies, 95)
    incident_p95 = percentile(incident_latencies, 95)
    retrieval_p95 = percentile(
        [float(record.get("latency_ms", 0) or 0) for record in retrieval_records], 95
    )
    generation_p95 = percentile(
        [float(record.get("latency_ms", 0) or 0) for record in generation_records], 95
    )
    multiplier = incident_p95 / baseline_p95 if baseline_p95 else 0.0
    investigation = f"""# Evidence điều tra challenge

- Challenge ID: `{challenge.challenge_id}`
- Incident: `{challenge.incident}`
- Feature bị ảnh hưởng: `{challenge.affected_feature}`
- Ngưỡng challenge: `{challenge.latency_threshold_ms} ms`
- Baseline P95 (ngoài các cửa sổ incident): `{baseline_p95:.0f} ms`
- Incident P95: `{incident_p95:.0f} ms` (`{multiplier:.1f}x` baseline)
- Retrieval P95: `{retrieval_p95:.0f} ms`
- Generation P95: `{generation_p95:.0f} ms`
- Correlation ID đại diện: `{correlation_id}`
- Trace ID: chưa có trong môi trường hiện tại vì `tracing_enabled=false`; không tạo ID giả.

## Chuỗi Metrics → Traces → Logs

1. Metrics: P95 tăng từ `{baseline_p95:.0f} ms` lên `{incident_p95:.0f} ms`, vượt ngưỡng challenge `{challenge.latency_threshold_ms} ms`.
2. Traces: mã đã tạo waterfall `agent_run → rag_retrieval → llm_generation`; cần Langfuse key thật để chụp trace ID/runtime waterfall.
3. Logs: cùng correlation ID `{correlation_id}`, `retrieval_completed.latency_ms={retrieval_p95:.0f}` trong khi `generation_completed.latency_ms={generation_p95:.0f}`.

## Kết luận

Root cause trực tiếp là incident `rag_slow` thêm độ trễ vào retrieval. Vì retrieval đồng bộ dùng `time.sleep` bên trong endpoint async, concurrency còn gây head-of-line blocking ở event loop, khiến latency phía client tăng theo hàng đợi.

Fix action: tắt incident, thay blocking I/O bằng client async hoặc chạy retrieval đồng bộ trong thread pool, đặt timeout/circuit breaker và giới hạn concurrency.

Preventive measure: alert P95, span-level latency cho retrieval, load test đồng thời, dashboard so sánh P50/P95/P99 và regression test bảo vệ latency budget.
"""
    (evidence_dir / "challenge-investigation.md").write_text(investigation, encoding="utf-8")

    pending = """# Evidence Langfuse còn cần thu thập

Môi trường chạy hiện tại không có `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY`, vì vậy `tracing_enabled=false`. Không có trace ID hoặc ảnh prompt version nào được tạo giả.

Sau khi nhóm điền key thật vào `.env` (không commit), cần:

1. Tạo prompt `day13-chat` version 1 với labels `baseline`, `production`.
2. Tạo version 2 với label `candidate`.
3. Chạy cùng input với `baseline` và `candidate`; lưu hai trace ID có `prompt_name`, `prompt_label`, `prompt_version`.
4. Chuyển `production` sang version 2, chạy một request, rồi rollback về version 1.
5. Lưu ảnh danh sách 10+ traces, waterfall và trước/sau rollback vào thư mục này; cập nhật REPORT.md.
"""
    (evidence_dir / "langfuse-pending.md").write_text(pending, encoding="utf-8")

    return {
        "baseline_p95_ms": baseline_p95,
        "incident_p95_ms": incident_p95,
        "retrieval_p95_ms": retrieval_p95,
        "generation_p95_ms": generation_p95,
        "correlation_id": correlation_id,
        "validate_logs_returncode": validate_logs.returncode,
        "validate_dashboard_returncode": validate_dashboard.returncode,
    }


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Thu thập evidence có thể kiểm chứng từ local runtime")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument(
        "--evidence-dir", type=Path, default=REPO_ROOT / "submission" / "evidence"
    )
    parser.add_argument("--with-tests", action="store_true")
    args = parser.parse_args()
    summary = collect(args.logs, args.evidence_dir, args.with_tests)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
