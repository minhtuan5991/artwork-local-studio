# Áp dụng 4 file POD Design Studio cho Qwen local

Đã đọc đủ 4 tài liệu POD do người dùng cung cấp ngày 30/09/2026. Nội dung là tài liệu tham khảo do người dùng cung cấp, không phải yêu cầu tự chạy giao thức automation.

## Mức phù hợp

| Tài liệu | Áp dụng cho app |
|---|---|
| KNOWLEDGE_01_WORKFLOW.md | Cơ sở chính của prompt CLONE: chấp nhận ảnh flat, garment/product mockup, screenshot; giữ design DNA, chữ, bố cục, màu, texture có chủ ý; sửa méo và mất nét thận trọng. |
| KNOWLEDGE_02_REDESIGN_STYLES.md | Không đưa style preset hay yêu cầu đổi pose/bố cục vào CLONE. Chỉ dùng nếu bổ sung REDESIGN riêng sau này. |
| KNOWLEDGE_03_QC_PRINT.md | Kiểm tra đầu ra: chữ đúng, đủ bố cục, không còn áo/sản phẩm, không halo, giữ distress; không tự tuyên bố 300 DPI/print-ready. |
| KNOWLEDGE_04_AUTOMATION_PROTOCOL.md | Ánh xạ MODE/INPUT_TYPE/BACKGROUND/PRESERVE/CHANGE_OR_EXTRA vào thiết lập và prompt. JOB_ID, OUTPUT: IMAGE_ONLY, điều khiển GPT, upload/capture trong conversation thuộc tầng automation; không phải prompt suy luận Qwen. |

## Những điều chỉnh cần thiết

- Đây là hướng dẫn cho GPT có thể phân tích, điều phối và kiểm tra. Qwen-Image-2.1 là model tạo/chỉnh ảnh: một prompt không tạo ra quy trình phân tích Design DNA hay QC đáng tin cậy một cách tự động.
- App chỉ dùng model Qwen-Image-2.1 cùng encoder/VAE của pipeline; không thêm model OCR, vision QC hoặc tách nền khác.
- Dùng câu lệnh trực tiếp và ràng buộc CLONE, bọc bằng mẫu RGBA chính thức của Qwen.
- Đưa chữ đã xác nhận vào prompt dưới dạng dữ liệu literal. Không tự điền chữ khó đọc.
- Chấp nhận flat artwork và sản phẩm khác áo; prompt có điều kiện theo ảnh, chưa có classifier độc lập.
- Chroma/trắng được composite bằng code từ RGBA để màu nền đúng và tránh thêm lượt AI.
- BACKGROUND: PRESERVE chưa thuộc phạm vi hiện tại. Không tự thêm REDESIGN/4 variants/UPSCALE độc lập.
- Chỉ kiểm tra tự động PNG, kích thước, alpha và nguy cơ chạm mép. Nội dung, chữ, halo và độ giống phải xem ảnh trên nền sáng/tối.

## Prompt adapter đang dùng

Prompt revision 4 nằm trong artwork_local/engine.py: make_prompt(). Bản 0.2.0 thêm yêu cầu dựng artwork thẳng theo nguồn đã được người dùng xoay; phép đo AI trong VALIDATION-VI.md vẫn là revision 3.

Nội dung cốt lõi:

    This is an RGBA image with transparency.
    CLONE the reference artwork as a complete standalone flat print graphic on a transparent canvas.
    If the reference is already flat artwork, preserve and clean it directly.
    For a mockup, recover only the underlying printed design and remove the garment or product and photographic effects.
    Keep the complete design and all lettering inside the canvas with clear margins.
    Lock composition, subject identity, pose, typography appearance, ink palette and intentional distress.
    Preserve all readable text exactly. Do not translate or correct spelling.
    Reconstruct unclear details conservatively without new unrelated elements.
    The image has alpha channel and the background is transparent.

Đây là adapter theo tài liệu, không phải toàn bộ tài liệu được ghép vào prompt. Prompt đầy đủ gồm các ràng buộc nền/chi tiết và chữ người dùng xác nhận.

## Giới hạn thực nghiệm

Lượt đầu xuất alpha thật nhưng còn viền áo; lượt crop/CFG1 nhanh hơn nhưng bị cắt chữ. Hai ví dụ này xác nhận file QC_PRINT có ích: đạt định dạng PNG/alpha chưa đủ để kết luận đạt CLONE. Chưa có benchmark 20 ảnh thực tế hoặc chứng minh độ chính xác clone ≥90%.

Sau khi áp dụng adapter CLONE revision 3, crop đủ thiết kế và nhập chữ xác nhận, lượt thử tiếp theo mất 212.3 giây ở 1K/20 bước/budget 4.5 GiB. PNG có alpha thật, không chạm mép, đủ chữ và viền cream, không còn thân áo trong quan sát trên checker. Đây là một fixture đơn giản; chưa thể suy rộng thành bảo đảm chất lượng cho mọi ảnh.

