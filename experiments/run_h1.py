"""
Official Experiment Runner for H1: Frozen-Commitment Mechanism.
Compares Greedy Insertion performance with freezing enabled vs disabled
across standard Li & Lim benchmark instances using paired seeds.
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


DEFAULT_INSTANCES = (
    "lc101",
    "lc201",
    "lr101",
    "lr201",
    "lrc101",
    "lrc201",
)

CSV_FIELDS = (
    "instance",
    "seed",
    "rho",
    "freeze_enabled",
    "vehicle_count",
    "request_count",
    "dynamic_request_count",
    "served_count",
    "unserved_count",
    "service_rate_SR",
    "rejection_rate_RR",
    "total_distance_D",
    "active_vehicles",
    "measurement_status",
)

MEASUREMENT_STATUS = "official_simulation_verified"


# ============================================================
# DATA VALIDATION
# ============================================================

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


# ============================================================
# RANDOM SEED CONTROL
# ============================================================

def _set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


# ============================================================
# EXPERIMENTAL CONDITION
# ============================================================

def _run_condition(
    instance_path: Path,
    seed: int,
    rho: float,
    lead_time: float,
    freeze_enabled: bool,
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

    # 4. Setup Simulation Engine (now passes depot_info for coordinates)
    sim_engine = SimulationEngine(time_horizon=1000.0, reoptimization_interval=10.0)
    sim_engine.setup_scenario(requests, vehicles, depot_info=depot_info)

    # 5. Instantiate Solver (Greedy with depot coordinates for Euclidean cost)
    depot_xy = (depot_info.get("x", 0.0), depot_info.get("y", 0.0))
    solver = GreedyInsertion(capacity, depot_xy=depot_xy)

    # Note: If freeze_enabled is False, we pass empty frozen commitments
    # To properly simulate H1 behavior, the DES engine handles reoptimization cycles.
    # Here we execute the simulation run with the solver.
    sim_result = sim_engine.run(solver=solver, freeze_enabled=freeze_enabled)
    # 6. Evaluate Performance
    served_count = sim_result["serviced_count"]
    metrics = SolutionEvaluator.evaluate_performance(
        sim_result["vehicles"],
        requests,
        served_count,
    )

    result = {
        "instance": instance_path.stem,
        "seed": seed,
        "rho": rho,
        "freeze_enabled": str(freeze_enabled).lower(),
        "vehicle_count": fleet_size,
        "request_count": len(requests),
        "dynamic_request_count": sum(req.is_dynamic for req in requests),
        "served_count": served_count,
        "unserved_count": len(requests) - served_count,
        "service_rate_SR": metrics["service_rate_SR"],
        "rejection_rate_RR": metrics["rejection_rate_RR"],
        "total_distance_D": metrics["total_distance_D"],
        "active_vehicles": metrics["active_vehicles"],
        "measurement_status": MEASUREMENT_STATUS,
    }

    return result


# ============================================================
# ARGUMENT PARSER
# ============================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run official paired H1 trials and export raw CSV data."
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
        default=PROJECT_ROOT / "results" / "raw" / "h1_raw.csv",
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

    return parser.parse_args()


# ============================================================
# MAIN EXPERIMENT
# ============================================================

def main() -> int:
    args = _parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()

    instance_paths = [data_dir / f"{name}.txt" for name in args.instances]
    for path in instance_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing instance file: {path}")

    rows = []
    total_trials = len(instance_paths) * args.seeds * 2
    completed_trials = 0

    print("=" * 65)
    print("OFFICIAL H1 FROZEN-COMMITMENT EXPERIMENT")
    print("=" * 65)
    print(f"Instances     : {len(instance_paths)}")
    print(f"Seeds         : {args.seeds}")
    print(f"Dynamic ratio : {args.rho}")
    print(f"Total trials  : {total_trials}")
    print("-" * 65)

    for instance_path in instance_paths:
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for freeze_enabled in (False, True):
                result = _run_condition(
                    instance_path=instance_path,
                    seed=seed,
                    rho=args.rho,
                    lead_time=args.lead_time,
                    freeze_enabled=freeze_enabled,
                )
                rows.append(result)
                completed_trials += 1
                condition = "FREEZE_ON" if freeze_enabled else "FREEZE_OFF"
                print(
                    f"[{completed_trials}/{total_trials}] "
                    f"{instance_path.stem} | Seed={seed} | {condition} | "
                    f"Served={result['served_count']} | Distance={result['total_distance_D']}"
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