# H1 Comparison Summary — Frozen-Commitment Mechanism

Summary across all 30 paired seeds for each Li & Lim instance. Distance `D` is the Euclidean travel distance accumulated by the DES engine through actual vehicle movement events (pickup → delivery stop sequences). The freeze mechanism locks the vehicle's next committed stop so the solver cannot reassign it during reoptimization.

| Instance | Paired seeds | Requests | Served (off/on) | Service rate (off/on) | D mean, freeze off | D mean, freeze on | Δ D (on − off) |
|---|---:|---:|---:|---:|---:|---:|---:|
| lc101 | 30 | 53 | 53.00 / 53.00 | 100.0% / 100.0% | 1401.86 | 1440.79 | +38.93 |
| lc201 | 30 | 51 | 39.43 / 37.53 | 77.3% / 73.6% | 1730.48 | 1664.38 | -66.10 |
| lr101 | 30 | 53 | 53.00 / 53.00 | 100.0% / 100.0% | 1707.13 | 1706.11 | -1.02 |
| lr201 | 30 | 51 | 41.10 / 39.63 | 80.6% / 77.7% | 1694.50 | 1627.86 | -66.64 |
| lrc101 | 30 | 53 | 53.00 / 53.00 | 100.0% / 100.0% | 2024.82 | 2030.23 | +5.41 |
| lrc201 | 30 | 51 | 27.97 / 25.20 | 54.8% / 49.4% | 1811.82 | 1596.92 | -214.91 |

## Statistical definition

For each paired instance-seed trial \(i\), define \(d_i = D_{\text{off},i} - D_{\text{on},i}\), where a positive value means the freeze-on run has a lower measured distance.

- \(H_0\): the distribution of paired differences is symmetric about zero.
- \(H_1\): the distribution of paired differences is shifted positively (\(D_{\text{on}} < D_{\text{off}}\)).
- Use a one-sided Wilcoxon signed-rank test with \(\alpha = 0.05\), pairing by the same instance and seed. The directional alternative is specified before examining results.
- Report the paired rank-biserial correlation \(r_{rb}=(W^+ - W^-)/(W^+ + W^-)\). This is the appropriate rank-based effect size for paired observations.

## Wilcoxon results

### Overall (all 180 paired trials pooled)

Across all 180 paired trials (174 non-zero differences), the one-sided Wilcoxon test gave:

- \(W^+ = 10001.5\), \(W^- = 5223.5\)
- \(p = 1.65 \times 10^{-4}\) (significant at \(\alpha = 0.05\))
- \(r_{rb} = 0.3138\) (small-to-medium effect size)
- Mean paired reduction \(\bar{d} = 50.72\) distance units, Median \(\tilde{d} = 18.56\)

### Per-instance results (Bonferroni-adjusted, k=6)

| Instance | n | W+ | W- | p (raw) | p (adjusted) | r_rb | Significant? |
|---|---:|---:|---:|---:|---:|---:|---|
| lc101 | 30 | 149.0 | 316.0 | 0.9580 | 1.0000 | -0.3591 | No |
| lc201 | 29 | 352.0 | 83.0 | 0.0018 | 0.0109 | 0.6184 | **Yes** |
| lr101 | 30 | 239.0 | 226.0 | 0.4516 | 1.0000 | 0.0280 | No |
| lr201 | 28 | 296.0 | 110.0 | 0.0171 | 0.1026 | 0.4581 | No |
| lrc101 | 29 | 200.0 | 235.0 | 0.6474 | 1.0000 | -0.0805 | No |
| lrc201 | 28 | 375.0 | 31.0 | 0.0000 | 0.0003 | 0.8473 | **Yes** |

## Interpretation

The overall Wilcoxon test rejects \(H_0\) with \(p = 1.65 \times 10^{-4}\), indicating that freezing committed routes provides a statistically significant reduction in total travel distance when pooling all instances.

However, the per-instance analysis reveals a **heterogeneous** pattern:

1. **Instances with wide time windows** (lc201, lr201, lrc201): Freezing tends to reduce distance. This makes sense because with wider time windows, the greedy solver has more flexibility, and freezing prevents costly last-minute rerouting. lc201 and lrc201 are significant after Bonferroni correction.

2. **Instances with tight time windows** (lc101, lr101, lrc101): Freezing has no significant effect, or may slightly increase distance. Tight time windows already constrain the solver's choices, so the commitment mechanism adds little benefit.

3. **Trade-off with service rate**: On instances where freeze_on reduces distance (lc201, lr201, lrc201), there is a slight decrease in service rate (fewer requests served). The commitment mechanism may cause some requests to become infeasible when the solver cannot reassign vehicles.

The overall effect size \(r_{rb} = 0.31\) represents a small-to-medium effect. The mechanism's benefit is instance-dependent, with the strongest improvement on problems with wide time windows and high dynamism.

## Figures

- [Paired differences boxplot](../figures/h1/h1_paired_differences.png)
- [Distance comparison bar chart](../figures/h1/h1_distance_comparison.png)
- [Effect size forest plot](../figures/h1/h1_effect_size.png)

## Draft text for report

> Để đánh giá H1, mỗi cặp thực nghiệm được ghép theo cùng bộ dữ liệu và cùng seed. Đặt \(d_i=D_{\text{off},i}-D_{\text{on},i}\), trong đó \(d_i>0\) biểu thị cơ chế đóng băng cho giá trị khoảng cách thấp hơn. Kiểm định Wilcoxon signed-rank một phía được sử dụng với mức ý nghĩa \(\alpha=0{,}05\), với giả thuyết đối \(H_1\) là phân phối độ lệch được dịch chuyển theo hướng \(D_{\text{on}}<D_{\text{off}}\).
>
> Trên 180 cặp quan sát (174 hiệu khác 0), kiểm định cho \(W^+=10001{,}5\), \(W^-=5223{,}5\), \(p=1{,}65\times10^{-4}\), cùng hệ số tương quan hạng biserial ghép cặp \(r_{rb}=0{,}31\). Mức giảm trung bình là 50,72 đơn vị khoảng cách (trung vị 18,56). Kết quả cho phép bác bỏ \(H_0\) ở mức tổng thể.
>
> Phân tích theo từng instance cho thấy tác động không đồng nhất: các instance có cửa sổ thời gian rộng (lc201, lrc201) có ý nghĩa thống kê sau hiệu chỉnh Bonferroni (\(p_{adj}=0{,}011\) và \(0{,}0003\)), với kích thước hiệu ứng lớn (\(r_{rb}=0{,}62\) và \(0{,}85\)). Các instance có cửa sổ thời gian chặt (lc101, lr101, lrc101) không có sự khác biệt có ý nghĩa.
>
> Cơ chế đóng băng cam kết có hiệu quả rõ rệt nhất trên các bài toán có cửa sổ thời gian rộng, nơi solver có nhiều không gian tái tối ưu. Tuy nhiên, tồn tại đánh đổi nhỏ với tỷ lệ phục vụ: một số yêu cầu có thể không khả thi khi lộ trình bị khóa.

Raw per-seed data: [`../raw/h1_raw.csv`](../raw/h1_raw.csv).
