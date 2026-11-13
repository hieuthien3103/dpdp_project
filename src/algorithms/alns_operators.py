import random
import numpy as np
from typing import List, Dict, Tuple
from src.simulation.entities import Request, Vehicle

class ALNSOperators:
    def __init__(self, capacity_constraint: float):
        self.capacity_constraint = capacity_constraint

    def random_removal(
        self, 
        vehicles: Dict[int, Vehicle], 
        num_to_remove: int, 
        frozen_commitments: Dict[int, int]
    ) -> Tuple[Dict[int, Vehicle], List[Request]]:
        """
        Loại ngẫu nhiên q yêu cầu khỏi lộ trình, 
        TUYỆT ĐỐI KHÔNG loại bỏ các request nằm tại frozen_commitments (H1).
        """
        active_requests_in_routes = []
        frozen_nodes_set = set(frozen_commitments.values())

        for vehicle in vehicles.values():
            for req_id in vehicle.route:
                # Không cho phép remove node đang bị đóng băng hướng tới
                if req_id not in frozen_nodes_set and req_id not in active_requests_in_routes:
                    active_requests_in_routes.append(req_id)
                    
        num_to_remove = min(num_to_remove, len(active_requests_in_routes))
        if num_to_remove <= 0:
            return vehicles, []

        chosen_ids = random.sample(active_requests_in_routes, num_to_remove)
        
        for vehicle in vehicles.values():
            vehicle.route = [r for r in vehicle.route if r not in chosen_ids]
            
        # Trả về các đối tượng Request giả lập từ id (cần map với request object nếu cần, 
        # ở đây trả về id hoặc đối tượng tùy thuộc vào thiết kế bộ nhớ - quy ước tạm thời)
        return vehicles, chosen_ids

    def greedy_repair(
        self, 
        vehicles: Dict[int, Vehicle], 
        removed_requests: List[Request], 
        frozen_commitments: Dict[int, int]
    ) -> Dict[int, Vehicle]:
        """
        Chèn lại các yêu cầu bị loại bằng phương pháp tham lam, 
        tuân thủ nghiêm ngặt frozen_commitments (H1).
        """
        for req in removed_requests:
            best_vid = None
            best_idx = -1
            min_cost = float('inf')
            
            for vid, vehicle in vehicles.items():
                if vehicle.current_load + getattr(req, 'demand', 1.0) <= self.capacity_constraint:
                    frozen_node = frozen_commitments.get(vid)
                    min_allowed_idx = 0
                    if frozen_node is not None and frozen_node in vehicle.route_nodes:
                        min_allowed_idx = vehicle.route_nodes.index(frozen_node) + 1
                        
                    for idx in range(min_allowed_idx, len(vehicle.route) + 1):
                        cost = getattr(req, 'e_pickup', 0.0) * 0.1 + idx * 0.5
                        if cost < min_cost:
                            min_cost = cost
                            best_vid = vid
                            best_idx = idx
                        
            if best_vid is not None and best_idx != -1:
                req_id = req.req_id if hasattr(req, 'req_id') else req
                demand = req.demand if hasattr(req, 'demand') else 1.0
                vehicles[best_vid].route.insert(best_idx, req_id)
                vehicles[best_vid].current_load += demand
                
        return vehicles