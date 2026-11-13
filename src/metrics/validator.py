from typing import List, Dict, Tuple
from src.simulation.entities import Request, Vehicle

class SolutionValidator:
    def __init__(self, capacity_constraint: float):
        self.capacity_constraint = capacity_constraint

    def validate(self, vehicles: Dict[int, Vehicle], requests_dict: Dict[int, Request]) -> Tuple[bool, str]:
        """
        Kiểm tra tính khả thi của toàn bộ hệ thống lộ trình đội xe:
        - Ràng buộc tải trọng (Capacity constraint Q)
        - Tính hợp lệ của các yêu cầu trong lộ trình
        """
        for vid, vehicle in vehicles.items():
            current_load = 0.0
            
            for req_id in vehicle.route:
                if req_id not in requests_dict:
                    return False, f"Xe {vid} chứa request_id không hợp lệ hoặc chưa được đăng ký: {req_id}"
                req = requests_dict[req_id]
                
                # Kiểm tra tải trọng cộng dồn
                current_load += req.demand
                if current_load > self.capacity_constraint + 1e-5:
                    return False, f"Xe {vid} vi phạm tải trọng: Tải hiện tại {current_load} vượt mức cho phép {self.capacity_constraint}"
                    
        return True, "Lời giải hoàn toàn hợp lệ."