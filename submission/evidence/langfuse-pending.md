# Evidence Langfuse còn cần thu thập

Môi trường chạy hiện tại không có `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY`, vì vậy `tracing_enabled=false`. Không có trace ID hoặc ảnh prompt version nào được tạo giả.

Sau khi nhóm điền key thật vào `.env` (không commit), cần:

1. Tạo prompt `day13-chat` version 1 với labels `baseline`, `production`.
2. Tạo version 2 với label `candidate`.
3. Chạy cùng input với `baseline` và `candidate`; lưu hai trace ID có `prompt_name`, `prompt_label`, `prompt_version`.
4. Chuyển `production` sang version 2, chạy một request, rồi rollback về version 1.
5. Lưu ảnh danh sách 10+ traces, waterfall và trước/sau rollback vào thư mục này; cập nhật REPORT.md.
