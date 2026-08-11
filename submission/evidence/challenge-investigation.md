# Evidence điều tra challenge

- Challenge ID: `day13-k4-observability-v1`
- Incident: `rag_slow`
- Feature bị ảnh hưởng: `monitoring`
- Ngưỡng challenge: `2000 ms`
- Baseline P95 (ngoài các cửa sổ incident): `156 ms`
- Incident P95: `2659 ms` (`17.0x` baseline)
- Retrieval P95: `2500 ms`
- Generation P95: `150 ms`
- Correlation ID đại diện: `req-8f674f48`
- Trace ID: chưa có trong môi trường hiện tại vì `tracing_enabled=false`; không tạo ID giả.

## Chuỗi Metrics → Traces → Logs

1. Metrics: P95 tăng từ `156 ms` lên `2659 ms`, vượt ngưỡng challenge `2000 ms`.
2. Traces: mã đã tạo waterfall `agent_run → rag_retrieval → llm_generation`; cần Langfuse key thật để chụp trace ID/runtime waterfall.
3. Logs: cùng correlation ID `req-8f674f48`, `retrieval_completed.latency_ms=2500` trong khi `generation_completed.latency_ms=150`.

## Kết luận

Root cause trực tiếp là incident `rag_slow` thêm độ trễ vào retrieval. Vì retrieval đồng bộ dùng `time.sleep` bên trong endpoint async, concurrency còn gây head-of-line blocking ở event loop, khiến latency phía client tăng theo hàng đợi.

Fix action: tắt incident, thay blocking I/O bằng client async hoặc chạy retrieval đồng bộ trong thread pool, đặt timeout/circuit breaker và giới hạn concurrency.

Preventive measure: alert P95, span-level latency cho retrieval, load test đồng thời, dashboard so sánh P50/P95/P99 và regression test bảo vệ latency budget.
