# Artwork Local Studio 0.2.0

App Windows tiếng Việt dùng Qwen-Image-2.1 local để tách và tái tạo artwork. Không dùng API AI.

## Cài đặt trên Windows

1. Tải **ArtworkLocalStudio-Setup-0.2.0.exe** từ [GitHub Releases](https://github.com/minhtuan5991/artwork-local-studio/releases/latest).
2. Chạy wizard. App cài cho tài khoản Windows hiện tại, không cần quyền quản trị. Có Start Menu, tùy chọn shortcut Desktop và kết nối Chrome/Edge.
3. Mở app → **Thiết lập Qwen** để tải model/runtime vào ổ đủ dung lượng. Tổng model khoảng 11,6 GB; cần thêm dung lượng cho runtime, cache và kết quả.
4. Nếu đã có model: **Cài đặt → Model & lưu ảnh**, chọn thư mục models và file runtime/sd-cli.exe đang có. Không cần tải lại.
5. Chọn thư mục lưu PNG trong bảng thiết lập đầu ra.

Windows x64 10 phiên bản 1809 trở lên hoặc Windows 11. NVIDIA cần driver hỗ trợ CUDA 12. Có chế độ CPU nhưng chậm; máy ít RAM/VRAM cần cấu hình phù hợp. Không bảo đảm tốc độ trên máy khác.

Bộ cài không kèm trọng số hoặc CUDA runtime. Model tải theo revision và SHA-256 cố định. Tải dở được giữ để tiếp tục.

## Tách và tái tạo artwork

1. **Chọn ảnh**, kéo thả PNG/JPEG/WebP hoặc Ctrl+V. Chọn nhiều file để thêm hàng loạt.
2. Với một ảnh, xoay ±90° hoặc nhập góc chính xác để dựng thẳng nguồn; sau đó chọn Rectangle/Lasso. Đổi góc xoay sẽ xóa vùng chọn cũ.
3. Thiết lập 1K/2K, trong suốt/trắng/chroma, giữ thiết kế/khôi phục chi tiết. Có ô nhập chữ xác nhận và yêu cầu sửa thêm.
4. **Thêm vào Queue → Chạy Queue**. Queue nằm bên phải; thiết lập nằm dưới vùng ảnh.
5. Chọn một ảnh trong Queue để xem nguồn/kết quả, trạng thái, thời gian và QC. Nút **Thao tác** chứa retry, chạy lại AI, xuất nền, đổi thứ tự và ẩn ảnh.

Ảnh đưa vào model là PNG đã xoay/crop thật. Prompt yêu cầu đầu ra artwork thẳng và không giữ phối cảnh sản phẩm; mức độ chính xác vẫn cần kiểm tra bằng mắt.

Mặc định: CFG 1, Euler, 20 bước, Q4, Flash Attention toàn bộ, mmap/offload, budget 3,5 GiB, Q8 cache và VAE tiling. GPU có đủ VRAM trống có thể tăng budget/chọn profile khác trong Cài đặt. Đã chạy fixture 1K với budget 4,5 GiB khoảng **212,3 giây** trên RTX 3050 Laptop 6 GB / RAM 11,7 GiB. Mục tiêu 1–2 phút chưa đạt; 2K và CPU chưa được benchmark.

Qwen3-VL encoder và VAE là các thành phần của pipeline Qwen. Không thêm OCR, rembg hoặc model tách nền khác.

## Extension Chrome / Edge

1. Nếu chưa chọn kết nối khi cài: **Cài đặt → Ảnh website → Đăng ký kết nối**.
2. Bấm **Mở thư mục extension**. Mở chrome://extensions hoặc edge://extensions → Developer mode → Load unpacked → chọn thư mục này.
3. Chuột phải ảnh trên website → Artwork Local Studio, hoặc bấm icon extension để lấy các ảnh trên trang.
4. **Click đúp thumbnail** để chọn và tải. Cho phép tên miền chứa ảnh khi trình duyệt hỏi.
5. Xoay nguồn cho thẳng → khoanh vùng → chọn tùy chọn ở góc trên phải → **Gửi vào Queue local**.

Toolbar cố định trong cửa sổ; chỉ thư viện thumbnail cuộn. Ảnh preview giữ đúng tỷ lệ. URL trang được giữ trong metadata nguồn, không hiển thị trên thư viện ảnh.

Native Messaging chỉ nhận extension ID **nimddfjhgiebfhfpgecahpgllikefljc**. App tự mở khi nhận ảnh; ảnh được xếp hàng, chưa tự chạy AI. Website dùng blob/chặn tải: Copy image rồi Ctrl+V trong app.

Khi cập nhật app, vào trang Extensions và bấm Reload. Nếu chuyển từ bản portable sang bản cài đặt, chọn lại thư mục extension trong nơi cài app.

## Lưu dữ liệu và nâng cấp

- Bản cài: Queue, cấu hình, cache, model và runtime mặc định trong **%LOCALAPPDATA%/ArtworkLocalStudio**. PNG mặc định trong Pictures/Artwork Local Studio hoặc thư mục bạn chọn.
- Bản portable: dữ liệu trong data bên cạnh EXE; model/runtime bên cạnh EXE hoặc đường dẫn được chọn.
- Nâng cấp bản cài giữ dữ liệu và model. Gỡ app giữ dữ liệu này; không tự xóa kết quả.
- Bản portable 0.1.0 vẫn giữ dữ liệu riêng. Khi chuyển sang installer lần đầu, chọn model/runtime cũ trong Cài đặt; Queue cũ không được tự di chuyển.
- App kiểm tra GitHub Releases khi mở bằng luồng nền. Offline không cản sử dụng app. Có thể tắt trong Cài đặt.
- Khi có bản mới, nút cập nhật hiển thị phiên bản. Mở trang tải, hoàn tất Queue/đóng app rồi chạy bộ cài mới. Không tự tải/cài âm thầm.
- Chỉ tải metadata phiên bản từ GitHub. Ảnh không được gửi tới GitHub hoặc dịch vụ AI.

## Queue, chống trùng và QC

Queue SQLite giữ qua lần mở app. Job đang chạy khi đóng bất thường chuyển Bị gián đoạn; retry chạy lại từ đầu. **Dừng sau ảnh này** hoàn tất ảnh hiện tại; **Hủy ảnh** dừng suy luận hiện tại.

Trùng pixel đã chuẩn hóa + cấu hình sẽ được bỏ qua. Ảnh gần giống có cảnh báo. Đổi seed/prompt tạo job khác. Ẩn khỏi Queue giữ ảnh và lịch sử trùng.

Bản RGBA gốc giữ trong data/results. Nếu không lưu được thư mục đích, chọn nơi khác → Thao tác → Thử lại / lưu tiếp → Chạy Queue; không cần sinh AI lại. Xuất trắng/chroma tái sử dụng RGBA cùng kích thước và composite bằng CPU.

PNG phải có alpha thật, đúng kích thước, không hoàn toàn đục/rỗng và không có foreground chạm mép đáng kể. File xuất không ghi đè file cũ, có JSON cấu hình/checksum.

Kiểm tra alpha không xác nhận chữ, độ giống, halo hoặc nội dung. **Duyệt QC** sau khi xem trên nền sáng/tối trước khi sử dụng kết quả.

## Giấy phép và kiểm chứng

Model theo **Qwen Research License** cho nghiên cứu/đánh giá phi thương mại; xem licenses/QWEN-LICENSE.txt. Mỗi thư viện giữ giấy phép riêng trong licenses/THIRD-PARTY.md.

Xem docs/VALIDATION-VI.md cho phạm vi kiểm thử và phép đo AI thật. Logo/app source/build script có tại [repository](https://github.com/minhtuan5991/artwork-local-studio).

## Phát triển

Python 3.12 x64, tạo .venv rồi cài requirements.txt. Chạy:

    .venv/Scripts/python.exe main.py
    .venv/Scripts/python.exe -m unittest discover -s tests -v
    node tests/extension_geometry.mjs
    powershell -File tools/build.ps1 -Installer

Bản build ở release/<version>/. Bộ cài Inno Setup và GitHub CLI tải từ release chính thức, kiểm SHA-256. Benchmark thật bằng tools/benchmark.py; fixture phần mềm không được dùng như đầu ra AI trong app.
