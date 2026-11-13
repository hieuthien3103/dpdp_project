import heapq
from typing import List, Dict, Any, Optional
from src.simulation.entities import Event, EventType, Vehicle, Request

class DESEngine:
    def __init__(self, time_horizon: float, reoptimization_interval: float = 10.0):
        self.current_time = 0.0
        self.time_horizon = time_horizon
        self.reoptimization_interval = reoptimization_interval
        
        # Hàng đợi ưu tiên quản lý sự kiện theo thời gian
        self.event_queue: List[Event] = []
        
        # Trạng thái hệ thống
        self.vehicles: Dict[int, Vehicle] = {}
        self.known_requests: List[Request] = []
        self.pending_requests: List[Request] = []
        
        # Kích hoạt chu kỳ E4 đầu tiên
        self._schedule_next_reoptimization(0.0)

    def add_vehicle(self, vehicle: Vehicle):
        self.vehicles[vehicle.vehicle_id] = vehicle

    def schedule_event(self, event: Event):
        if event.time <= self.time_horizon:
            heapq.heappush(self.event_queue, event)

    def _schedule_next_reoptimization(self, from_time: float):
        next_time = from_time + self.reoptimization_interval
        if next_time <= self.time_horizon:
            self.schedule_event(Event(next_time, EventType.E4_REOPTIMIZE))

    def run(self, solver=None, freeze_enabled: bool = True):
        """Vòng lặp thời gian cốt lõi của Mô phỏng sự kiện rời rạc"""
        print(f"🚀 Bắt đầu mô phỏng DPDP (Horizon = {self.time_horizon}s)...")
        while self.event_queue:
            current_event = heapq.heappop(self.event_queue)
            self.current_time = current_event.time
            
            if current_event.event_type == EventType.E1_NEW_REQUEST:
                self._handle_new_request(current_event.data)
            elif current_event.event_type == EventType.E2_VEHICLE_DEPARTS:
                self._handle_vehicle_departure(current_event.data)
            elif current_event.event_type == EventType.E3_VEHICLE_ARRIVES:
                self._handle_vehicle_arrival(current_event.data)
            elif current_event.event_type == EventType.E4_REOPTIMIZE:
                self._handle_reoptimization(solver, freeze_enabled)

        print(f"🛑 Kết thúc mô phỏng tại T = {self.current_time:.2f}")

    def _handle_reoptimization(self, solver, freeze_enabled: bool = True):
        """E4: Kích hoạt thuật toán giải quyết (Solver) với trạng thái H1 tùy biến"""
        if not solver or not self.pending_requests:
            self._schedule_next_reoptimization(self.current_time)
            return

        # Nếu FREEZE_OFF -> cam kết rỗng {}; Nếu FREEZE_ON -> lấy cam kết thực tế từ xe đang di chuyển
        frozen_commitments = self._freeze_commitments() if freeze_enabled else {}
        
        unserved = solver.solve(self.pending_requests, self.vehicles, frozen_commitments)
        self.pending_requests = unserved
            
        self._schedule_next_reoptimization(self.current_time)

    def _handle_new_request(self, data: Dict[str, Any]):
        """E1: Đơn hàng động xuất hiện"""
        req = data['request']
        self.known_requests.append(req)
        self.pending_requests.append(req)
        # Hệ thống không giải lại ngay, chờ gom đơn đến kỳ E4 tiếp theo

    def _handle_vehicle_departure(self, data: Dict[str, Any]):
        """E2: Xe bắt đầu rời khỏi một nút"""
        vid = data['vehicle_id']
        if vid in self.vehicles:
            self.vehicles[vid].is_moving = True

    def _handle_vehicle_arrival(self, data: Dict[str, Any]):
        """E3: Xe đến một nút (bắt đầu phục vụ)"""
        vid = data['vehicle_id']
        node_id = data['node_id']
        if vid in self.vehicles:
            self.vehicles[vid].is_moving = False
            self.vehicles[vid].current_node = node_id

    def _freeze_commitments(self) -> Dict[int, int]:
        """
        Khóa các node không được phép thay đổi.
        Ở đây xét nút đầu tiên của route hiện tại như một cam kết thực tế.
        Điều này đảm bảo H1 có thể được kích hoạt ngay cả khi mô phỏng chưa
        triển khai đầy đủ chuyển động của xe theo thời gian.
        """
        commitments = {}
        for vid, vehicle in self.vehicles.items():
            route_nodes = vehicle.route_node_sequence()
            if route_nodes:
                commitments[vid] = route_nodes[0]
            elif vehicle.is_moving and vehicle.destination_node is not None:
                commitments[vid] = vehicle.destination_node
        return commitments