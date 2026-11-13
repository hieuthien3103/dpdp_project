"""
Master Experiment Runner for ALNS-DPDP.
Executes all evaluation pipelines and hypothesis tests (H1 through H4)
sequentially and logs raw experimental metrics.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def run_script(script_name: str, extra_args: list[str] = None) -> None:
    script_path = PROJECT_ROOT / "experiments" / script_name
    if not script_path.is_file():
        print(f"❌ Không tìm thấy script thực nghiệm: {script_path}")
        return

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n🚀 Đang chạy pipeline: {script_name} ...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"⚠️ Cảnh báo: Script {script_name} kết thúc với mã lỗi {result.returncode}")
    else:
        print(f"✅ Hoàn thành thành công: {script_name}")


def main() -> int:
    print("=" * 70)
    print("MASTER EXPERIMENT PIPELINE (H1 - H4)")
    print("=" * 70)

    # 1. Chạy thực nghiệm H1 (Đánh giá cơ chế Đóng băng cam kết)
    run_script("run_h1.py", ["--seeds", "10"])

    # 2. Chạy thực nghiệm H2 (Ablation Study: Bộ lọc ứng viên)
    if (PROJECT_ROOT / "experiments" / "run_h2.py").is_file():
        run_script("run_h2.py")

    # 3. Chạy thực nghiệm H3 (Quét ngân sách thời gian B)
    if (PROJECT_ROOT / "experiments" / "run_h3.py").is_file():
        run_script("run_h3.py")

    # 4. Chạy thực nghiệm H4 (Quét mức độ động rho)
    if (PROJECT_ROOT / "experiments" / "run_h4.py").is_file():
        run_script("run_h4.py")

    print("\n" + "=" * 70)
    print("🎉 TẤT CẢ CÁC KỊCH BẢN THỰC NGHIỆM ĐÃ HOÀN TẤT!")
    print("📁 Dữ liệu kết quả raw được lưu tại thư mục: results/raw/")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())