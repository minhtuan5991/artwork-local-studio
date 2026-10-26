<img src="assets/logo-128.png" width="64" alt="Artwork Local Studio logo">

# Artwork Local Studio

Ứng dụng Windows dùng **Qwen-Image-2.1 trên máy** để tách và tái tạo artwork, xuất PNG với alpha thật. Giao diện tiếng Việt, Queue bền vững và extension Chrome/Edge. Không gọi API AI.

**[Tải bộ cài Windows](https://github.com/minhtuan5991/artwork-local-studio/releases/latest)** · [Hướng dẫn tiếng Việt](README-VI.md) · [Kết quả kiểm chứng](docs/VALIDATION-VI.md)

## Phiên bản 0.2.3

- Phát hiện sớm cấu hình native 2K vượt khả năng GPU 6–8 GB; hướng dẫn chuyển 1K hoặc thử CPU, giữ nguyên kích thước job đã yêu cầu.
- Giới hạn ảnh tham chiếu lớn theo profile để giảm bộ nhớ, giữ tỷ lệ/alpha và giữ nguyên file gốc. File tham chiếu tạm được dọn sau xử lý.
- Hiển thị rõ lỗi thiếu bộ nhớ và cập nhật trạng thái preview khi job đổi trạng thái.
- Đã chạy lại một ảnh thực ở 1K/20 bước trên RTX 3050 Laptop 6 GB: khoảng 268,6 giây, PNG RGBA có alpha thật, không chạm mép. Native 2K trên máy 6 GB chưa khả thi với backend hiện tại.

## Queue từ 0.2.2

- Chọn một/nhiều ảnh trong Queue bằng Ctrl/Shift hoặc Chọn tất cả; có số lượng ảnh đã chọn.
- Xóa đã chọn, phím Delete và menu chuột phải; giữ ảnh đang xử lý, ảnh gốc và PNG đã lưu.
- Hoàn tác xóa bằng nút hoặc Ctrl+Z trong danh sách. Ảnh chờ được khôi phục ở trạng thái Đã hủy để tránh tự chạy AI.
- [Kiểm tra khả năng nâng cấp Qwen local ngày 26/10/2026](docs/QWEN-UPGRADE-2026-10-26-VI.md).

## Giao diện từ 0.2.1

- Forest green cho app, extension và logo.
- Các bảng cài đặt, menu và danh sách chọn dùng nền trắng sáng, chữ đậm, kể cả khi Windows đang bật giao diện tối.
- Bốn điểm neo ở góc ảnh: kéo để xoay quanh tâm; giữ Shift để xoay theo nấc 15°.

- Giao diện mới: Queue bên phải, thiết lập đầu ra bên dưới vùng ảnh.
- Logo thống nhất cho app, bộ cài và extension.
- Xoay ảnh nguồn ±90° hoặc nhập góc chính xác trước khi khoanh vùng.
- Extension: click đúp để tải ảnh, giữ đúng tỷ lệ, thanh công cụ cố định, tùy chọn ở góc trên phải.
- Bộ cài Windows theo tài khoản hiện tại; giữ Queue/model khi nâng cấp.
- Tự kiểm tra bản mới trên GitHub khi mở app; có nút kiểm tra thủ công.

## Cài đặt

Windows x64 10 phiên bản 1809 trở lên / Windows 11. Tải **ArtworkLocalStudio-Setup-0.2.3.exe** từ [GitHub Releases](https://github.com/minhtuan5991/artwork-local-studio/releases/tag/v0.2.3). ZIP Windows là bản portable; ZIP Extension dùng để tải riêng extension Chrome/Edge.

Với bản portable đã gom về một thư mục, chạy **ArtworkLocalStudio.exe** hoặc **StartApp.cmd**; data, models và runtime nằm cạnh EXE. Mã nguồn có công cụ sao chép/đối chiếu dữ liệu portable cũ trong tools/consolidate_data.py; công cụ không xóa thư mục nguồn và không tự di chuyển dữ liệu khi cài installer. Để extension tự mở EXE mới, mở Cài đặt → Ảnh website → Đăng ký kết nối trong app mới.

Bộ cài **không chứa trọng số model**. Bấm **Thiết lập Qwen** để tải khoảng 12 GB model/runtime có checksum, hoặc chọn bộ model và runtime đang có trong Cài đặt. Máy dùng GPU NVIDIA cần driver hỗ trợ CUDA 12. CPU được hỗ trợ nhưng chậm.

Mục tiêu 1–2 phút/1K chưa đạt trong phép đo hiện tại: RTX 3050 Laptop 6 GB đã xử lý fixture đơn giản khoảng **3 phút 32 giây** ở cấu hình được ghi trong tài liệu kiểm chứng. 2K và các máy khác chưa được benchmark. Cần duyệt chữ, chi tiết và độ giống bằng mắt.

Model theo **Qwen Research License**, giới hạn nghiên cứu/đánh giá phi thương mại. Xem [giấy phép model](licenses/QWEN-LICENSE.txt). Code và bộ cài không bao gồm trọng số; các thành phần phụ thuộc có giấy phép riêng trong [THIRD-PARTY.md](licenses/THIRD-PARTY.md).

## Phát triển và build

Python 3.12 x64, PowerShell:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe main.py
./tools/build.ps1 -Installer
```

Bản build nằm trong `release/<version>/`. Inno Setup và GitHub CLI phục vụ build được tải từ release chính thức với SHA-256 cố định vào `.tools/`.

Để kiểm tra extension bằng fixture local, cài Playwright cho Node và Microsoft Edge rồi chạy `node tools/qa_extension.cjs`. Đây là bridge giả lập để kiểm thử giao diện và pixel; không thay thế việc thử Native Messaging trong extension đã được cài.
