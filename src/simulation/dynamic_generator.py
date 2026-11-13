
import numpy as np
from typing import Dict, List, Tuple

from src.simulation.entities import Request


def parse_and_dynamize_li_lim(
    filepath: str,
    rho: float = 0.5,
    lead_time: float = 15.0,
    seed: int = 42,
) -> Tuple[List[Request], Dict, float]:
    """
    Đọc dữ liệu Li & Lim, tạo Request pickup-delivery
    và sinh thời điểm xuất hiện cho các yêu cầu động.

    Tọa độ được lưu trực tiếp trong Request để phục vụ
    tính khoảng cách và thời gian di chuyển trong DES.
    """

    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho must be between 0 and 1.")

    if lead_time < 0:
        raise ValueError("lead_time must be non-negative.")

    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    if not lines:
        raise ValueError("Li & Lim instance file is empty.")

    # --------------------------------------------------
    # 1. Đọc thông tin đội xe
    # --------------------------------------------------
    vehicle_info = lines[0].strip().split()

    if len(vehicle_info) < 2:
        raise ValueError("Invalid Li & Lim header.")

    fleet_size = int(vehicle_info[0])
    capacity = float(vehicle_info[1])

    if fleet_size <= 0 or capacity <= 0:
        raise ValueError("Invalid fleet size or vehicle capacity.")

    # --------------------------------------------------
    # 2. Đọc danh sách node
    # --------------------------------------------------
    nodes = {}

    for line_number, line in enumerate(lines[1:], start=2):
        parts = line.strip().split()

        if not parts:
            continue

        if len(parts) < 9:
            raise ValueError(
                f"Invalid node data at line {line_number}: {line.strip()}"
            )

        node_id = int(parts[0])

        if node_id in nodes:
            raise ValueError(f"Duplicate node ID: {node_id}")

        nodes[node_id] = {
            "x": float(parts[1]),
            "y": float(parts[2]),
            "demand": float(parts[3]),
            "ready_time": float(parts[4]),
            "due_date": float(parts[5]),
            "service_time": float(parts[6]),
            "pickup_idx": int(parts[7]),
            "delivery_idx": int(parts[8]),
        }

    if 0 not in nodes:
        raise ValueError("Depot node 0 is missing.")

    depot = nodes[0]

    # --------------------------------------------------
    # 3. Ghép cặp pickup-delivery
    # --------------------------------------------------
    requests: List[Request] = []

    for node_id, pickup_data in nodes.items():

        if node_id == 0:
            continue

        delivery_id = pickup_data["delivery_idx"]

        if delivery_id == 0:
            continue

        if delivery_id not in nodes:
            raise ValueError(
                f"Delivery node {delivery_id} of request "
                f"{node_id} does not exist."
            )

        delivery_data = nodes[delivery_id]

        distance_from_depot = float(
            np.hypot(
                pickup_data["x"] - depot["x"],
                pickup_data["y"] - depot["y"],
            )
        )

        request = Request(
            req_id=node_id,
            pickup_node=node_id,
            delivery_node=delivery_id,
            demand=abs(pickup_data["demand"]),
            service_time=pickup_data["service_time"],
            e_pickup=pickup_data["ready_time"],
            l_pickup=pickup_data["due_date"],
            e_delivery=delivery_data["ready_time"],
            l_delivery=delivery_data["due_date"],

            # Tọa độ pickup
            pickup_x=pickup_data["x"],
            pickup_y=pickup_data["y"],

            # Tọa độ delivery
            delivery_x=delivery_data["x"],
            delivery_y=delivery_data["y"],
        )

        request._t_0r = distance_from_depot
        requests.append(request)

    if not requests:
        raise ValueError("No pickup-delivery requests found.")

    # --------------------------------------------------
    # 4. Sinh yêu cầu động
    # --------------------------------------------------
    rng = np.random.default_rng(seed)

    number_of_requests = len(requests)
    number_of_dynamic = int(np.ceil(rho * number_of_requests))

    dynamic_indices = set(
        rng.choice(
            number_of_requests,
            size=number_of_dynamic,
            replace=False,
        ).tolist()
    )

    for index, request in enumerate(requests):

        if index in dynamic_indices:
            request.is_dynamic = True

            upper_bound = max(
                0.0,
                request.l_pickup - request._t_0r - lead_time,
            )

            request.tau_r = round(
                float(rng.uniform(0.0, upper_bound)),
                2,
            )

        else:
            request.is_dynamic = False
            request.tau_r = 0.0

    # Xóa biến tạm
    for request in requests:
        delattr(request, "_t_0r")

    depot_info = {
        "x": depot["x"],
        "y": depot["y"],
        "due_date": depot["due_date"],
    }

    return requests, depot_info, capacity
