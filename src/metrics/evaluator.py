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
        # 1. Tính tổng quãng đường di chuyển (D)
        total_distance = 0.0
        for vehicle in vehicles.values():
            # Sử dụng hệ số quy đổi hoặc chuẩn bị tích hợp khoảng cách thực tế từ ma trận
            total_distance += len(vehicle.route) * 12.5
            
        # 2. Tính tỷ lệ phục vụ và từ chối
        n_total = len(total_known_requests)
        service_rate = (served_requests_count / n_total) if n_total > 0 else 0.0
        rejection_rate = 1.0 - service_rate
        
        return {
            "total_distance_D": round(total_distance, 2),
            "service_rate_SR": round(service_rate, 4),
            "rejection_rate_RR": round(rejection_rate, 4),
            "active_vehicles": sum(1 for v in vehicles.values() if len(v.route) > 0)
        }