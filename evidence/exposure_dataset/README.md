# Nguồn exposure: SinD public sample records

Nguồn chính: https://github.com/SOTIF-AVLab/SinD
Commit cố định: 930e4dea78d924c6e9a58ff8e378331f93bba8ec.

Đã dùng đủ bốn mẫu công khai của Tianjin, Changchun, Chongqing và Xi'an. Các manifest ghi URL tải, kích thước và SHA-256. LICENSE và Format.md là tài liệu nguyên bản từ repo. Dữ liệu chỉ được dùng cho bài nghiên cứu phi thương mại này.

Tái lập từ thư mục gốc lab/bài nộp:

    python -m lab11.exposure_dataset --download

Lệnh tải CSV nếu thiếu và kiểm tra checksum; chỉ cần numpy và thư viện chuẩn Python, không GPU hay API key. Nếu CSV đã có, dùng python -m lab11.exposure_dataset để phân tích offline. Repo Git chỉ giữ manifest/tài liệu, metadata nhỏ và kết quả. Cache CSV quỹ đạo lớn đã chuyển ra ngoài repo; lệnh --download tải lại từ URL cố định và kiểm tra checksum trước khi phân tích.

Kết quả chính: 0/1938 lượt ô tô đủ điều kiện; dùng cận trên Wilson danh định 0.0019783282014351738 làm giả định bảo thủ, không coi đó là tần suất dương quan sát được. Đơn vị là lượt ô tô qua giao lộ, không phải chuyến đi dài hoàn chỉnh. Chuyển miền sang town A và phân phối hazard kỹ thuật chưa được hiệu chỉnh; ghi rõ hạn chế trong REPORT.md và hazard.json: why.
