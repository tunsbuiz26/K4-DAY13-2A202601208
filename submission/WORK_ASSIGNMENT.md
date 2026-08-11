# Phân công công việc nhóm

## Nguyên tắc

- Giữ bốn vai trò chính theo README; không tạo vai trò thứ năm chỉ để chia nhỏ đầu việc.
- Nguyễn Ngọc Chi và Trần Thanh Bình đồng sở hữu vai trò Incident, Report & Demo, nhưng có deliverable tách biệt để chấm cá nhân.
- Mỗi đầu việc có file sở hữu, tiêu chí nghiệm thu và evidence bàn giao.

| Thành viên | Vai trò | Deliverable chính | Tiêu chí nghiệm thu |
|---|---|---|---|
| Đào Chí Hiển | Logging & PII | `app/middleware.py`, `app/logging_config.py`, `app/main.py`, `app/pii.py`, test hardening | Correlation ID xuyên suốt; enrichment đủ; validator ≥80; 0 PII leak |
| Nguyễn Bùi Anh Tuấn | Tracing & Prompt Version | `app/agent.py`, `app/tracing.py`, `app/prompt_management.py`, Langfuse prompt v1/v2 | Waterfall 3 span; metadata prompt đúng; 10+ trace; evidence rollback thật |
| Nguyễn Việt Anh | Dashboard, SLO & Alert | `app/metrics.py`, `config/dashboard.yaml`, `scripts/generate_dashboard.py`, dashboard evidence | Validator 6/6; đủ 6 nhóm signal; 60 phút; đơn vị và threshold rõ |
| Nguyễn Ngọc Chi | Incident, Report & Demo | `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`, challenge analysis | Nối Metrics → Traces → Logs; root cause, fix, preventive measure có evidence |
| Trần Thanh Bình | Incident, Report & Demo (đồng sở hữu) | `scripts/collect_evidence.py`, test suite, `submission/`, security/demo checklist | Test pass; evidence tái tạo được; báo cáo không bịa trace/commit; không lộ secret |

## Điểm giao tiếp bắt buộc

1. Hiển bàn giao schema event và redaction contract cho Tuấn/Việt Anh trước khi chốt trace và dashboard.
2. Tuấn bàn giao tên span, prompt metadata và trace ID cho Chi để điều tra incident.
3. Việt Anh bàn giao P95/error/cost/quality snapshot và dashboard screenshot cho Chi/Bình.
4. Chi bàn giao root cause, fix, preventive measure và alert/runbook cho Bình.
5. Bình chạy gate cuối, đối chiếu report với Git và yêu cầu sửa sai trước demo.
