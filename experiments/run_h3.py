"""
Official Experiment Runner for H3: Adaptive Weights under Tight Time Budgets.
Investigates the role and degradation of ALNS adaptive operator weights
when the decision time budget B per reoptimization cycle is constricted:
B in {0.05s, 0.2s, 1.0s} under ADAPTIVE_ON vs ADAPTIVE_OFF.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algorithms.alns_d import ALNS_D
from src.metrics.evaluator import SolutionEvaluator
from src.simulation.dynamic_generator import parse_and_dynamize_li_lim
from src.simulation.entities import Vehicle
from src.simulation.engine import SimulationEngine

DEFAULT_INSTANCES = (
    "lc101",
    "lc201",
    "lr101",
    "lr201",
    "lrc101",
    "lrc201",
)

DEFAULT_BUDGETS = (0.05, 0.20, 1.00)

CSV_FIELDS = (
    "instance",
    "seed",
    "rho",
    "time_budget_B",
    "adaptive_weights",
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
    "reopt_cycles",
    "measurement_status",
)

MEASUREMENT_STATUS = "official_simulation_verified"


def _read_fleet_size(instance_path: Path) -> int:
    with instance_path.open("r", encoding="utf-8") as instance_file:
        header = instance_file.readline().split()
    return int(header[0])


def _set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _run_condition(
    instance_path: Path,
    seed: int,
    rho: float,
    lead_time: float,
    time_budget: float,
    adaptive_weights: bool,
) -> dict[str, Any]:
    
    requests, depot_info, capacity = parse_and_dynamize_li_lim(
        str(instance_path),
        rho=rho,
        lead_time=lead_time,
        seed=seed,
    )

    fleet_size = _read_fleet_size(instance_path)
    vehicles = [
        Vehicle(vehicle_id=vid, capacity=capacity, start_node=0)
        for vid in range(fleet_size)
    ]

    _set_random_seed(seed)

    sim_engine = SimulationEngine(time_horizon=1000.0, reoptimization_interval=10.0)
    sim_engine.setup_scenario(requests, vehicles, depot_info=depot_info)

    depot_xy = (depot_info.get("x", 0.0), depot_info.get("y", 0.0))
    solver = ALNS_D(
        capacity_constraint=capacity,
        depot_xy=depot_xy,
        time_budget=time_budget,
        use_adaptive_weights=adaptive_weights,
    )

    sim_result = sim_engine.run(solver=solver, freeze_enabled=True)

    served_count = sim_result["serviced_count"]
    metrics = SolutionEvaluator.evaluate_performance(
        sim_result["vehicles"],
        requests,
        served_count,
    )

    avg_decision_time_ms = (sim_result["avg_decision_time"] * 1000.0) if sim_result["decision_times"] else 0.0

    return {
        "instance": instance_path.stem,
        "seed": seed,
        "rho": rho,
        "time_budget_B": time_budget,
        "adaptive_weights": str(adaptive_weights).lower(),
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
        "reopt_cycles": len(sim_result["decision_times"]),
        "measurement_status": MEASUREMENT_STATUS,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run official H3 trials evaluating ALNS adaptive weights across time budgets."
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
        default=PROJECT_ROOT / "results" / "raw" / "h3_raw.csv",
        help="CSV output path.",
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        default=DEFAULT_INSTANCES,
        choices=DEFAULT_INSTANCES,
        help="Instance names.",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=10,
        help="Number of paired random seeds per budget.",
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
        "--budgets",
        nargs="+",
        type=float,
        default=DEFAULT_BUDGETS,
        help="Time budget B values in seconds.",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()

    instance_paths = [data_dir / f"{name}.txt" for name in args.instances]
    for path in instance_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing instance file: {path}")

    rows = []
    total_trials = len(instance_paths) * args.seeds * len(args.budgets) * 2
    completed_trials = 0

    print("=" * 65)
    print("OFFICIAL H3 ADAPTIVE WEIGHTS TIME BUDGET EXPERIMENT")
    print("=" * 65)
    print(f"Instances     : {len(instance_paths)}")
    print(f"Seeds         : {args.seeds}")
    print(f"Budgets B (s) : {args.budgets}")
    print(f"Total trials  : {total_trials}")
    print("-" * 65)

    for budget in args.budgets:
        for instance_path in instance_paths:
            for seed in range(args.seed_start, args.seed_start + args.seeds):
                for adaptive in (False, True):
                    result = _run_condition(
                        instance_path=instance_path,
                        seed=seed,
                        rho=args.rho,
                        lead_time=15.0,
                        time_budget=budget,
                        adaptive_weights=adaptive,
                    )
                    rows.append(result)
                    completed_trials += 1
                    cond = "ADAPT_ON" if adaptive else "ADAPT_OFF"
                    print(
                        f"[{completed_trials}/{total_trials}] "
                        f"B={budget}s | {instance_path.stem} | Seed={seed} | {cond} | "
                        f"D={result['total_distance_D']} | SR={result['service_rate_SR']*100:.1f}%"
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
