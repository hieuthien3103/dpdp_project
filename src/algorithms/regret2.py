from typing import List, Dict, Tuple, Optional
import numpy as np
from src.simulation.entities import Request, Vehicle

class Regret2Insertion:
    def __init__(self, capacity_constraint: float):
        self.capacity_constraint = capacity_constraint

    def solve(self, pending_requests: List[Request], vehicles: Dict[int, Vehicle], frozen_commitments: Dict[int, int]) -> List[Request]:
        """
        Thực thi thuật toán Regret-2 Insertion:
        Tính giá trị hối tiếc c_r^{(2)} = delta_f^{(2)} - delta_f^{(1)} cho mỗi yêu cầu,
        tuân thủ frozen_commitments.
        """
        unassigned = pending_requests.copy()
        
        while unassigned:
            best_req: Optional[Request] = None
            best_vehicle_id: Optional[int] = None
            best_insert_idx: int = -1
            max_regret_value = -1.0
            
            for req in unassigned:
                costs_for_req = []
                
                for vid, vehicle in vehicles.items():
                    frozen_node = frozen_commitments.get(vid)
                    cost, idx = self._evaluate_insertion(req, vehicle, frozen_node)
                    if cost != float('inf') and idx != -1:
                        costs_for_req.append((cost, vid, idx))
                
                costs_for_req.sort(key=lambda x: x[0])
                
                if len(costs_for_req) == 0:
                    continue
                elif len(costs_for_req) == 1:
                    regret_val = float('inf')
                    best_cost, b_vid, b_idx = costs_for_req[0]
                else:
                    cost_1, vid_1, idx_1 = costs_for_req[0]
                    cost_2, vid_2, idx_2 = costs_for_req[1]
                    regret_val = cost_2 - cost_1
                    best_cost, b_vid, b_idx = cost_1, vid_1, idx_1
                
                if regret_val > max_regret_value or max_regret_value == -1.0:
                    max_regret_value = regret_val
                    best_req = req
                    best_vehicle_id = b_vid
                    best_insert_idx = b_idx

            if best_req is not None and best_vehicle_id is not None:
                self._insert_request(vehicles[best_vehicle_id], best_req, best_insert_idx)
                unassigned.remove(best_req)
            else:
                break
                
        return unassigned

    def _evaluate_insertion(self, req: Request, vehicle: Vehicle, frozen_node: Optional[int]) -> Tuple[float, int]:
        if vehicle.current_load + req.demand > self.capacity_constraint:
            return float('inf'), -1
            
        min_allowed_idx = 0
        if frozen_node is not None and frozen_node in vehicle.route:
            frozen_idx = vehicle.route.index(frozen_node)
            min_allowed_idx = frozen_idx + 1
            
        best_cost = float('inf')
        best_idx = -1
        
        for idx in range(min_allowed_idx, len(vehicle.route) + 1):
            mock_cost = req.e_pickup * 0.05 + idx * 0.5
            if mock_cost < best_cost:
                best_cost = mock_cost
                best_idx = idx
                
        return best_cost if best_idx != -1 else float('inf'), best_idx

    def _insert_request(self, vehicle: Vehicle, req: Request, index: int):
        vehicle.route.insert(index, req.req_id)
        vehicle.current_load += req.demand