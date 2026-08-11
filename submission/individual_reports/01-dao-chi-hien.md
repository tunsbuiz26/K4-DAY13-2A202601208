# Báo cáo cá nhân - Đào Chí Hiển - MSSV 2A202601066

## Vai trò và mục tiêu

Vai trò chính: **Logging & PII**. Mục tiêu là để mọi request `/chat` có thể truy vết bằng correlation ID, log JSON có đủ metadata phục vụ dashboard/điều tra và dữ liệu nhạy cảm bị loại bỏ trước khi đến bất kỳ sink nào.

## Phần việc thực hiện

- Hoàn thiện `CorrelationIdMiddleware`: xóa contextvars để tránh rò ngữ cảnh giữa request, nhận ID hợp lệ từ `x-request-id` hoặc sinh `req-<8 hex>`, bind vào structlog và trả `x-request-id`/`x-response-time-ms`.
- Bind `user_id_hash`, `session_id`, `feature`, `model`, `env` tại đầu `/chat` để `request_received`, agent events và `response_sent` dùng chung context.
- Chuyển user ID thành SHA-256 rút gọn thay vì ghi định danh thô.
- Viết processor redaction đệ quy cho string trong dict/list/tuple; đặt processor sau exception formatter nhưng trước file/JSON renderer.
- Mở rộng PII patterns cho email, điện thoại Việt Nam, CCCD, thẻ thanh toán, hộ chiếu và địa chỉ có nhãn.
- Bổ sung test cho propagation header, format ID, nested payload, exception text, passport và address.

## File và evidence

- File sở hữu: `app/middleware.py`, `app/logging_config.py`, `app/main.py`, `app/pii.py`, `tests/test_observability_hardening.py`.
- Validator: `submission/evidence/validate-logs.txt` - 100/100, 0 thiếu enrichment, 0 PII leak.
- Correlation chain: `submission/evidence/correlation-chain.json`.
- Redaction record: `submission/evidence/pii-redaction.json`.

## Giải thích kỹ thuật

**Correlation ID khác trace ID như thế nào?** Correlation ID là khóa ứng dụng truyền qua header/log để nối các event của một request. Trace ID do tracing backend quản lý và liên kết nhiều span; một trace có thể mang correlation ID làm metadata để chuyển từ trace sang log.

**PII scrub trước hay sau JSON render?** Phải scrub trước renderer và trước file sink. Nếu render trước rồi mới scrub một nhánh payload, exception hoặc field top-level vẫn có thể ghi dữ liệu thô xuống log.

**Vì sao clear contextvars?** Worker có thể tái sử dụng execution context. Không clear ở biên request có thể gán nhầm user/session/correlation ID cũ cho request mới.

## Kết quả và việc còn lại

Phần local đạt gate logging/PII. Commit/PR cá nhân chưa được tạo trong working tree hiện tại; cần commit đúng tài khoản Đào Chí Hiển và cập nhật link vào báo cáo nhóm trước khi nộp.
