Dưới đây là phần nội dung hoàn chỉnh và chuẩn mực cho file `README.md` để bạn đưa vào repository quản lý mã nguồn cho môn Đồ án Chuyên ngành:

---

# 📦 ALNS-DPDP: Dynamic Pickup and Delivery Problem (DPDP) Benchmark & Validation

## 📌 1. Mô tả dự án (Project Overview)

Repository này chứa toàn bộ mã nguồn mô phỏng, thuật toán và kịch bản thực nghiệm cho đề tài Đồ án Chuyên ngành:

> *"Nghiên cứu thuật toán Adaptive Large Neighborhood Search (ALNS) trong giao vận đô thị – Ứng dụng ALNS cho bài toán giao nhận hàng động (DPDP)"*
> 
> 

Dự án xây dựng hệ thống **Mô phỏng sự kiện rời rạc (Discrete Event Simulation - DES)** kết hợp bộ giải **ALNS-D** (tích hợp các cơ chế cải tiến: *đóng băng lộ trình cam kết*, *bộ lọc ứng viên theo độ lệch tuyến và hướng*, và *cắt ngắn vòng lặp theo ngân sách thời gian thực*). Mục tiêu cốt lõi là tự động hóa pipeline thực nghiệm, thu thập các chỉ số đánh giá đa tiêu chí và xử lý thống kê bằng kiểm định **Wilcoxon signed-rank test** nhằm kiểm chứng **4 giả thuyết khoa học (H1–H4)** so với các phương pháp đối chứng (Greedy Insertion, Regret-2, ALNS Full) trên bộ dữ liệu chuẩn Li & Lim động hóa và mạng lưới đường bộ thực tế khu vực TP.HCM.

---

## 🎯 2. Mục tiêu nghiên cứu (Research Objectives)

* **Tầng 1 (Mục tiêu chính):** Đánh giá hiệu quả của thuật toán ALNS so với chiến lược chèn tham lam truyền thống (`Greedy Insertion`) trong bài toán DPDP.


* **Tầng 2 (Mục tiêu mở rộng):** Đánh giá định lượng tác động của các cơ chế cải tiến thông qua 4 giả thuyết khoa học:


* **H1:** Cơ chế đóng băng lộ trình đã cam kết giúp giảm tổng quãng đường di chuyển có ý nghĩa thống kê so với chèn tham lam.


* **H2:** Bộ lọc ứng viên giúp giảm thời gian tính toán trung bình cho mỗi quyết định ($\bar{t}_{\text{dec}}$) mà không làm suy giảm đáng kể chất lượng lời giải.


* **H3:** Đánh giá vai trò và sự suy giảm đóng góp của cơ chế trọng số thích nghi khi ngân sách thời gian mỗi chu kỳ bị siết ngắn.


* **H4:** Hiệu quả tương đối ($\text{Gap \%}$) của ALNS-D tăng rõ rệt theo mức độ động ($\rho$) của bài toán.





---

## ⚙️ 3. Ma trận Thuật toán & Phương pháp Đối chứng

Hệ thống triển khai 4 nhóm thuật toán để so sánh chéo:

1. **Greedy Insertion:** Đối chứng chính (Baseline tốc độ, góc nhìn thiển cận).


2. **Regret-2 Insertion:** Đối chứng bổ sung thông minh hơn, đồng thời dùng làm thủ tục sinh lời giải khởi tạo ($s_0$) cho ALNS.


3. **ALNS Full:** ALNS cơ sở tái tối ưu toàn phần không đóng băng (môi trường lý tưởng tĩnh).


4. **ALNS-D (Đề xuất):** Phiên bản cải tiến thực tế tích hợp ràng buộc cam kết, lọc ứng viên và giới hạn thời gian $B$.



---

## 📂 4. Cấu trúc Thư mục (Repository Layout)

```text
dpdp_project/
├── configs/              # Cấu hình tham số chuẩn và các kịch bản H1-H4
│   ├── base.yaml         # Siêu tham số ALNS-D (Bảng 2.4)
│   ├── exp_h1.yaml       # Cấu hình kiểm chứng H1
│   ├── exp_h2.yaml       # Cấu hình Ablation Study H2
│   ├── exp_h3.yaml       # Cấu hình quét ngân sách B cho H3
│   └── exp_h4.yaml       # Cấu hình quét mức độ động rho cho H4
├── data/                 # Dữ liệu tĩnh Li & Lim và mạng đường HCM (.graphml)
├── src/                  # Mã nguồn lõi hệ thống
│   ├── simulation/       # Khung mô phỏng sự kiện rời rạc (DES - Thuật toán 2.2)
│   ├── algorithms/       # Các solver: Greedy, Regret-2, ALNS-operators, ALNS-D
│   ├── metrics/          # Bộ tính toán chỉ tiêu (validator.py, evaluator.py)
│   └── analysis/         # Kiểm định thống kê Wilcoxon signed-rank test & Plotting
├── experiments/          # Các kịch bản chạy thực nghiệm độc lập (run_h1.py -> run_h4.py)
├── results/              # Lưu log raw CSV, bảng tổng hợp LaTeX và biểu đồ
├── requirements.txt      # Danh sách thư viện Python (numpy, scipy, alns, osmnx,...)
└── README.md

```

---

## 📊 5. Nguyên tắc Xử lý Kết quả & Đạo đức Nghiên cứu

* **Liêm chính Dữ liệu:** Phân tích trên toàn bộ tập dữ liệu, tuyệt đối không chọn lọc (cherry-pick) seed hay instance.


* **Kiểm định Thống kê:** Sử dụng kiểm định phi tham số *Wilcoxon signed-rank test* ($\alpha = 0.05$) trên các cặp mẫu chạy cùng hạt giống ngẫu nhiên. Nếu $p > 0.05$, chỉ kết luận là *"chưa đủ bằng chứng để bác bỏ giả thuyết"*.


* **Phân tích Đánh đổi (Trade-off):** Làm rõ sự đánh đổi giữa chất lượng quãng đường và tốc độ phản hồi tính bằng giây nhằm đảm bảo tính khả thi trong thực tế vận hành đô thị.