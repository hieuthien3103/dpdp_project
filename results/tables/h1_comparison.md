# H1 comparison summary

Summary across all 30 paired seeds for each Li & Lim instance. `D` is the current prototype evaluator's distance computed from route-node coordinates; it is not yet a road-network travel distance.

| Instance | Paired seeds | Requests | Served (off/on) | Service rate (off/on) | D mean, freeze off | D mean, freeze on | Δ D (on − off) |
|---|---:|---:|---:|---:|---:|---:|---:|
| lc101 | 30 | 53 | 53 / 53 | 100% / 100% | 2295.28 | 1662.63 | -632.65 |
| lc201 | 30 | 51 | 45.27 / 45.27 | 88.76% / 88.76% | 2684.67 | 2013.59 | -671.07 |
| lr101 | 30 | 53 | 53 / 53 | 100% / 100% | 2273.57 | 2096.61 | -176.97 |
| lr201 | 30 | 51 | 51 / 51 | 100% / 100% | 2582.95 | 1921.36 | -661.59 |
| lrc101 | 30 | 53 | 53 / 53 | 100% / 100% | 2882.00 | 2670.77 | -211.23 |
| lrc201 | 30 | 51 | 51 / 51 | 100% / 100% | 3910.50 | 3088.42 | -822.08 |

## Statistical definition

For each paired instance-seed trial \(i\), define \(d_i = D_{\text{off},i} - D_{\text{on},i}\), where a positive value means the freeze-on run has a lower measured distance.

- \(H_0\): the distribution of paired differences is symmetric about zero.
- \(H_1\): the distribution of paired differences is shifted positively (\(D_{\text{on}} < D_{\text{off}}\)).
- Use a one-sided Wilcoxon signed-rank test with \(\alpha = 0.05\), pairing by the same instance and seed. The directional alternative should be specified before examining results.
- Report the paired rank-biserial correlation \(r_{rb}=(W^+ - W^-)/(W^+ + W^-)\). This is the appropriate rank-based effect size for paired observations. Cliff's delta is intended for independent samples and is not used here.

## Wilcoxon results

Across all 180 paired trials, every difference was positive. The average paired reduction \(D_{\text{off}} - D_{\text{on}}\) was 529.26 in the evaluator's distance units (median: 614.85). The one-sided Wilcoxon test gave \(W^+=16290\), \(W^-=0\), \(p=1.37\times10^{-31}\) (normal approximation), and \(r_{rb}=1.00\).

The per-instance tests each had \(n=30\), \(W^+=465\), \(W^-=0\), \(p=9.31\times10^{-10}\), and \(r_{rb}=1.00\). These remain significant with a Bonferroni-adjusted threshold of \(0.05/6\). The observed reductions are directionally consistent across all six instances.

## Interpretation and validity limitation

The output is statistically consistent with H1 **within the current prototype**, but it is not yet sufficient to claim that route freezing reduces real vehicle travel distance. The current evaluator measures coordinate distances along the planned route-node sequence, not distance traveled on a road network, and the DES does not execute vehicle movement events; the freeze mechanism is based on the first planned route node. Therefore, describe these as preliminary prototype results, not a validated operational or road-network result. A confirmatory H1 experiment requires actual pickup/delivery stop sequencing, vehicle movement and commitment lifecycle, a consistent distance matrix/network metric, and rerunning the paired trials.

## Draft text for a report

> Để đánh giá H1, mỗi cặp thực nghiệm được ghép theo cùng bộ dữ liệu và cùng seed. Đặt \(d_i=D_{\text{off},i}-D_{\text{on},i}\), trong đó \(d_i>0\) biểu thị cơ chế đóng băng cho giá trị khoảng cách thấp hơn. Kiểm định Wilcoxon signed-rank một phía được sử dụng với mức ý nghĩa \(\alpha=0{,}05\), với giả thuyết đối \(H_1\) là phân phối độ lệch được dịch chuyển theo hướng \(D_{\text{on}}<D_{\text{off}}\). Trên 180 cặp quan sát, cả 180 cặp đều có \(d_i>0\); mức giảm trung bình là 529,26 đơn vị khoảng cách (trung vị 614,85). Kiểm định cho \(W^+=16290\), \(W^-=0\), \(p=1{,}37\times10^{-31}\), cùng hệ số tương quan hạng biserial ghép cặp \(r_{rb}=1{,}00\). Kết quả theo từng instance cũng có ý nghĩa sau hiệu chỉnh Bonferroni. Do đó, kết quả prototype hiện tại có xu hướng và ý nghĩa thống kê phù hợp với H1. Tuy nhiên, vì khoảng cách được tính từ tọa độ các node trong route dự kiến thay vì quãng đường mạng đường thực tế, và mô phỏng chưa thực thi đầy đủ chuyển động xe, kết quả này chỉ nên được xem là sơ bộ; chưa đủ để kết luận H1 đã được xác nhận trong điều kiện vận hành thực tế.

Raw per-seed data: [`../raw/h1_raw.csv`](../raw/h1_raw.csv).
