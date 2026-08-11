# Báo cáo cá nhân - Trần Thanh Bình - MSSV 2A202601174

## Vai trò và mục tiêu

Vai trò: **Incident, Report & Demo - đồng sở hữu**, tập trung QA, automation evidence và tính trung thực của bài nộp. Mục tiêu là mọi kết luận trong báo cáo đều trỏ tới output có thể tái tạo, không lộ secret/PII và không khai báo trace/commit chưa tồn tại.

## Phần việc thực hiện

- Thiết kế gate cuối gồm pytest, log validator, dashboard validator, evidence collector, Git diff/status và secret/PII scan.
- Xây `scripts/collect_evidence.py` tự xác định cửa sổ incident, loại cửa sổ incident khỏi baseline, tính P95 và trích correlation chain/PII record.
- Tự động lưu `validate-logs.txt`, `validate-dashboard.txt`, `pytest.txt`, `challenge-investigation.md` và checklist Langfuse còn thiếu.
- Đối chiếu report với repository URL, base SHA, file thay đổi và trạng thái working tree.
- Tổng hợp báo cáo nhóm, năm báo cáo cá nhân và checklist demo.
- Ghi rõ browser tích hợp không khả dụng; dùng PNG tạo từ cùng snapshot dữ liệu thay vì tuyên bố có screenshot browser.

## File và evidence

- File sở hữu: `scripts/collect_evidence.py`, `submission/REPORT.md`, `submission/WORK_ASSIGNMENT.md`, `submission/individual_reports/`, `submission/evidence/`.
- Test: `submission/evidence/pytest.txt` - 29 passed.
- Log validator: `submission/evidence/validate-logs.txt` - 100/100.
- Dashboard validator: `submission/evidence/validate-dashboard.txt` - 6/6.
- Pending external evidence: `submission/evidence/langfuse-pending.md`.

## Giải thích kỹ thuật

**Vì sao validate_logs đạt 100 chưa đồng nghĩa bài đạt 100?** Script chỉ chấm nhanh schema/correlation/enrichment/PII. Rubric còn trace/prompt version, runtime dashboard, incident reasoning, demo, report và commit/PR cá nhân.

**Evidence tốt có đặc điểm gì?** Có timestamp/cửa sổ đo, ID liên kết, lệnh tái tạo, nguồn dữ liệu rõ và không mâu thuẫn với Git. Screenshot đơn lẻ không đủ nếu không biết nó đến từ query/log nào.

**Kiểm tra secret/PII trước nộp ra sao?** Xác nhận `.env` bị ignore, quét tracked files cho pattern key/email/phone/card, kiểm tra evidence chỉ chứa dữ liệu đã redact và xem `git diff --check`/`git status`.

## Kết quả và việc còn lại

Gate local đã qua 29 test và hai validator. Cần từng thành viên tạo commit/PR bằng tài khoản thật, thu Langfuse evidence và chạy lại collector ngay trước final commit. Commit/PR cá nhân hiện chưa có nên báo cáo không gán tác giả giả.
