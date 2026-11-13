import time
import random
import math
import numpy as np
from typing import List, Dict, Tuple, Optional

from src.simulation.entities import Request, Vehicle
from src.algorithms.alns_operators import ALNSOperators
from src.algorithms.regret2 import Regret2Insertion
from src.algorithms.greedy import GreedyInsertion


class ALNS_D:
    def __init__(
        self,
        capacity_constraint: float,
        depot_xy: Tuple[float, float] = (0.0, 0.0),
        time_budget: float = 2.0,
        max_iterations: int = 1000,
        use_adaptive_weights: bool = True,
        reaction_factor: float = 0.1,
        sigma_1: float = 33.0,
        sigma_2: float = 9.0,
        sigma_3: float = 3.0,
    ):
        self.capacity_constraint = capacity_constraint
        self.depot_xy = depot_xy
        self.time_budget = time_budget
        self.max_iterations = max_iterations
        self.use_adaptive_weights = use_adaptive_weights
        self.reaction_factor = reaction_factor

        self.sigma_1 = sigma_1
        self.sigma_2 = sigma_2
        self.sigma_3 = sigma_3

        self.operators = ALNSOperators(capacity_constraint, depot_xy)
        self.initial_solver = GreedyInsertion(capacity_constraint, depot_xy)

        # Định nghĩa các toán tử: 2 Destroy, 2 Repair
        self.destroy_ops = ["random_removal", "worst_removal"]
        self.repair_ops = ["greedy_repair", "regret_repair"]

        # Trọng số của các toán tử
        self.destroy_weights = {op: 1.0 for op in self.destroy_ops}
        self.repair_weights = {op: 1.0 for op in self.repair_ops}

        # Điểm số tích lũy & số lần sử dụng
        self.destroy_scores = {op: 0.0 for op in self.destroy_ops}
        self.repair_scores = {op: 0.0 for op in self.repair_ops}
        self.destroy_counts = {op: 0 for op in self.destroy_ops}
        self.repair_counts = {op: 0 for op in self.repair_ops}

        self._node_coords: Dict[int, Tuple[float, float]] = {}

    def _build_node_coords(self, pending_requests: List[Request], vehicles: Dict[int, Vehicle]) -> None:
        self._node_coords = {0: self.depot_xy}
        for v in vehicles.values():
            if v.current_x is not None and v.current_y is not None:
                self._node_coords[v.current_node] = (v.current_x, v.current_y)
        for req in pending_requests:
            if req.pickup_x is not None and req.pickup_y is not None:
                self._node_coords[req.pickup_node] = (req.pickup_x, req.pickup_y)
            if req.delivery_x is not None and req.delivery_y is not None:
                self._node_coords[req.delivery_node] = (req.delivery_x, req.delivery_y)
        self.operators.set_node_coords(self._node_coords)

    def _select_operator(self, ops: List[str], weights: Dict[str, float]) -> str:
        if not self.use_adaptive_weights:
            return random.choice(ops)
        total = sum(weights[op] for op in ops)
        if total <= 0:
            return random.choice(ops)
        probs = [weights[op] / total for op in ops]
        return random.choices(ops, weights=probs, k=1)[0]

    def solve(
        self,
        pending_requests: List[Request],
        vehicles: Dict[int, Vehicle],
        frozen_commitments: Dict[int, int],
    ) -> List[Request]:
        """
        ALNS-D Solver chính tuân thủ ngân sách thời gian thực time_budget (B).
        """
        start_time = time.perf_counter()
        if not pending_requests:
            return []

        self._build_node_coords(pending_requests, vehicles)
        requests_dict = {req.req_id: req for req in pending_requests}

        # 1. Sinh nghiệm khởi tạo s_0 bằng GreedyInsertion tuân thủ frozen_commitments
        current_vehicles = self._clone_vehicles(vehicles)
        unassigned_after_init = self.initial_solver.solve(
            pending_requests,
            current_vehicles,
            frozen_commitments,
        )

        for v in current_vehicles.values():
            for rid in v.route:
                if rid in requests_dict:
                    requests_dict[rid].assigned_vehicle_id = v.vehicle_id

        best_vehicles = self._clone_vehicles(current_vehicles)
        best_cost = self._evaluate_solution_cost(best_vehicles)
        current_cost = best_cost

        # Tham số Simulated Annealing
        temperature = 100.0
        cooling_rate = 0.98
        iteration = 0

        # Vòng lặp ALNS giới hạn nghiêm ngặt theo time_budget
        while (time.perf_counter() - start_time < self.time_budget) and (iteration < self.max_iterations):
            iteration += 1

            # Lấy danh sách các đơn đã được xếp vào xe
            assigned_req_ids = []
            for v in current_vehicles.values():
                assigned_req_ids.extend(v.route)

            if not assigned_req_ids:
                break

            q = random.randint(1, max(1, len(assigned_req_ids) // 3))

            # Chọn toán tử
            d_op = self._select_operator(self.destroy_ops, self.destroy_weights)
            r_op = self._select_operator(self.repair_ops, self.repair_weights)

            self.destroy_counts[d_op] += 1
            self.repair_counts[r_op] += 1

            # Phá hủy
            cloned = self._clone_vehicles(current_vehicles)
            if d_op == "random_removal":
                destroyed, removed = self.operators.random_removal(cloned, q, frozen_commitments, requests_dict)
            else:
                destroyed, removed = self.operators.worst_removal(cloned, q, frozen_commitments, requests_dict)

            # Sửa chữa
            if r_op == "greedy_repair":
                repaired = self.operators.greedy_repair(destroyed, removed, frozen_commitments)
            else:
                repaired = self.operators.regret_repair(destroyed, removed, frozen_commitments)

            new_cost = self._evaluate_solution_cost(repaired)
            cost_diff = new_cost - current_cost

            # Đánh giá điểm thưởng theo ALNS (sigma_1, sigma_2, sigma_3)
            reward = 0.0
            if new_cost < best_cost:
                reward = self.sigma_1
                best_cost = new_cost
                best_vehicles = self._clone_vehicles(repaired)
                current_cost = new_cost
                current_vehicles = self._clone_vehicles(repaired)
            elif cost_diff < 0:
                reward = self.sigma_2
                current_cost = new_cost
                current_vehicles = self._clone_vehicles(repaired)
            elif random.random() < math.exp(-cost_diff / max(temperature, 1e-5)):
                reward = self.sigma_3
                current_cost = new_cost
                current_vehicles = self._clone_vehicles(repaired)

            if self.use_adaptive_weights:
                self.destroy_scores[d_op] += reward
                self.repair_scores[r_op] += reward

            temperature *= cooling_rate

        # Cập nhật trọng số thích nghi sau chu kỳ (Roulette Wheel Weights Update)
        if self.use_adaptive_weights:
            for op in self.destroy_ops:
                if self.destroy_counts[op] > 0:
                    score_avg = self.destroy_scores[op] / self.destroy_counts[op]
                    self.destroy_weights[op] = (1 - self.reaction_factor) * self.destroy_weights[op] + self.reaction_factor * score_avg
                    self.destroy_scores[op] = 0.0
                    self.destroy_counts[op] = 0

            for op in self.repair_ops:
                if self.repair_counts[op] > 0:
                    score_avg = self.repair_scores[op] / self.repair_counts[op]
                    self.repair_weights[op] = (1 - self.reaction_factor) * self.repair_weights[op] + self.reaction_factor * score_avg
                    self.repair_scores[op] = 0.0
                    self.repair_counts[op] = 0

        # Áp nghiệm tốt nhất vào đội xe
        for vid, veh in vehicles.items():
            if vid in best_vehicles:
                veh.route = list(best_vehicles[vid].route)
                veh.route_nodes = list(best_vehicles[vid].route_nodes)
                veh.current_load = best_vehicles[vid].current_load

        serviced_request_ids = set()
        for veh in vehicles.values():
            for r_id in veh.route:
                serviced_request_ids.add(r_id)

        return [req for req in pending_requests if req.req_id not in serviced_request_ids]

    def _clone_vehicles(self, vehicles: Dict[int, Vehicle]) -> Dict[int, Vehicle]:
        cloned = {}
        for vid, vehicle in vehicles.items():
            new_vehicle = Vehicle(
                vehicle.vehicle_id,
                vehicle.capacity,
                vehicle.current_node,
                vehicle.current_x,
                vehicle.current_y,
            )
            new_vehicle.current_load = vehicle.current_load
            new_vehicle.route = list(vehicle.route)
            new_vehicle.route_nodes = list(vehicle.route_nodes)
            new_vehicle.is_moving = vehicle.is_moving
            new_vehicle.destination_node = vehicle.destination_node
            new_vehicle.total_distance = vehicle.total_distance
            new_vehicle.completed_request_ids = list(vehicle.completed_request_ids)
            cloned[vid] = new_vehicle
        return cloned

    def _evaluate_solution_cost(self, vehicles: Dict[int, Vehicle]) -> float:
        """Tổng chiều dài đường đi của tất cả các node trong route_nodes."""
        total_dist = 0.0
        for v in vehicles.values():
            route = v.route_node_sequence()
            if not route:
                continue
            prev = v.current_node
            for node in route:
                c1 = self._node_coords.get(prev, self.depot_xy)
                c2 = self._node_coords.get(node, self.depot_xy)
                total_dist += math.hypot(c2[0] - c1[0], c2[1] - c1[1])
                prev = node
        return total_dist
