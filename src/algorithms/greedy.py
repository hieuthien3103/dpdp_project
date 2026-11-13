from typing import List, Dict, Tuple, Optional
from src.simulation.entities import Request, Vehicle

class GreedyInsertion:
    def __init__(self, capacity_constraint: float):
        self.capacity_constraint = capacity_constraint

    def solve(self, pending_requests: List[Request], vehicles: Dict[int, Vehicle], frozen_commitments: Dict[int, int]) -> List[Request]:
        """
        Thực thi thuật toán Greedy Insertion (Baseline chính):
        Lặp lại việc tìm và chèn đơn hàng có chi phí tăng thêm nhỏ nhất
        vào các xe khả dụng, tuân thủ nghiêm ngặt các nút đã đóng băng (frozen_commitments).
        """
        unassigned = pending_requests.copy()

        while unassigned:
            best_req: Optional[Request] = None
            best_vehicle_id: Optional[int] = None
            best_cost_increase = float('inf')
            best_insertion_index = -1

            for req in unassigned:
                for vid, vehicle in vehicles.items():
                    frozen_node = frozen_commitments.get(vid)
                    cost, insert_idx = self._evaluate_insertion(req, vehicle, frozen_node)

                    if cost < best_cost_increase:
                        best_cost_increase = cost
                        best_req = req
                        best_vehicle_id = vid
                        best_insertion_index = insert_idx

            if best_req is not None and best_vehicle_id is not None:
                self._insert_request(vehicles[best_vehicle_id], best_req, best_insertion_index)
                unassigned.remove(best_req)
            else:
                break

        return unassigned

    def _evaluate_insertion(self, req: Request, vehicle: Vehicle, frozen_node: Optional[int]) -> Tuple[float, int]:
        """
        Tính toán chi phí tăng thêm nếu chèn req vào vehicle,
        có kiểm tra ràng buộc tải trọng và tuân thủ frozen_node (H1).
        `vehicle.route` lưu request ID, nhưng `frozen_node` theo node nên cần
        dựa vào `vehicle.route_nodes` để xác định vị trí cam kết.
        """
        if vehicle.current_load + req.demand > self.capacity_constraint:
            return float('inf'), -1

        route_nodes = vehicle.route_node_sequence()
        min_allowed_idx = 0
        if frozen_node is not None and frozen_node in route_nodes:
            frozen_idx = route_nodes.index(frozen_node)
            min_allowed_idx = frozen_idx + 1

        best_cost = float('inf')
        best_idx = -1

        for idx in range(min_allowed_idx, len(route_nodes) + 1):
            mock_cost = req.e_pickup * 0.1 + idx * 1.0
            if mock_cost < best_cost:
                best_cost = mock_cost
                best_idx = idx

        return best_cost if best_idx != -1 else float('inf'), best_idx

    def _insert_request(self, vehicle: Vehicle, req: Request, index: int):
        """Cập nhật trạng thái xe sau khi chèn đơn hàng thành công"""
        vehicle.route.insert(index, req.req_id)
        vehicle.route_nodes.insert(index, req.pickup_node)
        vehicle.route_nodes.insert(index + 1, req.delivery_node)
        vehicle.current_load += req.demand