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

## 5. Train: raw vs clean (15 điểm riêng)

Đã hoàn thành huấn luyện trên Google Colab với GPU NVIDIA Tesla T4, mô hình YOLO26n (`yolo26n.pt`), 20 epoch, 2 seed (0 và 1), cùng tập validation 40 ảnh và tập test 100 ảnh. Hai biến thể sử dụng cùng cấu hình huấn luyện, chỉ khác dữ liệu train: Raw gồm 224 ảnh, Clean gồm 193 ảnh.

| Biến thể | Ảnh train | Seed | mAP50 (TB ± độ lệch) | mAP50-95 | Precision | Recall |
|---|---:|---:|---|---|---|---|
| Raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| Clean | 193 | 2 | 0.729 ± 0.002 | 0.500 ± 0.000 | 0.794 ± 0.028 | 0.619 ± 0.005 |

**Chênh lệch mAP50 (Clean − Raw): +0.004**, tương đương khoảng +0,4 điểm phần trăm. Mức cải thiện nhỏ và cần được xem xét cùng độ dao động giữa các seed. Precision tăng khoảng 0.030, nhưng Recall giảm 0.030 và mAP50-95 giảm 0.012.

**Phân tích theo lớp:** Trung bình hai seed, Clean tăng AP50 ở Car (khoảng +0.0155), Person (+0.0056), Bus (+0.0203), nhưng giảm ở Truck (khoảng −0.0270). Do đó, tác động của việc làm sạch không đồng đều giữa các lớp.

**Giả thuyết và cách kiểm chứng:**

1. Việc loại 31 ảnh và sửa nhãn có thể giảm nhiễu dữ liệu, giúp Precision tăng. Cần kiểm tra từng nhóm ảnh bị loại, đối chiếu lỗi nhãn trước/sau và chạy thêm seed để xác nhận.
2. Việc giảm số ảnh train từ 224 xuống 193 có thể làm mất một số ví dụ hữu ích, đặc biệt ở lớp Truck, khiến Recall hoặc AP50 giảm. Cần thống kê số đối tượng theo lớp trước/sau và đánh giá trên nhiều tập test.
3. Tập test chỉ gồm 100 ảnh nên kết quả có thể nhạy với mẫu dữ liệu. Cần đánh giá thêm trên tập test độc lập và tăng số seed.

**Kết luận:** Clean có mAP50 và Precision trung bình cao hơn Raw nhưng mAP50-95 và Recall thấp hơn. Với 2 seed, mức chênh lệch mAP50 nhỏ, chưa đủ bằng chứng khẳng định Clean cải thiện hiệu năng ổn định. Pipeline vẫn giữ quyết định HOLD do 34/193 ảnh còn cảnh báo (17,62%).

**Minh chứng:** `submission/results/raw_seed0.json`, `raw_seed1.json`, `clean_seed0.json`, `clean_seed1.json`, `comparison.json`, `comparison.md`, `comparison.png`.

## 6. Quyết định và ghi chú AI

**Quyết định cuối: HOLD.** Pipeline đã hết lỗi bắt buộc nhưng tỷ lệ ảnh cảnh báo 17,62% vẫn cao hơn ngưỡng 10%. Cần tiếp tục review, xử lý và kiểm tra lại cảnh báo, sau đó chạy lại pipeline và Gate. Với 193 ảnh, cần giảm số ảnh cảnh báo xuống dưới 10%, tức tối đa 19 ảnh nếu tổng ảnh không thay đổi.

**Ghi chú sử dụng AI:**

- **Prompt chính:** Hỗ trợ triển khai các module kiểm tra nhãn, second opinion, AutoFix, Gate và hướng dẫn chạy Calibration cho Day 09.
- **Cách kiểm code AI:** Chạy 79 bài kiểm thử bằng pytest, kiểm tra báo cáo CSV/JSON, chạy calibration sweep và kiểm chứng Gate bằng trường hợp không có review.
- **Một lần AI sai:** Hướng dẫn PowerShell ban đầu dùng cú pháp here-string không hợp lệ, gây lỗi thực thi; đã điều chỉnh cách viết lệnh và kiểm tra lại kết quả.

**Kết luận:** AutoQC giúp tự động hóa kiểm tra dữ liệu, phát hiện và sửa một phần lỗi, ưu tiên các ảnh cần con người xem xét. Kết quả HOLD phản ánh đúng tình trạng dataset chưa đủ điều kiện phát hành, thay vì cố tình hạ ngưỡng để đạt Release.