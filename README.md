<img src="assets/logo-128.png" width="64" alt="Artwork Local Studio logo">

# Artwork Local Studio

Ứng dụng Windows dùng **Qwen-Image-2.1 trên máy** để tách và tái tạo artwork, xuất PNG với alpha thật. Giao diện tiếng Việt, Queue bền vững và extension Chrome/Edge. Không gọi API AI.

**[Tải bộ cài Windows](https://github.com/minhtuan5991/artwork-local-studio/releases/latest)** · [Hướng dẫn tiếng Việt](README-VI.md) · [Kết quả kiểm chứng](docs/VALIDATION-VI.md)

## Bản 0.2.0

- Giao diện mới: Queue bên phải, thiết lập đầu ra bên dưới vùng ảnh.
- Logo thống nhất cho app, bộ cài và extension.
- Xoay ảnh nguồn ±90° hoặc nhập góc chính xác trước khi khoanh vùng.
- Extension: click đúp để tải ảnh, giữ đúng tỷ lệ, thanh công cụ cố định, tùy chọn ở góc trên phải.
- Bộ cài Windows theo tài khoản hiện tại; giữ Queue/model khi nâng cấp.
- Tự kiểm tra bản mới trên GitHub khi mở app; có nút kiểm tra thủ công.

## Cài đặt

Windows x64 10 phiên bản 1809 trở lên / Windows 11. Tải `ArtworkLocalStudio-Setup-0.2.0.exe` từ Releases, chạy wizard, rồi mở app.

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
