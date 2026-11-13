import time
import random
import numpy as np
from typing import List, Dict

from src.simulation.entities import Request, Vehicle
from src.algorithms.alns_operators import ALNSOperators
from src.algorithms.regret2 import Regret2Insertion


class ALNS_D:
    def __init__(
        self,
        capacity_constraint: float,
        time_budget: float = 2.0,
        max_iterations: int = 1000
    ):
        self.capacity_constraint = capacity_constraint
        self.time_budget = time_budget
        self.max_iterations = max_iterations

        self.operators = ALNSOperators(capacity_constraint)
        self.regret2_solver = Regret2Insertion(capacity_constraint)

    def solve(
        self,
        pending_requests: List[Request],
        vehicles: Dict[int, Vehicle],
        frozen_commitments: Dict[int, int]
    ) -> List[Request]:
        """
        ALNS-D: Adaptive Large Neighborhood Search - Dynamic.
        Trả về danh sách các request chưa được phục vụ thực tế (unserved requests).
        """
        start_time = time.time()
        free_requests = pending_requests.copy()

        if not free_requests:
            return []

        # 1. Khởi tạo nghiệm ban đầu bằng Regret-2 (có truyền frozen_commitments)
        current_vehicles = self._clone_vehicles(vehicles)
        unassigned_after_init = self.regret2_solver.solve(
            free_requests,
            current_vehicles,
            frozen_commitments
        )
        
        # Xác định các request đã được phục vụ thành công trong nghiệm ban đầu
        assigned_reqs = [r for r in free_requests if r not in unassigned_after_init]

        best_vehicles = self._clone_vehicles(current_vehicles)
        best_cost = self._evaluate_solution_cost(best_vehicles)

        current_vehicles = self._clone_vehicles(best_vehicles)
        current_cost = best_cost

        # Tham số Simulated Annealing
        iteration = 0
        temperature = 100.0
        cooling_rate = 0.98

        # Vòng lặp ALNS-D
        while (
            time.time() - start_time < self.time_budget
            and iteration < self.max_iterations
        ):
            iteration += 1
            nu = random.randint(1, max(1, len(assigned_reqs) // 3)) if assigned_reqs else 1

            # 4.1 Destroy (Truyền frozen_commitments để bảo vệ các nút đang di chuyển)
            destroyed_vehicles, removed_reqs = self.operators.random_removal(
                self._clone_vehicles(current_vehicles),
                nu,
                frozen_commitments
            )

            # 4.2 Repair (Truyền frozen_commitments)
            repaired_vehicles = self.operators.greedy_repair(
                destroyed_vehicles,
                removed_reqs,
                frozen_commitments
            )

            new_cost = self._evaluate_solution_cost(repaired_vehicles)
            cost_diff = new_cost - current_cost

            # 4.3 Acceptance Criterion (Simulated Annealing)
            if (
                cost_diff < 0
                or random.random() < np.exp(-cost_diff / max(temperature, 1e-5))
            ):
                current_vehicles = self._clone_vehicles(repaired_vehicles)
                current_cost = new_cost

                if current_cost < best_cost:
                    best_cost = current_cost
                    best_vehicles = self._clone_vehicles(current_vehicles)

            temperature *= cooling_rate

        # Cập nhật trạng thái đội xe tốt nhất
        for vid, veh in vehicles.items():
            if vid in best_vehicles:
                veh.route = list(best_vehicles[vid].route)
                veh.current_load = best_vehicles[vid].current_load

        # Xác định lại danh sách request chưa được phục vụ thực tế sau tối ưu
        serviced_request_ids = set()
        for veh in vehicles.values():
            for r_id in veh.route:
                serviced_request_ids.add(r_id)
                
        final_unserved = [req for req in pending_requests if req.req_id not in serviced_request_ids]
        return final_unserved

    def _clone_vehicles(self, vehicles: Dict[int, Vehicle]) -> Dict[int, Vehicle]:
        cloned = {}
        for vid, vehicle in vehicles.items():
            new_vehicle = Vehicle(
                vehicle.vehicle_id,
                vehicle.capacity,
                vehicle.current_node
            )
            new_vehicle.current_load = vehicle.current_load
            new_vehicle.route = list(vehicle.route)
            new_vehicle.is_moving = vehicle.is_moving
            new_vehicle.destination_node = vehicle.destination_node
            cloned[vid] = new_vehicle
        return cloned

    def _evaluate_solution_cost(self, vehicles: Dict[int, Vehicle]) -> float:
        total_cost = 0.0
        for vehicle in vehicles.values():
            total_cost += len(vehicle.route) * 15.0 + vehicle.current_load * 2.0
        return total_cost