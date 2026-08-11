# Báo cáo Day 13 Observability

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
| Nguyễn Việt Anh | 2A202601144 | Dashboard, SLO & Alert | Metrics, dashboard 6 panel, validator, runtime dashboard |
| Nguyễn Ngọc Chi | 2A202602024 | Incident, Report & Demo | SLO, alert rules, runbook, điều tra challenge và biện pháp phòng ngừa |
| Trần Thanh Bình | 2A202601174 | Incident, Report & Demo (đồng sở hữu) | QA, automation evidence, báo cáo, checklist demo và kiểm tra nộp bài |

Chi tiết phân công và tiêu chí hoàn thành nằm tại [`WORK_ASSIGNMENT.md`](WORK_ASSIGNMENT.md).

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
