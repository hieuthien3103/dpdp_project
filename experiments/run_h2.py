"""
Official Experiment Runner for H2: Candidate Filter Ablation Study.
Compares Greedy Insertion performance with candidate filtering enabled vs disabled
across standard Li & Lim benchmark instances using paired seeds.
Measures average decision time (t_dec), total distance (D), and service rate (SR).
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algorithms.greedy import GreedyInsertion
from src.metrics.evaluator import SolutionEvaluator
from src.simulation.dynamic_generator import parse_and_dynamize_li_lim
from src.simulation.entities import Vehicle
from src.simulation.engine import SimulationEngine


# Dynamically discover instances in the data directory
def list_instances(data_dir: Path) -> list[str]:
    """Return sorted list of instance base names (without .txt) in data_dir."""
    return [p.stem for p in sorted(data_dir.glob("*.txt"))]


CSV_FIELDS = (
    "instance",
    "seed",
    "rho",
    "filter_enabled",
    "candidate_k",
    "vehicle_count",
    "request_count",
    "dynamic_request_count",
    "served_count",
    "unserved_count",
    "service_rate_SR",
    "rejection_rate_RR",
    "total_distance_D",
    "active_vehicles",
    "avg_decision_time_ms",
    "total_decision_time_s",
    "reopt_cycles",
    "measurement_status",
)

MEASUREMENT_STATUS = "official_simulation_verified"


def _read_fleet_size(instance_path: Path) -> int:
    with instance_path.open("r", encoding="utf-8") as instance_file:
        header = instance_file.readline().split()

    if len(header) < 2:
        raise ValueError(f"Invalid Li & Lim header in {instance_path}")

    try:
        fleet_size = int(header[0])
    except ValueError as exc:
        raise ValueError(f"Invalid fleet size in {instance_path}: {header[0]!r}") from exc

    if fleet_size <= 0:
        raise ValueError(f"Fleet size must be positive in {instance_path}")

    return fleet_size


def _set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _run_condition(
    instance_path: Path,
    seed: int,
    rho: float,
    lead_time: float,
    filter_enabled: bool,
    candidate_k: int = 5,
    freeze_enabled: bool = True,
) -> dict[str, Any]:
    
    # 1. Generate dynamic requests & capacity
    requests, depot_info, capacity = parse_and_dynamize_li_lim(
        str(instance_path),
        rho=rho,
        lead_time=lead_time,
        seed=seed,
    )

    # 2. Initialize fleet
    fleet_size = _read_fleet_size(instance_path)
    vehicles = [
        Vehicle(vehicle_id=vid, capacity=capacity, start_node=0)
        for vid in range(fleet_size)
    ]

    # 3. Reset random state
    _set_random_seed(seed)

    # 4. Setup Simulation Engine
    sim_engine = SimulationEngine(time_horizon=1000.0, reoptimization_interval=10.0)
    sim_engine.setup_scenario(requests, vehicles, depot_info=depot_info)

    # 5. Instantiate Solver with or without candidate filter
    depot_xy = (depot_info.get("x", 0.0), depot_info.get("y", 0.0))
    solver = GreedyInsertion(
        capacity_constraint=capacity,
        depot_xy=depot_xy,
        filter_candidates=filter_enabled,
        candidate_k=candidate_k,
    )

    # 6. Execute DES Run (with route freezing enabled as established in H1)
    sim_result = sim_engine.run(solver=solver, freeze_enabled=freeze_enabled)

    # 7. Evaluate Metrics
    served_count = sim_result["serviced_count"]
    metrics = SolutionEvaluator.evaluate_performance(
        sim_result["vehicles"],
        requests,
        served_count,
    )

    decision_times = sim_result["decision_times"]
    avg_decision_time_ms = (sim_result["avg_decision_time"] * 1000.0) if decision_times else 0.0
    total_decision_time_s = sum(decision_times)

    result = {
        "instance": instance_path.stem,
        "seed": seed,
        "rho": rho,
        "filter_enabled": str(filter_enabled).lower(),
        "candidate_k": candidate_k if filter_enabled else fleet_size,
        "vehicle_count": fleet_size,
        "request_count": len(requests),
        "dynamic_request_count": sum(req.is_dynamic for req in requests),
        "served_count": served_count,
        "unserved_count": len(requests) - served_count,
        "service_rate_SR": metrics["service_rate_SR"],
        "rejection_rate_RR": metrics["rejection_rate_RR"],
        "total_distance_D": metrics["total_distance_D"],
        "active_vehicles": metrics["active_vehicles"],
        "avg_decision_time_ms": round(avg_decision_time_ms, 3),
        "total_decision_time_s": round(total_decision_time_s, 4),
        "reopt_cycles": len(decision_times),
        "measurement_status": MEASUREMENT_STATUS,
    }

    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run official paired H2 candidate-filtering ablation trials."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "li_lim_100",
        help="Directory containing the Li & Lim instances.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "raw" / "h2_raw.csv",
        help="CSV output path.",
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        default=None,
        help="Instance names. If omitted, all .txt files in data-dir are used.",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=30,
        help="Number of paired random seeds.",
    )
    parser.add_argument(
        "--seed-start",
        type=int,
        default=1,
        help="First random seed.",
    )
    parser.add_argument(
        "--rho",
        type=float,
        default=0.5,
        help="Dynamic request ratio.",
    )
    parser.add_argument(
        "--lead-time",
        type=float,
        default=15.0,
        help="Lead time for dynamic requests.",
    )
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=5,
        help="Top-k candidate vehicles to evaluate per request.",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()

    # Determine which instances to run
    if args.instances:
        instance_names = args.instances
    else:
        instance_names = list_instances(data_dir)
    instance_paths = [data_dir / f"{name}.txt" for name in instance_names]

    for path in instance_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing instance file: {path}")

    rows = []
    total_trials = len(instance_paths) * args.seeds * 2
    completed_trials = 0

    print("=" * 65)
    print("OFFICIAL H2 CANDIDATE FILTER ABLATION EXPERIMENT")
    print("=" * 65)
    print(f"Instances     : {len(instance_paths)}")
    print(f"Seeds         : {args.seeds}")
    print(f"Dynamic ratio : {args.rho}")
    print(f"Candidate k   : {args.candidate_k}")
    print(f"Total trials  : {total_trials}")
    print("-" * 65)

    for instance_path in instance_paths:
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for filter_enabled in (False, True):
                result = _run_condition(
                    instance_path=instance_path,
                    seed=seed,
                    rho=args.rho,
                    lead_time=args.lead_time,
                    filter_enabled=filter_enabled,
                    candidate_k=args.candidate_k,
                )
                rows.append(result)
                completed_trials += 1
                condition = "FILTER_ON" if filter_enabled else "FILTER_OFF"
                print(
                    f"[{completed_trials}/{total_trials}] "
                    f"{instance_path.stem} | Seed={seed} | {condition} | "
                    f"t_dec={result['avg_decision_time_ms']}ms | Dist={result['total_distance_D']}"
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 65)
    print("EXPERIMENT COMPLETED SUCCESSFULLY")
    print(f"Total records saved: {len(rows)}")
    print(f"CSV output path    : {output_path}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
