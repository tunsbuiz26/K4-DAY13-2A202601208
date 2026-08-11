# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `ai_api_tail_latency_slo_breach`
- Severity: High.
- SLI/SLO liên quan: Latency P95 <= 3.000 ms trong cửa sổ SLO 28 ngày.
- Điều kiện và thời gian duy trì: P95 > 3.000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: Câu trả lời chậm, timeout phía client và giảm khả năng hoàn thành tác vụ.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận time range, lưu P50/P95/P99 và traffic cùng thời điểm.
  2. Mở trace chậm, so sánh thời gian span retrieval và generation.
  3. Tìm log bằng correlation ID của trace để xác nhận incident, lỗi tool hoặc thay đổi token.
- Mitigation tạm thời: Tắt incident/feature gây chậm, giảm concurrency hoặc chuyển sang đường fallback; theo dõi P95 ít nhất 10 phút sau khôi phục.
- Owner: `oncall-observability`.

## Alert 2

- Tên: `ai_api_error_rate_slo_breach`
- Severity: Critical.
- SLI/SLO liên quan: Error rate <= 2% trong cửa sổ SLO 28 ngày.
- Điều kiện và thời gian duy trì: Error rate > 2% liên tục 5 phút và có ít nhất 10 request để tránh nhiễu mẫu nhỏ.
- Ảnh hưởng tới người dùng: Request `/chat` thất bại hoặc trả HTTP 5xx.
- Ba bước kiểm tra đầu tiên:
  1. Xem breakdown theo `error_type`, feature và model.
  2. Mở một trace lỗi đại diện để tìm span đầu tiên chuyển trạng thái lỗi.
  3. Dùng correlation ID tìm `request_failed`, đối chiếu `error_type` và payload đã redact.
- Mitigation tạm thời: Vô hiệu hóa tool/incident lỗi, dùng fallback an toàn và rollback thay đổi gần nhất nếu bằng chứng khớp.
- Owner: `oncall-api`.

## Alert 3

- Tên: `ai_api_quality_degradation`
- Severity: Medium.
- SLI/SLO liên quan: Quality proxy trung bình >= 0,75.
- Điều kiện và thời gian duy trì: Trung bình < 0,75 liên tục 15 phút và có ít nhất 10 request.
- Ảnh hưởng tới người dùng: Câu trả lời thiếu ngữ cảnh, quá ngắn hoặc không bám câu hỏi dù API vẫn thành công.
- Ba bước kiểm tra đầu tiên:
  1. Phân đoạn quality theo feature, model, prompt label và prompt version.
  2. So sánh trace trước/sau lần đổi prompt label; kiểm tra retrieval có tài liệu hay không.
  3. Dùng correlation ID xem `response_sent.quality_score`, token và preview đã redact.
- Mitigation tạm thời: Rollback label `production` về prompt baseline đã biết ổn định và xác nhận chất lượng trên cùng bộ input.
- Owner: `oncall-ai-quality`.

## Quy tắc đóng sự cố

Chỉ đóng alert khi chỉ số đã trở lại ngưỡng ít nhất hai chu kỳ đánh giá, đã lưu metric/trace/log làm evidence và đã ghi owner cho preventive action. Không đưa secret, prompt chứa PII hoặc dữ liệu người dùng nguyên văn vào ticket.
