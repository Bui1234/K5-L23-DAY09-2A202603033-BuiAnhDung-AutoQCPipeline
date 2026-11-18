# Báo cáo Day 09 — Bùi Anh Dũng,

## 1. Kết luận trước

Pipeline AutoQC tiếp nhận **224 ảnh**, loại 31 ảnh ở bước Intake và giữ lại **193 ảnh (86,16%)** để xử lý. Sau 35 thay đổi AutoFix và 80 lượt review ảnh mô phỏng, QC v3 không còn lỗi bắt buộc (ERROR = 0). Tuy nhiên, vẫn có **34/193 ảnh cảnh báo (17,62%)**, vượt ngưỡng 10%, nên Gate quyết định **HOLD**. Dataset nháp được xuất tại `submission/export/clean_v1` nhưng chưa đủ điều kiện Release.

## 2. Lỗi và phân việc

Thống kê từ `02_error_list_v1.csv`; số liệu là số dòng phát hiện, một ảnh có thể xuất hiện nhiều lần.

| Mã lỗi | Số dòng | Ai xử lý | Lý do |
|---|---:|---|---|
| BAD_CLASS_ID | 6 | Máy | Kiểm tra ID lớp không hợp lệ |
| BAD_CLASS_NAME | 2 | Máy | Kiểm tra tên lớp |
| BAD_FORMAT | 3 | Máy | Phát hiện dòng nhãn sai định dạng |
| BAD_SIZE | 3 | Máy | Loại ảnh không đạt kích thước |
| BOX_OUT_OF_IMAGE | 8 | Máy | Điều chỉnh box vượt biên khi có thể |
| BOX_ZERO | 4 | Máy | Loại box có kích thước không hợp lệ |
| CORRUPT_IMAGE | 2 | Máy | Loại ảnh bị hỏng |
| DUP_BOX | 7 | Máy | Loại box trùng |
| DUP_IMAGE_EXACT | 8 | Máy | Lọc ảnh trùng chính xác |
| DUP_IMAGE_NEAR | 7 | Máy | Lọc ảnh gần trùng |
| LEAK_TEST | 11 | Máy | Loại dữ liệu trùng với tập tham chiếu |
| MISSING_LABEL_FILE | 6 | Người | Cần bổ sung nhãn |
| BOX_HUGE | 3 | Người | Kiểm tra box quá lớn |
| BOX_TINY | 6 | Người | Kiểm tra box nhỏ |
| CLASS_RARE | 4 | Người | Kiểm tra lớp hiếm |
| EMPTY_LABEL | 11 | Người | Xác nhận ảnh không có đối tượng |
| POSSIBLE_FALSE_POS | 24 | Người | Kiểm tra đối tượng gán thừa |
| POSSIBLE_LOOSE_BOX | 27 | Người | Kiểm tra box chưa khít |
| POSSIBLE_MISSING | 53 | Người | Kiểm tra đối tượng bị bỏ sót |
| POSSIBLE_WRONG_CLASS | 17 | Người | Kiểm tra nhầm lớp |

Các mã thuộc nhóm máy được phát hiện hoặc xử lý bằng kiểm tra quy tắc, Intake và AutoFix; không có nghĩa mọi dòng đều được AutoFix thành công.

Hàng đợi review ưu tiên ảnh có rủi ro cao. `img_0020` đứng đầu với priority 11.524 vì có nhiều mã cảnh báo; các ảnh thiếu nhãn như `img_0031` có priority 10.0.

Với ngân sách **80/121 ảnh (66,12%)**, review log ghi nhận 80 ảnh được thay bằng nhãn người. Trong số đó có **88 lượt cảnh báo ngữ nghĩa**: 51 `POSSIBLE_MISSING`, 17 `POSSIBLE_WRONG_CLASS`, 12 `POSSIBLE_FALSE_POS`, 8 `POSSIBLE_LOOSE_BOX`. Đây là số lượt mã cảnh báo, không phải 88 lỗi đã xác nhận.

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Đánh đổi |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | 2 | **16** | DUP_IMAGE_NEAR: 1.00/0.50 → 1.00/0.83 | F1 tăng 0.67 → 0.91 |
| `second_opinion.conf` | 0.25 | **0.60** | WRONG_CLASS: 0.56/0.83 → 0.62/0.83; MISSING: 0.50/1.00 → 0.57/1.00 | Cải thiện hai nhóm lỗi, nhưng giảm khả năng phát hiện box lỏng |

Ở confidence 0.60, F1 của `POSSIBLE_WRONG_CLASS` tăng từ 0.67 lên 0.71; `POSSIBLE_MISSING` tăng từ 0.67 lên 0.73. Ngược lại, F1 của `POSSIBLE_LOOSE_BOX` giảm từ 0.33 xuống 0.20.

**Rủi ro calibration:** Tăng pHash lên 20 khiến Recall của `DUP_IMAGE_EXACT` giảm từ 1.00 xuống 0.33 và F1 của `DUP_IMAGE_NEAR` giảm từ 0.91 xuống 0.67. Điều này chứng minh ngưỡng cao hơn không luôn tốt hơn. Ngoài ra, bộ calibration sử dụng lỗi cố ý nên kết quả chưa chắc đại diện cho dữ liệu thực tế.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

Đã kiểm chứng Gate bằng lệnh:

`python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`

Kết quả: **REWORK**, còn **6 lỗi bắt buộc**, exit code **20**, thư mục `work/exp_nb` không được tạo. Như vậy, Gate chặn việc xuất dataset khi lỗi bắt buộc chưa được xử lý.

Hai điểm mù có bằng chứng:

1. **Bounding box lỏng:** Calibration ở confidence 0.60 chỉ đạt Recall 0.20 cho `POSSIBLE_LOOSE_BOX`, tương đương phát hiện 1/5 trường hợp lỗi cố ý.
2. **Cảnh báo false positive:** `POSSIBLE_FALSE_POS` có TP = 5, FP = 9, Precision = 0.36. Nhiều cảnh báo không tương ứng với lỗi đã chèn, làm tăng khối lượng review.

Ngoài ra, pipeline vẫn còn 34/193 ảnh cảnh báo sau 80 lượt review, cho thấy AutoQC chưa thay thế hoàn toàn kiểm tra của con người.

## 5. Train: raw vs clean (tùy chọn)

**Chưa chạy.** Phần huấn luyện raw và clean trên Colab được chấm riêng; hiện chưa có kết quả mAP50, seed hoặc độ lệch chuẩn để so sánh. Vì vậy chưa thể kết luận dataset clean cải thiện hiệu năng mô hình.

## 6. Quyết định và ghi chú AI

**Quyết định cuối: HOLD.** Pipeline đã hết lỗi bắt buộc nhưng tỷ lệ ảnh cảnh báo 17,62% vẫn cao hơn ngưỡng 10%. Cần tiếp tục review, xử lý và kiểm tra lại cảnh báo, sau đó chạy lại pipeline và Gate. Với 193 ảnh, cần giảm số ảnh cảnh báo xuống dưới 10%, tức tối đa 19 ảnh nếu tổng ảnh không thay đổi.

**Ghi chú sử dụng AI:**

- **Prompt chính:** Hỗ trợ triển khai các module kiểm tra nhãn, second opinion, AutoFix, Gate và hướng dẫn chạy Calibration cho Day 09.
- **Cách kiểm code AI:** Chạy 79 bài kiểm thử bằng pytest, kiểm tra báo cáo CSV/JSON, chạy calibration sweep và kiểm chứng Gate bằng trường hợp không có review.
- **Một lần AI sai:** Hướng dẫn PowerShell ban đầu dùng cú pháp here-string không hợp lệ, gây lỗi thực thi; đã điều chỉnh cách viết lệnh và kiểm tra lại kết quả.

**Kết luận:** AutoQC giúp tự động hóa kiểm tra dữ liệu, phát hiện và sửa một phần lỗi, ưu tiên các ảnh cần con người xem xét. Kết quả HOLD phản ánh đúng tình trạng dataset chưa đủ điều kiện phát hành, thay vì cố tình hạ ngưỡng để đạt Release.