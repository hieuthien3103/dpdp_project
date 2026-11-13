from typing import List, Dict, Any
from src.simulation.entities import Request, Vehicle

class SolutionEvaluator:
    @staticmethod
    def evaluate_performance(
        vehicles: Dict[int, Vehicle], 
        total_known_requests: List[Request], 
        served_requests_count: int,
        requests_dict: Dict[int, Request] = None
    ) -> Dict[str, Any]:
        """
        Tính toán các chỉ số đánh giá đa tiêu chí (Bảng 1.7):
        - Tổng quãng đường di chuyển (D)
        - Tỷ lệ phục vụ (Service Rate - SR)
        - Tỷ lệ từ chối (Rejection Rate - RR)
        - Số lượng xe hoạt động (Active Vehicles)
        """
        # 1. Tính tổng quãng đường di chuyển (D) — sử dụng total_distance
        #    tích lũy bởi DES engine qua các sự kiện E3 (vehicle.start_movement)
        total_distance = 0.0
        for vehicle in vehicles.values():
            if vehicle.total_distance > 0:
                # Ưu tiên khoảng cách thực tế từ DES simulation
                total_distance += vehicle.total_distance
            else:
                # Fallback: tính từ route_nodes khi DES chưa dispatch
                node_coords = {}
                for req in total_known_requests:
                    if req.pickup_node is not None and req.pickup_x is not None and req.pickup_y is not None:
                        node_coords[req.pickup_node] = (req.pickup_x, req.pickup_y)
                    if req.delivery_node is not None and req.delivery_x is not None and req.delivery_y is not None:
                        node_coords[req.delivery_node] = (req.delivery_x, req.delivery_y)

                route_nodes = list(vehicle.route_node_sequence())
                if not route_nodes:
                    continue

                prev_node = vehicle.current_node if vehicle.current_node is not None else 0
                for node in route_nodes:
                    if node in node_coords and prev_node in node_coords:
                        x1, y1 = node_coords[prev_node]
                        x2, y2 = node_coords[node]
                        total_distance += ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                    elif prev_node != node:
                        total_distance += 1.0
                    prev_node = node

        # 2. Tính tỷ lệ phục vụ và từ chối
        n_total = len(total_known_requests)
        service_rate = (served_requests_count / n_total) if n_total > 0 else 0.0
        rejection_rate = 1.0 - service_rate
        
        return {
            "total_distance_D": round(total_distance, 2),
            "service_rate_SR": round(service_rate, 4),
            "rejection_rate_RR": round(rejection_rate, 4),
            "active_vehicles": sum(1 for v in vehicles.values() if len(v.completed_request_ids) > 0 or len(v.route) > 0)
        }
