import heapq
import math
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

        # Request lookup and depot info
        self.requests_by_id: Dict[int, Request] = {}
        self.depot_info: Optional[Dict[str, Any]] = None

        # Tracking decision time
        self.decision_times: List[float] = []

        # Kích hoạt chu kỳ E4 đầu tiên
        self._schedule_next_reoptimization(0.0)

    def set_depot_info(self, depot: Dict[str, Any]) -> None:
        """Store depot coordinate information."""
        self.depot_info = depot

    def register_request(self, req: Request) -> None:
        """Register a request for ID-based lookup."""
        self.requests_by_id[req.req_id] = req

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
            elif current_event.event_type == EventType.E3_VEHICLE_ARRIVES:
                self._handle_vehicle_arrival(current_event.data)
            elif current_event.event_type == EventType.E4_REOPTIMIZE:
                self._handle_reoptimization(solver, freeze_enabled)
            # E2 departure is handled inline by start_movement — no separate handler

        print(f"🛑 Kết thúc mô phỏng tại T = {self.current_time:.2f}")

    # ------------------------------------------------------------------
    # Helper: compute Euclidean distance
    # ------------------------------------------------------------------
    def _euclidean(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # ------------------------------------------------------------------
    # Helper: get coordinates of a node (pickup/delivery/depot)
    # ------------------------------------------------------------------
    def _node_coords(self, node_id: int) -> tuple:
        """Return (x, y) for a node by searching requests and depot."""
        for req in self.requests_by_id.values():
            if req.pickup_node == node_id:
                return (req.pickup_x, req.pickup_y)
            if req.delivery_node == node_id:
                return (req.delivery_x, req.delivery_y)
        # Fallback to depot
        if self.depot_info is not None:
            return (self.depot_info.get('x', 0.0), self.depot_info.get('y', 0.0))
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Helper: dispatch a vehicle to its next stop
    # ------------------------------------------------------------------
    def _dispatch_vehicle(self, vehicle: Vehicle) -> None:
        """Pick the first request in vehicle.route and send vehicle to the next stop."""
        if not vehicle.route:
            return
        if vehicle.is_moving:
            return

        req_id = vehicle.route[0]
        req = self.requests_by_id.get(req_id)
        if req is None:
            return

        # Determine next stop
        if not req.is_picked_up:
            stop_type = "pickup"
            dest_node = req.pickup_node
            dest_x = req.pickup_x if req.pickup_x is not None else 0.0
            dest_y = req.pickup_y if req.pickup_y is not None else 0.0
        else:
            stop_type = "delivery"
            dest_node = req.delivery_node
            dest_x = req.delivery_x if req.delivery_x is not None else 0.0
            dest_y = req.delivery_y if req.delivery_y is not None else 0.0

        # Current position
        cur_x = vehicle.current_x if vehicle.current_x is not None else 0.0
        cur_y = vehicle.current_y if vehicle.current_y is not None else 0.0

        distance = self._euclidean(cur_x, cur_y, dest_x, dest_y)
        speed = 1.0
        travel_time = distance / speed if speed > 0 else 0.0
        departure_time = self.current_time
        arrival_time = departure_time + travel_time

        # Set commitment
        vehicle.set_commitment(req_id, stop_type, dest_node)

        # Build route_nodes if not already reflecting this stop
        if dest_node not in vehicle.route_nodes:
            vehicle.route_nodes.append(dest_node)

        # Start movement
        vehicle.start_movement(
            destination_node=dest_node,
            destination_x=dest_x,
            destination_y=dest_y,
            departure_time=departure_time,
            arrival_time=arrival_time,
            distance=distance,
            request_id=req_id,
            stop_type=stop_type,
        )

        # Schedule E3 arrival
        self.schedule_event(Event(
            time=arrival_time,
            event_type=EventType.E3_VEHICLE_ARRIVES,
            data={
                'vehicle_id': vehicle.vehicle_id,
                'node_id': dest_node,
                'request_id': req_id,
                'stop_type': stop_type,
            }
        ))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_reoptimization(self, solver, freeze_enabled: bool = True):
        """E4: Kích hoạt thuật toán giải quyết (Solver) với trạng thái H1 tùy biến"""
        if not solver or not self.pending_requests:
            self._schedule_next_reoptimization(self.current_time)
            return

        # Nếu FREEZE_OFF -> cam kết rỗng {}; Nếu FREEZE_ON -> lấy cam kết thực tế
        frozen_commitments = self._freeze_commitments() if freeze_enabled else {}

        import time
        t_start = time.perf_counter()
        unserved = solver.solve(self.pending_requests, self.vehicles, frozen_commitments)
        t_elapsed = time.perf_counter() - t_start
        self.decision_times.append(t_elapsed)

        self.pending_requests = unserved

        # Dispatch idle vehicles that now have routes
        for vid, vehicle in self.vehicles.items():
            if vehicle.route and not vehicle.is_moving:
                self._dispatch_vehicle(vehicle)

        self._schedule_next_reoptimization(self.current_time)

    def _handle_new_request(self, data: Dict[str, Any]):
        """E1: Đơn hàng động xuất hiện"""
        req = data['request']
        self.known_requests.append(req)
        self.pending_requests.append(req)
        # Register for lookup
        self.register_request(req)

    def _handle_vehicle_arrival(self, data: Dict[str, Any]):
        """E3: Xe đến một nút — perform pickup or delivery, then dispatch next."""
        vid = data['vehicle_id']
        node_id = data['node_id']
        req_id = data.get('request_id')
        stop_type = data.get('stop_type')

        if vid not in self.vehicles:
            return

        vehicle = self.vehicles[vid]

        # Complete movement (updates position, clears destination, sets is_moving=False)
        vehicle.complete_movement(self.current_time)

        # Process pickup or delivery
        if req_id is not None and req_id in self.requests_by_id:
            req = self.requests_by_id[req_id]

            if stop_type == "pickup":
                # Solver already reserved the demand in current_load when
                # inserting the request, so we back it out before calling
                # pickup() which adds it again.  This keeps the running
                # load accurate throughout the simulation.
                vehicle.current_load -= req.demand
                if abs(vehicle.current_load) < 1e-9:
                    vehicle.current_load = 0.0
                vehicle.pickup(req, self.current_time)
                # After pickup, need to go to delivery — keep req in route
                # Clear commitment for this stop, will set new one when dispatching
                vehicle.clear_commitment()
                # Remove pickup node from route_nodes
                if node_id in vehicle.route_nodes:
                    vehicle.route_nodes.remove(node_id)
                # Dispatch to delivery
                self._dispatch_vehicle(vehicle)

            elif stop_type == "delivery":
                vehicle.deliver(req, self.current_time)
                # Remove request from route
                if req_id in vehicle.route:
                    vehicle.route.remove(req_id)
                # Remove delivery node from route_nodes
                if node_id in vehicle.route_nodes:
                    vehicle.route_nodes.remove(node_id)
                # Clear commitment
                vehicle.clear_commitment()
                # Clear current request
                vehicle.current_request_id = None
                vehicle.current_stop_type = None
                # Remove from pending if present
                self.pending_requests = [
                    r for r in self.pending_requests if r.req_id != req_id
                ]
                # Dispatch to next request if any remain
                if vehicle.route:
                    self._dispatch_vehicle(vehicle)

    def _freeze_commitments(self) -> Dict[int, int]:
        """
        Return {vehicle_id: committed_node_id} for vehicles with active commitments.
        Fallback: if vehicle is moving with a destination, use that.
        """
        commitments = {}
        for vid, vehicle in self.vehicles.items():
            if vehicle.commitment_active and vehicle.committed_stop is not None:
                # committed_stop is (node_id, stop_type)
                commitments[vid] = vehicle.committed_stop[0]
            elif vehicle.is_moving and vehicle.destination_node is not None:
                commitments[vid] = vehicle.destination_node
        return commitments
