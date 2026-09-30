# Kiểm chứng bản 0.1.0 — 30/09/2026

## Phạm vi đã triển khai

Desktop Windows x64 PySide6, nhập ảnh máy/clipboard/kéo thả, rectangle/lasso/zoom/pan, Queue SQLite lưu qua lần mở app, trùng pixel và cảnh báo pHash, worker một ảnh mỗi lần, hủy/dừng sau ảnh, retry, PNG alpha thật, composite trắng/chroma, lưu không ghi đè, giữ master khi lỗi lưu, Native Messaging host và extension Chrome/Edge.

Chỉ có Qwen-Image-2.1 là model tạo/tái tạo/tách artwork. Qwen3-VL encoder và VAE là thành phần của pipeline Qwen. Không có API suy luận, model OCR, rembg, segmentation hoặc model sửa ảnh khác.

Prompt CLONE revision 3 đã áp dụng nội dung phù hợp từ 4 file KNOWLEDGE của người dùng. Có checklist duyệt QC nội dung, tách khỏi kiểm tra PNG/alpha.

## Kiểm thử phần mềm

25 kiểm thử unittest đã qua: Queue persistent/selected order/recover, source retention khi hủy, chống trùng sau đổi metadata và ẩn/restart, gần giống cảnh báo, đổi seed, tái sử dụng master cho đổi nền, save failure retry không chạy AI thêm, không ghi đè, receipt checksum, bác RGB/alpha toàn đục/khác kích thước/chạm mép, options, Unicode command arguments, Native Messaging framing/origin/ảnh hỏng/payload fields, crop/lasso ở pixel gốc, filter/selection và Qt screenshot.

Fixture AI tổng hợp chỉ dùng trong test_core.py để kiểm tra phần mềm. Các phép đo bên dưới gọi sd-cli và trọng số Qwen thật.

Bản EXE được kiểm tra mở giao diện bằng Qt offscreen và truyền ảnh qua native host đã đóng gói. Test intake không chạy AI. Chưa kiểm thử end-to-end extension trên một website Etsy/Chrome/Edge đang đăng nhập; cần load unpacked và cấp quyền tên miền trong trình duyệt của người dùng.

## Suy luận AI thật trên máy hiện tại

NVIDIA RTX 3050 Laptop 6 GB VRAM, RAM 11.7 GiB. Runtime CUDA12 stable-diffusion.cpp master-929-3f8527a. Denoiser Q4_K_M, encoder Q4_K_M, vision projector F16, VAE BF16. Tất cả file model/runtime tải theo revision cố định và xác minh SHA-256.

| Lượt | Cấu hình và kết quả |
|---|---|
| Ban đầu, CFG6, diffusion-only FA | OOM trong text/image encoder; không có PNG. |
| Giảm budget, tắt prefix cache, diffusion-only FA | Vẫn OOM encoder; giảm budget riêng không giải quyết được. |
| FA toàn bộ + mmap + Q8 prefix, CFG6, budget 3.5 GiB, 20 bước, mockup nguyên áo | 570.1 giây; PNG RGBA 1024² có alpha thật nhưng còn viền áo/translucent residue. QC nội dung không đạt. |
| Crop sát, CFG1, budget 4.5 GiB, 20 bước, prompt revision 2 | 209.7 giây; alpha thật và loại áo tốt hơn, nhưng chữ chạm/cắt mép. QC nội dung không đạt; nguyên nhân gồm vùng crop nguồn quá sát. |
| Crop chứa đủ thiết kế, CFG1, budget 4.5 GiB, 20 bước, chữ xác nhận ARTWORK 42, prompt POD CLONE revision 3 | 212.3 giây; RGBA 1024², alpha min 0/max 255, 826704 pixel alpha <16, 215417 pixel alpha >127, không foreground chạm mép. Quan sát trên checker thấy chữ đầy đủ, viền cream quanh biểu tượng, không còn thân áo. |

Các lượt sử dụng fixture đơn giản tự tạo gồm biểu tượng sao và chữ trên áo, seed 42. Đổi nhiều yếu tố giữa các lượt để khắc phục lỗi; không phải A/B đo riêng từng tham số. Lượt cuối chưa chứng minh chất lượng tương đương trên mockup phức tạp hoặc chữ dài.

PNG, preview checker, metadata và log chi tiết nằm trong test-output/benchmark-pod-clone. Preview checker dùng composite xác định bằng code để nhìn alpha; PNG gốc vẫn là RGBA từ Qwen.

## Kết luận thực tế

- Có thể chạy pipeline Qwen local và xuất alpha thật trên máy này khi có Flash Attention toàn bộ, mmap/offload và budget phù hợp.
- Lượt cuối khoảng 3 phút 32 giây/1K ở budget 4.5 GiB. Chưa đạt mục tiêu 1–2 phút. Default app dùng budget 3.5 GiB thận trọng hơn và có thể chậm hơn số đo này.
- CLI tạo context mới mỗi job. Chưa có context thường trú xuyên Queue, nên vẫn có thời gian nạp/mã hóa mỗi ảnh.
- 2K có nút chọn và engine xuất native size; chưa benchmark AI 2K trên 6 GB VRAM. Khả năng lỗi/chậm cao hơn.
- Chưa đo median/P95 trên 20 ảnh thực, chưa chạy 10 ảnh AI liên tiếp, chưa đo peak RAM/VRAM bằng sampler liên tục. Giá trị memory đã quan sát trong một thời điểm không được gọi là peak.
- Chưa chứng minh mục tiêu chất lượng ≥90%. Duyệt QC nội dung bằng mắt vẫn cần thiết.
- Máy yếu hơn có lựa chọn CPU/memory controls; chưa benchmark CPU. Không bảo đảm thời gian trên máy khác.

Đây là bản ứng dụng local có thể sử dụng để thử nghiệm, chưa phải chứng nhận tự động artwork print-ready hay clone chính xác tuyệt đối.

## Nguồn kỹ thuật

- Qwen và mẫu prompt RGBA: https://github.com/QwenLM/Qwen-Image-2.1
- Backend và weight components: https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md
- Performance/memory management: https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/performance.md
- Native Messaging: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging

## Cập nhật 0.2.0 — giao diện, xoay nguồn, installer và GitHub

31 unittest đã qua, gồm kiểm thử cũ cùng chiều xoay, alpha ở góc mở rộng, kích thước Pillow, vùng chọn sau xoay đưa vào source của Queue, data directory của bản cài, phân tích phiên bản và lỗi mạng khi kiểm tra cập nhật.

Qt offscreen đã kiểm tra bố cục ở 1280×800 và 1920×1080; các điều khiển đầu ra đủ chiều cao và không chồng vùng preview. Logo SVG được xuất PNG đa kích thước và ICO cho app/installer.

Edge headless với fixture tự tạo và Chrome bridge giả lập đã xác nhận: click đúp tải ảnh, URL trang không hiển thị, toolbar không dịch khi cuộn thư viện, canvas backing theo devicePixelRatio, giữ tỷ lệ, và Native Messaging payload chứa PNG đã xoay đúng chiều với pixel đúng vị trí. Không có lỗi JavaScript. Đây là kiểm thử giao diện/transport giả lập; quyền domain và extension/native kết nối trên website thật vẫn cần kiểm tra khi người dùng cài extension.

Bản EXE 0.2.0 đã mở giao diện, bác origin không được phép và đưa ảnh qua native host đã đóng gói vào Queue mà không chạy AI.

Bộ cài Inno Setup đã được thử cài im lặng vào thư mục test riêng, mở app đã cài và gỡ cài đặt. Queue/model thử nghiệm còn nguyên sau khi gỡ; registry Native Messaging hiện có không đổi trong bài test. Bài test bỏ qua đăng ký host/shortcut bằng TESTMODE; kết nối được hỗ trợ bằng task trong installer và nút Đăng ký kết nối của app.

Prompt revision 4 thêm yêu cầu đầu ra thẳng theo ảnh đã xoay. Không chạy benchmark Qwen mới trong đợt cập nhật này; các con số tốc độ/chất lượng AI phía trên thuộc revision 3. Xoay/crop xác định và các thay đổi giao diện không chứng minh chất lượng clone mới.

Cập nhật phiên bản dùng public GitHub Releases từ minhtuan5991/artwork-local-studio, chạy nền mỗi lần mở app. App không tự cài và không gửi ảnh qua mạng để kiểm tra bản mới.
