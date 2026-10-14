# Bằng chứng ảnh 3D — MSSV 202602625

Bốn ảnh PNG gốc do người dùng cung cấp, được sao chép nguyên byte. Không cắt, chỉnh sửa hoặc dựng lại. `metadata.json` lưu SHA-256, kích thước, tên cảnh và thời gian.

Nạp `evidence/viewer-three-cases.json` trong chương 9 của `viewer/index.html` để phát lại đúng ba tình huống/bốn cấu hình đã chụp. File `evidence/viewer.json` vẫn là bản đầy đủ do runner xuất.

| Ảnh | Cảnh | Thời điểm sự kiện | Thời gian hiển thị trong ảnh | Câu báo cáo |
|---|---|---:|---:|---|
| bus_bypass-B-01.png | 1-BUS-baseline | 12,75 s | 12,8 s; thời gian làm tròn, có thông báo va chạm | 5 |
| fix-B-01.png | 1-BUS-fixed-ghost | baseline 12,75 s; bản sửa không va chạm | 12,8 s | 6 |
| crosswalk_block-C-01.png | 2-CROSSWALK-baseline | 21,10 s | 21,1 s | 5 |
| hazard-bike.png | 3-BICYCLE-fixed-ghost | 5,05 s | 5,1 s | 9 |

Ở cảnh baseline, xe chính được ghim vào policy gốc và bóng mờ dùng bản sửa; nhãn policy của bảng UI có thể gây nhầm. Ở cảnh fixed-ghost, xe chính dùng cutinLat=3 và bóng mờ dùng baseline. Chú thích trong REPORT.md dùng cấu hình thật của cảnh, không sửa nhãn UI vì viewer là mã được cung cấp.

Các ảnh chứng minh từng chuỗi sự kiện, không phải dữ liệu thực nghiệm để tính exposure. Exposure từ SinD được ghi riêng trong evidence/exposure.json và hazard.json.
