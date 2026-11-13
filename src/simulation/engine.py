from typing import List, Dict, Any, Optional
from src.simulation.entities import Event, EventType, Vehicle, Request
from src.simulation.des_engine import DESEngine

class SimulationEngine:
    def __init__(self, time_horizon: float, reoptimization_interval: float = 10.0):
        self.time_horizon = time_horizon
        self.reoptimization_interval = reoptimization_interval
        self.des_engine = DESEngine(time_horizon, reoptimization_interval)

    def setup_scenario(
        self,
        requests: List[Request],
        vehicles: List[Vehicle],
        depot_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Thiết lập kịch bản ban đầu cho mô phỏng:
        - Đưa danh sách phương tiện vào hệ thống.
        - Phân loại đơn hàng: Đơn tĩnh đưa thẳng vào pending,
          đơn động lên lịch sự kiện E1_NEW_REQUEST tại mốc thời gian tau_r.
        - Truyền depot_info và đăng ký requests vào DES engine.
        """
        # Pass depot info to DES engine
        if depot_info is not None:
            self.des_engine.set_depot_info(depot_info)

        # Set vehicle start coordinates from depot
        for vehicle in vehicles:
            if depot_info is not None:
                if vehicle.current_x is None:
                    vehicle.current_x = depot_info.get('x', 0.0)
                if vehicle.current_y is None:
                    vehicle.current_y = depot_info.get('y', 0.0)
            self.des_engine.add_vehicle(vehicle)

        for req in requests:
            # Register every request for ID-based lookup
            self.des_engine.register_request(req)

            if req.tau_r <= 0.0:
                self.des_engine.known_requests.append(req)
                self.des_engine.pending_requests.append(req)
            else:
                event_data = {'request': req}
                event = Event(time=req.tau_r, event_type=EventType.E1_NEW_REQUEST, data=event_data)
                self.des_engine.schedule_event(event)

    def run(self, solver, freeze_enabled: bool = True) -> Dict[str, Any]:
        """
        Kích hoạt vòng lặp mô phỏng, truyền cờ freeze_enabled vào DES Engine để kiểm soát H1.
        """
        self.des_engine.run(solver, freeze_enabled=freeze_enabled)

        total_requests = len(self.des_engine.known_requests)
        pending_count = len(self.des_engine.pending_requests)

        # Count actually delivered requests
        serviced_count = sum(
            1 for req in self.des_engine.requests_by_id.values()
            if req.is_delivered
        )

        return {
            "total_requests": total_requests,
            "serviced_count": serviced_count,
            "pending_count": pending_count,
            "vehicles": self.des_engine.vehicles
        }
