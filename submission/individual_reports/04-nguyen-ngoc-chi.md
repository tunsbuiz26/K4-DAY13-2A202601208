# Báo cáo cá nhân - Nguyễn Ngọc Chi - MSSV 2A202602024

## Vai trò và mục tiêu

Vai trò chính: **Incident, Report & Demo**, đồng thời sở hữu phần SLO/alert/runbook. Mục tiêu là phát hiện sự cố từ triệu chứng người dùng, nối bằng chứng Metrics → Traces → Logs và đề xuất fix/phòng ngừa có thể hành động.

## Phần việc thực hiện

- Chốt SLO 28 ngày: latency P95 ≤ 3.000 ms, error rate ≤ 2%, daily cost ≤ 2,50 USD, quality mean ≥ 0,75.
- Hoàn thiện ba alert symptom-based với severity, duration, minimum traffic, owner và runbook.
- Viết runbook ba bước đầu: xác định cửa sổ metrics, mở trace/span bất thường, dùng correlation ID xác nhận log.
- Chạy challenge chính thức `day13-k4-observability-v1`, scenario `rag_slow`, feature `monitoring`.
- So sánh baseline/incident và chọn correlation ID đại diện `req-91e29444`.
- Xác định root cause và preventive action, bao gồm ảnh hưởng head-of-line blocking do `time.sleep` trong đường xử lý async.

## File và evidence

- File sở hữu: `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`, nội dung incident trong `submission/REPORT.md`.
- Investigation: `submission/evidence/challenge-investigation.md`.
- Correlation chain: `submission/evidence/correlation-chain.json`.
- Dashboard screenshot: `submission/evidence/dashboard.png`.

## Kết quả điều tra

- Baseline P95: 150 ms.
- Incident P95: 2.654 ms, tăng 17,7 lần và vượt ngưỡng challenge 2.000 ms.
- Retrieval P95: 2.500 ms; generation P95: 150 ms.
- Root cause trực tiếp: incident `rag_slow` tại retrieval.
- Fix: tắt incident, dùng async/thread pool cho blocking retrieval, timeout/circuit breaker và concurrency limit.
- Preventive measure: alert P95, span-level latency, concurrent regression test và theo dõi P50/P95/P99.

## Giải thích kỹ thuật

**Alert tốt cần gì?** Condition gắn với SLI/SLO người dùng, duration chống nhiễu, severity phản ánh impact, minimum traffic khi mẫu nhỏ, owner rõ và runbook có mitigation.

**Vì sao mở metrics trước trace?** Metrics cho biết có sự cố hay không, phạm vi thời gian và loại triệu chứng. Trace dùng để localize; log dùng để giải thích. Mở log trước dễ bị chìm trong event rời rạc.

## Hạn chế và việc còn lại

Trace ID thật chưa có vì tracing bị tắt khi thiếu Langfuse key. Cần chụp waterfall sau khi cấu hình project thật và cập nhật evidence. Commit/PR cá nhân cũng chưa được tạo.
