
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EventType(Enum):
    """Các loại sự kiện trong mô phỏng sự kiện rời rạc."""
    E1_NEW_REQUEST = 1
    E2_VEHICLE_DEPARTS = 2
    E3_VEHICLE_ARRIVES = 3
    E4_REOPTIMIZE = 4


@dataclass(order=True)
class Event:
    """Sự kiện được sắp xếp theo thời điểm xảy ra."""
    time: float
    event_type: EventType = field(compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass
class Request:
    """Một yêu cầu giao nhận gồm một điểm lấy và một điểm giao."""

    req_id: int
    pickup_node: int
    delivery_node: int
    demand: float
    service_time: float
    e_pickup: float
    l_pickup: float
    e_delivery: float
    l_delivery: float

    # Thời điểm yêu cầu xuất hiện và loại yêu cầu
    tau_r: float = 0.0
    is_dynamic: bool = False

    # Tọa độ pickup/delivery lấy từ dữ liệu Li & Lim
    pickup_x: Optional[float] = None
    pickup_y: Optional[float] = None
    delivery_x: Optional[float] = None
    delivery_y: Optional[float] = None

    # Trạng thái phục vụ
    is_picked_up: bool = False
    is_delivered: bool = False
    assigned_vehicle_id: Optional[int] = None

    # Thời điểm thực tế
    pickup_time: Optional[float] = None
    delivery_time: Optional[float] = None

    @property
    def is_served(self) -> bool:
        """Một request chỉ được xem là phục vụ khi đã giao hàng."""
        return self.is_delivered

    @property
    def pickup_coordinates(self) -> Optional[Tuple[float, float]]:
        if self.pickup_x is None or self.pickup_y is None:
            return None
        return self.pickup_x, self.pickup_y

    @property
    def delivery_coordinates(self) -> Optional[Tuple[float, float]]:
        if self.delivery_x is None or self.delivery_y is None:
            return None
        return self.delivery_x, self.delivery_y


class Vehicle:
    """Phương tiện vận chuyển trong mô phỏng DPDP."""

    def __init__(
        self,
        vehicle_id: int,
        capacity: float,
        start_node: int,
        start_x: Optional[float] = None,
        start_y: Optional[float] = None,
    ):
        self.vehicle_id = vehicle_id
        self.capacity = float(capacity)

        # Trạng thái tải trọng và vị trí
        self.current_load = 0.0
        self.current_node = start_node
        self.current_x = start_x
        self.current_y = start_y

        # Điểm đến hiện tại
        self.destination_node: Optional[int] = None
        self.destination_x: Optional[float] = None
        self.destination_y: Optional[float] = None

        # Route tiếp tục lưu request ID để tương thích Greedy/Regret-2.
        # route_nodes lưu dữ liệu node thực tế tương ứng với từng request trong route
        # để cho phép H1 khóa các điểm đang được cam kết.
        self.route: List[int] = []
        self.route_nodes: List[int] = []

        # Trạng thái di chuyển
        self.is_moving = False
        self.departure_time: Optional[float] = None
        self.arrival_time: Optional[float] = None
        self.travel_distance = 0.0
        self.total_distance = 0.0
        self.total_travel_time = 0.0

        # Request và loại điểm dừng đang được phục vụ
        self.current_request_id: Optional[int] = None
        self.current_stop_type: Optional[str] = None

        # Thông tin cam kết phục vụ cho H1
        self.commitment_active = False
        self.committed_request_id: Optional[int] = None
        self.committed_stop: Optional[Tuple[int, str]] = None

        # Thống kê
        self.completed_request_ids: List[int] = []

    def is_idle(self) -> bool:
        """Xe rảnh khi không di chuyển và không còn request trong route."""
        return (
            not self.is_moving
            and self.current_request_id is None
            and len(self.route) == 0
        )

    def has_destination(self) -> bool:
        return self.destination_node is not None

    def can_change_destination(self) -> bool:
        """Không được đổi điểm đến khi đang thực hiện cam kết."""
        return not self.commitment_active

    def start_movement(
        self,
        destination_node: int,
        destination_x: float,
        destination_y: float,
        departure_time: float,
        arrival_time: float,
        distance: float,
        request_id: Optional[int] = None,
        stop_type: Optional[str] = None,
    ) -> None:
        """Ghi nhận xe bắt đầu di chuyển đến một điểm dừng."""
        if self.is_moving:
            raise RuntimeError(
                f"Vehicle {self.vehicle_id} is already moving."
            )

        if arrival_time < departure_time:
            raise ValueError("arrival_time must not be earlier than departure_time")

        self.destination_node = destination_node
        self.destination_x = float(destination_x)
        self.destination_y = float(destination_y)

        self.departure_time = float(departure_time)
        self.arrival_time = float(arrival_time)
        self.travel_distance = float(distance)

        self.current_request_id = request_id
        self.current_stop_type = stop_type
        self.is_moving = True

        self.total_distance += float(distance)
        self.total_travel_time += float(arrival_time - departure_time)

    def complete_movement(self, arrival_time: float) -> None:
        """Ghi nhận xe đến điểm đích."""
        if not self.is_moving:
            raise RuntimeError(
                f"Vehicle {self.vehicle_id} is not moving."
            )

        if self.destination_node is None:
            raise RuntimeError("Vehicle has no destination node.")

        if self.arrival_time is not None and arrival_time < self.arrival_time:
            raise ValueError("Vehicle cannot arrive before scheduled arrival.")

        self.current_node = self.destination_node
        self.current_x = self.destination_x
        self.current_y = self.destination_y

        self.destination_node = None
        self.destination_x = None
        self.destination_y = None

        self.is_moving = False
        self.departure_time = None
        self.arrival_time = None
        self.travel_distance = 0.0

    def set_commitment(
        self,
        request_id: int,
        stop_type: str,
        node_id: int,
    ) -> None:
        """Đánh dấu điểm dừng mà xe đã cam kết thực hiện."""
        if stop_type not in ("pickup", "delivery"):
            raise ValueError("stop_type must be 'pickup' or 'delivery'")

        self.commitment_active = True
        self.committed_request_id = request_id
        self.committed_stop = (node_id, stop_type)

    def clear_commitment(self) -> None:
        """Xóa cam kết sau khi xe hoàn thành điểm dừng."""
        self.commitment_active = False
        self.committed_request_id = None
        self.committed_stop = None

    def route_node_sequence(self) -> List[int]:
        """Trả về chuỗi node tương ứng với `route`, dùng cho ràng buộc H1."""
        if self.route_nodes:
            return list(self.route_nodes)
        return []

    def pickup(self, request: Request, current_time: float) -> None:
        """Ghi nhận lấy hàng và cập nhật tải trọng."""
        if request.is_picked_up:
            raise ValueError(f"Request {request.req_id} was already picked up.")

        if request.is_delivered:
            raise ValueError(f"Request {request.req_id} was already delivered.")

        if self.current_load + request.demand > self.capacity:
            raise ValueError(
                f"Vehicle {self.vehicle_id} capacity exceeded."
            )

        request.is_picked_up = True
        request.pickup_time = float(current_time)
        request.assigned_vehicle_id = self.vehicle_id
        self.current_load += request.demand

    def deliver(self, request: Request, current_time: float) -> None:
        """Ghi nhận giao hàng và giảm tải trọng."""
        if not request.is_picked_up:
            raise ValueError(
                f"Request {request.req_id} must be picked up before delivery."
            )

        if request.is_delivered:
            raise ValueError(f"Request {request.req_id} was already delivered.")

        request.is_delivered = True
        request.delivery_time = float(current_time)
        self.current_load -= request.demand

        # Tránh sai số số thực làm tải trọng âm rất nhỏ
        if abs(self.current_load) < 1e-9:
            self.current_load = 0.0

        self.completed_request_ids.append(request.req_id)
