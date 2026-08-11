# Báo cáo cá nhân - Nguyễn Bùi Anh Tuấn - MSSV 2A202601208

## Vai trò và mục tiêu

Vai trò chính: **Tracing & Prompt Version**. Mục tiêu là giải thích được thời gian của từng bước agent, biết request dùng prompt version/label nào và rollback mà không giả mạo trạng thái Langfuse.

## Phần việc thực hiện

- Tổ chức waterfall `agent_run` → `rag_retrieval` → `llm_generation` bằng Langfuse `observe`.
- Gắn trace metadata: user hash, session, feature/model tags, `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`.
- Gắn generation metadata: doc count, query preview đã redact, prompt identity, token usage, cost và managed prompt object khi lấy được từ Langfuse.
- Giữ local fallback rõ ràng: `local-v1` với source `local` hoặc `local-fallback`; lỗi fetch được ghi theo exception type, không giả thành managed version.
- Bảo đảm app không gọi prompt backend khi tracing tắt và vẫn chạy đầy đủ bằng fake LLM.
- Chuẩn hóa checklist tạo `day13-chat` v1/v2, labels `baseline`/`candidate`/`production`, đổi label và rollback.

## File và evidence

- File sở hữu: `app/agent.py`, `app/tracing.py`, `app/prompt_management.py`, `tests/test_agent_prompt_trace.py`, `tests/test_prompt_management.py`, `tests/test_tracing_adapter.py`.
- Test chứng minh metadata prompt được liên kết với trace/generation và fallback không bị báo sai.
- Checklist external evidence: `submission/evidence/langfuse-pending.md`.
- Môi trường hiện tại không có Langfuse key, nên chưa có trace ID/screenshot thật. Đây là hạn chế được khai báo, không được thay bằng ID giả.

## Giải thích kỹ thuật

**Khi metrics báo latency tăng, mở gì tiếp?** Dùng metrics xác định cửa sổ và tail percentile, mở trace chậm trong cửa sổ đó để tìm span chiếm thời gian, rồi dùng correlation ID mở log để xác nhận nguyên nhân cụ thể.

**Evidence nào đủ để kết luận một span là root cause?** Span phải tăng đồng thời với triệu chứng, chiếm phần lớn critical path, lặp lại ở nhiều trace bị ảnh hưởng và log/config cùng correlation ID phải xác nhận điều kiện gây chậm. Chỉ một trace chậm chưa đủ.

**Vì sao prompt label và version đều cần ghi?** Label biểu thị routing có thể thay đổi (`production`), còn version là artifact bất biến. Ghi cả hai mới tái tạo được request và chứng minh rollback.

## Kết quả và việc còn lại

Instrumentation, safe no-key fallback và unit test đã hoàn thành tại các commit `0e60fa9` và `601914e` bằng tài khoản `tunsbuiz26`. Nhóm vẫn cần key/project Langfuse thật để tạo tối thiểu 10 traces, hai prompt version, trace IDs và ảnh rollback trước khi nộp.
