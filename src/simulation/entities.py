from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

# ==========================================
# 1. ĐỊNH NGHĨA SỰ KIỆN MÔ PHỎNG (DES)
# ==========================================
class EventType(Enum):
    E1_NEW_REQUEST = 1       # Đơn hàng động xuất hiện
    E2_VEHICLE_DEPARTS = 2   # Xe bắt đầu rời khỏi một nút
    E3_VEHICLE_ARRIVES = 3   # Xe đến một nút (bắt đầu phục vụ)
    E4_REOPTIMIZE = 4        # Chu kỳ kích hoạt thuật toán ALNS-D

@dataclass(order=True)
class Event:
    time: float
    event_type: EventType = field(compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)

# ==========================================
# 2. ĐỊNH NGHĨA ĐƠN HÀNG (REQUEST)
# ==========================================
@dataclass
class Request:
    req_id: int
    pickup_node: int
    delivery_node: int
    demand: float
    service_time: float
    e_pickup: float
    l_pickup: float
    e_delivery: float
    l_delivery: float
    tau_r: float = 0.0         # Thời điểm xuất hiện (theo Công thức 1.3)
    is_dynamic: bool = False   # True nếu là đơn hàng động

# ==========================================
# 3. ĐỊNH NGHĨA PHƯƠNG TIỆN (VEHICLE)
# ==========================================
class Vehicle:
    def __init__(self, vehicle_id: int, capacity: float, start_node: int):
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.current_load = 0.0
        self.current_node = start_node
        self.destination_node: Optional[int] = None # Nút tiếp theo đang hướng tới
        self.route: List[int] = []                  # Lộ trình dự kiến (chứa các Request ID hoặc Node ID)
        self.is_moving: bool = False

    def is_idle(self) -> bool:
        return not self.is_moving and len(self.route) == 0
