# Báo cáo cá nhân - Nguyễn Việt Anh - MSSV 2A202601144

## Vai trò và mục tiêu

Vai trò chính: **Dashboard, SLO & Alert**; phạm vi cá nhân tập trung vào metrics và dashboard runtime. Mục tiêu là biến `data/logs.jsonl` thành sáu panel đúng contract, có đơn vị, time range và threshold có thể kiểm chứng.

## Phần việc thực hiện

- Rà soát mapping event/field: `response_sent.latency_ms`, `request_received`, `request_failed.error_type`, `cost_usd`, `tokens_in/out`, `quality_score`.
- Xây `scripts/generate_dashboard.py` đọc JSONL, lọc cửa sổ 60 phút, tính nearest-rank P50/P95/P99, traffic, error rate, cost, token và quality mean.
- Sinh dashboard HTML tự refresh 30 giây và snapshot JSON máy đọc.
- Sinh ảnh PNG 6 panel từ cùng metrics để nộp evidence khi browser tích hợp không khả dụng.
- Hiển thị trạng thái trong/vượt ngưỡng bằng cả màu và text; giữ đúng đơn vị contract.
- Bổ sung test aggregation của cả sáu signal và test HTML/PNG output.

## File và evidence

- File sở hữu: `app/metrics.py`, `config/dashboard.yaml`, `scripts/validate_dashboard.py`, `scripts/generate_dashboard.py`, `tests/test_dashboard_validator.py`, `tests/test_generate_dashboard.py`.
- Contract validator: `submission/evidence/validate-dashboard.txt` - 6/6 panel.
- Dashboard: `submission/evidence/dashboard.html`.
- Screenshot: `submission/evidence/dashboard.png`.
- Snapshot: `submission/evidence/dashboard-metrics.json`.

## Giải thích kỹ thuật

**Vì sao average latency có thể bỏ sót sự cố?** Average làm loãng tail latency. Một nhóm nhỏ request rất chậm có thể gây timeout nhưng mean vẫn đẹp; P95/P99 cho thấy trải nghiệm ở đuôi phân phối.

**Cost tăng khi traffic không tăng thì kiểm tra gì?** Kiểm tra `tokens_in`, `tokens_out`, model, prompt version, retrieval context length và retry/tool loop. Cost/request tăng thường đến từ token hoặc model mix chứ không phải request count.

**Validator 6/6 có đủ chứng minh dashboard đúng không?** Không. Validator chỉ kiểm tra contract YAML. Phải có runtime screenshot và snapshot từ log thật để chứng minh query/aggregation hiển thị đúng.

## Kết quả và việc còn lại

Dashboard local đã dựng và kiểm tra trực quan; P95 hiện là 2.654 ms, error 0%, cost 0,0440 USD, 3.512 token và quality 0,857 trên cửa sổ evidence. Commit/PR cá nhân chưa được tạo và cần cập nhật trước khi nộp.
