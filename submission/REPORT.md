# Báo cáo nhóm Day 13 - AI Observability

## 1. Thông tin nhóm

- Tên nhóm: K4-DAY13-2A202601208
- Repository URL: https://github.com/tunsbuiz26/K4-DAY13-2A202601208
- Commit SHA hiện có: `0e60fa913a6bca3bba4aa4bcf6ab373c7bef5b30`
- Trạng thái Git: Nguyễn Bùi Anh Tuấn đã commit phần Tracing & Prompt Version bằng tài khoản `tunsbuiz26`; các phần còn lại và file nhóm vẫn ở working tree, chưa được đẩy. Nhóm phải commit bằng đúng tài khoản người thực hiện trước khi nộp và thay SHA ở trên bằng SHA cuối.

Nhóm giữ đúng bốn vai trò chính của đề bài; Nguyễn Ngọc Chi và Trần Thanh Bình cùng chia sẻ vai trò Incident, Report & Demo.

| Thành viên | Mã sinh viên | Vai trò chính | Phạm vi sở hữu |
|---|---|---|---|
| Đào Chí Hiển | 2A202601066 | Logging & PII | Correlation ID, structured logging, context metadata, redaction, test bảo mật log |
| Nguyễn Bùi Anh Tuấn | 2A202601208 | Tracing & Prompt Version | Waterfall span, metadata trace/generation, prompt fallback/version/label, quy trình rollback |
| Nguyễn Việt Anh | 2A202601144 | Dashboard, SLO & Alert | Metrics, dashboard 6 panel, validator, HTML/PNG runtime dashboard |
| Nguyễn Ngọc Chi | 2A202602024 | Incident, Report & Demo | SLO, alert rules, runbook, điều tra challenge và biện pháp phòng ngừa |
| Trần Thanh Bình | 2A202601174 | Incident, Report & Demo (đồng sở hữu) | QA, automation evidence, báo cáo, checklist demo và kiểm tra nộp bài |

Chi tiết phân công và tiêu chí hoàn thành nằm tại [`WORK_ASSIGNMENT.md`](WORK_ASSIGNMENT.md).

## 2. Kết quả kỹ thuật

- `python scripts/validate_logs.py`: **100/100** trên 66 log records; 0 record thiếu field bắt buộc; 0 record thiếu enrichment; 25 correlation ID; 0 PII leak.
- `python scripts/validate_dashboard.py`: **HỢP LỆ 6/6 panel**.
- `python -m pytest -q`: **29 passed**.
- Dashboard runtime: [`evidence/dashboard.html`](evidence/dashboard.html); ảnh evidence: [`evidence/dashboard.png`](evidence/dashboard.png); snapshot máy đọc: [`evidence/dashboard-metrics.json`](evidence/dashboard-metrics.json).
- Tổng trace Langfuse đã xác minh: **0 trong môi trường hiện tại**, vì không có `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY`. Không tạo trace ID hoặc screenshot giả. Checklist còn lại nằm tại [`evidence/langfuse-pending.md`](evidence/langfuse-pending.md).

## 3. Logging, correlation ID và PII

Middleware xóa contextvars ở đầu/cuối request, chỉ chấp nhận `x-request-id` đúng dạng `req-<8 hex>` hoặc sinh ID mới, bind ID vào structlog và trả lại `x-request-id` cùng `x-response-time-ms` ở response.

Endpoint `/chat` bind các field `user_id_hash`, `session_id`, `feature`, `model`, `env` trước `request_received`. Processor redaction chạy sau khi format exception nhưng trước cả file sink và JSON renderer; mọi string lồng trong dict/list/tuple đều được scrub. Pattern hiện bao phủ email, điện thoại Việt Nam, CCCD, thẻ thanh toán, hộ chiếu và địa chỉ có nhãn.

- Evidence correlation chain: [`evidence/correlation-chain.json`](evidence/correlation-chain.json), đại diện `req-91e29444`.
- Evidence redaction: [`evidence/pii-redaction.json`](evidence/pii-redaction.json).
- Kết quả validator: [`evidence/validate-logs.txt`](evidence/validate-logs.txt).

## 4. Tracing và prompt versioning

Waterfall trong mã gồm `agent_run` → `rag_retrieval` → `llm_generation`. Trace metadata ghi `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`; generation metadata bổ sung doc count, query preview đã redact, token usage, cost và managed prompt link khi Langfuse khả dụng.

- Prompt name: `day13-chat`.
- Local fallback đã xác minh: version `local-v1`, label theo `LANGFUSE_PROMPT_LABEL`, `prompt_source=local` hoặc `local-fallback`; không giả là managed prompt.
- Baseline/candidate version và trace ID: chưa thể tạo trong môi trường không có key.
- Rollback `production`: chưa thể thực hiện trên project Langfuse thật; thực hiện đúng checklist trong [`evidence/langfuse-pending.md`](evidence/langfuse-pending.md) trước khi nộp.

## 5. Dashboard, SLO và alert

Dashboard dùng `data/logs.jsonl` làm nguồn chuẩn và hiển thị đúng sáu nhóm: latency P50/P95/P99, traffic, error rate/breakdown, cost, input/output token và quality proxy. Time range là 60 phút, refresh 30 giây, mỗi panel có đơn vị và SLO line theo `config/dashboard.yaml`.

Các SLO chính:

- Latency P95 ≤ 3.000 ms; mục tiêu 99,5% trong 28 ngày.
- Error rate ≤ 2%; mục tiêu 99% trong 28 ngày.
- Daily cost ≤ 2,50 USD.
- Quality proxy trung bình ≥ 0,75.

Ba alert symptom-based đã hoàn thiện: tail latency (high), error rate (critical) và quality degradation (medium). Mỗi alert có duration, minimum traffic khi cần, owner, mitigation và chuỗi kiểm tra Metrics → Traces → Logs tại [`../docs/alerts.md`](../docs/alerts.md).

## 6. Điều tra challenge chính thức

- Challenge ID: `day13-k4-observability-v1`.
- Scenario: `rag_slow`; feature bị ảnh hưởng: `monitoring`; ngưỡng challenge: 2.000 ms.
- Triệu chứng metrics: P95 ngoài incident là 150 ms; trong incident là 2.654 ms, tăng 17,7 lần và vượt ngưỡng challenge.
- Correlation ID đại diện: `req-91e29444`.
- Log cùng ID: `retrieval_completed.latency_ms=2500`, `generation_completed.latency_ms=150`, tổng response 2.654 ms.
- Trace ID: chờ Langfuse key thật; mã đã instrument waterfall nhưng không tạo ID giả.
- Root cause: `rag_slow` chèn 2,5 giây vào retrieval. `time.sleep` chạy trong đường xử lý async còn block event loop, nên concurrency tạo head-of-line blocking và làm latency phía client tăng theo hàng đợi.
- Fix action: tắt incident; thay blocking I/O bằng async client hoặc thread pool; đặt timeout/circuit breaker và giới hạn concurrency.
- Preventive measure: alert P95, span-level retrieval latency, concurrent load test và latency regression budget.

Toàn bộ phép tính và chuỗi bằng chứng nằm tại [`evidence/challenge-investigation.md`](evidence/challenge-investigation.md).

## 7. Đóng góp cá nhân

| Thành viên | Mã sinh viên | Phần việc | Commit/PR | Báo cáo cá nhân |
|---|---|---|---|---|
| Đào Chí Hiển | 2A202601066 | Logging, correlation ID, context, PII | Chưa tạo - cần commit bằng tài khoản cá nhân | [`individual_reports/01-dao-chi-hien.md`](individual_reports/01-dao-chi-hien.md) |
| Nguyễn Bùi Anh Tuấn | 2A202601208 | Tracing waterfall, prompt metadata/version workflow | `0e60fa9` trên `main` | [`individual_reports/02-nguyen-bui-anh-tuan.md`](individual_reports/02-nguyen-bui-anh-tuan.md) |
| Nguyễn Việt Anh | 2A202601144 | Metrics, dashboard, validator, screenshot | Chưa tạo - cần commit bằng tài khoản cá nhân | [`individual_reports/03-nguyen-viet-anh.md`](individual_reports/03-nguyen-viet-anh.md) |
| Nguyễn Ngọc Chi | 2A202602024 | SLO, alerts, runbook, incident investigation | Chưa tạo - cần commit bằng tài khoản cá nhân | [`individual_reports/04-nguyen-ngoc-chi.md`](individual_reports/04-nguyen-ngoc-chi.md) |
| Trần Thanh Bình | 2A202601174 | QA, evidence automation, report, demo checklist | Chưa tạo - cần commit bằng tài khoản cá nhân | [`individual_reports/05-tran-thanh-binh.md`](individual_reports/05-tran-thanh-binh.md) |

## 8. Hạn chế và checklist trước khi nộp

1. Điền Langfuse key thật vào `.env`, tạo prompt v1/v2, thu ít nhất 10 traces, lưu waterfall và evidence rollback.
2. Mỗi thành viên tạo commit/PR đúng phần sở hữu; cập nhật link và final SHA vào báo cáo.
3. Chạy lại `pytest`, hai validator và `scripts/collect_evidence.py --with-tests`.
4. Xác nhận `.env`, key, secret và raw PII không nằm trong Git.
5. Demo theo luồng Dashboard Metrics → Langfuse Trace → JSON Logs → Root cause → Fix.
