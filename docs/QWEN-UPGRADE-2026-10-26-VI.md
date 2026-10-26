# Kiểm tra nâng cấp mô hình — 26/10/2026

Kết luận: chưa có đường nâng cấp Qwen-Image-3.0 local được xác minh cho app này. Giữ Qwen-Image-2.1 hiện tại. Hướng thử tiếp theo hợp lý cho tốc độ là Qwen-Image-2.1-Turbo, nhưng chưa tích hợp hoặc benchmark trong bản 0.2.2.

## Phân biệt các tên mô hình

- **Qwen3 / Qwen3-VL** là họ mô hình ngôn ngữ/hiểu ảnh. App đã dùng **Qwen3-VL-8B** làm encoder và vision projector theo model-manifest.json. Thành phần này không thay thế mô hình sinh PNG RGBA.
- **Qwen-Image-3.0** là mô hình sinh/sửa ảnh đã được Qwen công bố. Tài liệu Alibaba hiện mô tả cách dùng qua dịch vụ/API; bản công bố không đủ để kết luận có thể tải trọng số chạy offline.
- **Qwen-Image-2.1-Turbo** có trọng số chính thức, cùng kiến trúc sinh ảnh 7B với 2.1 và lịch lấy mẫu 8 bước. Đây là ứng viên local có thể nghiên cứu nâng cấp, vẫn thuộc pipeline Qwen.

## Kiểm tra đã thực hiện

Đã đối chiếu blog Qwen-Image-3.0, tài liệu API Alibaba, danh mục mô hình tác giả Qwen trên Hugging Face, repo Qwen-Image-2.1, model card Turbo và tài liệu backend stable-diffusion.cpp.

Danh mục công khai của Qwen tìm thấy 2.1 và 2.1-Turbo; chưa tìm thấy bộ trọng số 3.0 công khai có thể xác minh. Địa chỉ repo GitHub QwenLM/Qwen-Image-3.0 trả 404; endpoint Hugging Face tương ứng trả 401, nên riêng mã HTTP đó không chứng minh mô hình không tồn tại. Tài liệu backend được kiểm tra liệt kê hỗ trợ Qwen Image 2.1 và Turbo, chưa xác nhận hỗ trợ 3.0.

Vì vậy, **chưa thể nâng app này lên Qwen-Image-3.0 mà vẫn bảo đảm yêu cầu không dùng API**. Đây là kết luận về khả năng tích hợp đã kiểm chứng tại thời điểm kiểm tra, không phải khẳng định sẽ không có trọng số trong tương lai.

## Đánh giá Turbo trên RTX 3050 Laptop 6 GB

Backend hiện tại của app được ghim ở bản build tháng 9. Tài liệu backend mới có lịch sigma dành riêng cho Turbo. Runtime đang có chỉ mô tả --sigmas dưới dạng danh sách số; chưa xác minh runtime này hiểu tên preset Turbo. Không chỉ giảm số bước của model cũ xuống 8 rồi gọi đó là Turbo.

Lộ trình thử: ghim/checksum checkpoint Turbo Q4 cùng runtime hỗ trợ, giữ bộ model/runtime cũ làm đối chứng; thêm profile Turbo với lịch sigma đúng; đo cùng bộ ảnh ở 1K; kiểm tra alpha thật, chữ, nét mảnh, biến dạng và thời gian/RAM/VRAM. Chỉ chuyển mặc định sau khi vượt kiểm tra chất lượng. 8 bước giảm công đoạn khử nhiễu nhưng không loại bỏ thời gian nạp model, mã hóa nguồn và giải mã VAE, nên chưa thể cam kết 1–2 phút/ảnh trên GPU 6 GB.

Bản 0.2.2 chỉ đổi quản lý ảnh trong Queue. Không tải trọng số mới, không đổi model/prompt/sampler và không chạy suy luận hay benchmark mới.

## Nguồn chính thức và mã nguồn backend

- [Blog Qwen-Image-3.0](https://qwen.ai/blog?id=qwen-image-3.0)
- [Tài liệu API Alibaba Qwen Image 3.0/2.1](https://help.aliyun.com/zh/model-studio/qwen-image-generation-and-editing-api-reference)
- [Danh mục model Qwen](https://huggingface.co/models?author=Qwen&sort=created)
- [Repo Qwen-Image-2.1](https://github.com/QwenLM/Qwen-Image-2.1)
- [Trọng số và model card 2.1-Turbo](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo)
- [Backend Qwen Image 2.1 / Turbo / alpha](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md)
