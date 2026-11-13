import math
import random
from typing import List, Dict, Tuple, Optional
from src.simulation.entities import Request, Vehicle


class ALNSOperators:
    def __init__(self, capacity_constraint: float, depot_xy: Tuple[float, float] = (0.0, 0.0)):
        self.capacity_constraint = capacity_constraint
        self.depot_xy = depot_xy
        self._node_coords: Dict[int, Tuple[float, float]] = {}

    @staticmethod
    def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    def set_node_coords(self, coords: Dict[int, Tuple[float, float]]) -> None:
        self._node_coords = coords

    def _get_coord(self, node_id: int) -> Tuple[float, float]:
        return self._node_coords.get(node_id, self.depot_xy)

    # ============================================================
    # REMOVAL OPERATORS (Phá hủy nghiệm)
    # ============================================================

    def random_removal(
        self,
        vehicles: Dict[int, Vehicle],
        num_to_remove: int,
        frozen_commitments: Dict[int, int],
        requests_dict: Dict[int, Request],
    ) -> Tuple[Dict[int, Vehicle], List[Request]]:
        """Loại bỏ ngẫu nhiên các đơn hàng khỏi đội xe, bảo vệ frozen_commitments."""
        removable_req_ids = []
        frozen_nodes_set = set(frozen_commitments.values())

        for vid, vehicle in vehicles.items():
            frozen_node = frozen_commitments.get(vid)
            for req_id in vehicle.route:
                if req_id in requests_dict:
                    req = requests_dict[req_id]
                    # Không loại bỏ nếu điểm pickup hoặc delivery của đơn này đang bị đóng băng
                    if req.pickup_node in frozen_nodes_set or req.delivery_node in frozen_nodes_set:
                        continue
                    if req_id not in removable_req_ids:
                        removable_req_ids.append(req_id)

        q = min(num_to_remove, len(removable_req_ids))
        if q <= 0:
            return vehicles, []

        chosen_ids = set(random.sample(removable_req_ids, q))
        removed_requests = [requests_dict[rid] for rid in chosen_ids if rid in requests_dict]

        for vehicle in vehicles.values():
            new_route = []
            new_route_nodes = []
            new_load = 0.0
            for rid in vehicle.route:
                if rid not in chosen_ids:
                    new_route.append(rid)
                    if rid in requests_dict:
                        req = requests_dict[rid]
                        new_route_nodes.extend([req.pickup_node, req.delivery_node])
                        new_load += req.demand
            vehicle.route = new_route
            vehicle.route_nodes = new_route_nodes
            vehicle.current_load = new_load

        return vehicles, removed_requests

    def worst_removal(
        self,
        vehicles: Dict[int, Vehicle],
        num_to_remove: int,
        frozen_commitments: Dict[int, int],
        requests_dict: Dict[int, Request],
    ) -> Tuple[Dict[int, Vehicle], List[Request]]:
        """Loại bỏ các đơn hàng gây độ tăng khoảng cách lớn nhất (Worst Cost Removal)."""
        removable_req_ids = []
        frozen_nodes_set = set(frozen_commitments.values())

        cost_contributions = []
        for vid, vehicle in vehicles.items():
            for req_id in vehicle.route:
                if req_id in requests_dict:
                    req = requests_dict[req_id]
                    if req.pickup_node in frozen_nodes_set or req.delivery_node in frozen_nodes_set:
                        continue
                    p_coord = self._get_coord(req.pickup_node)
                    d_coord = self._get_coord(req.delivery_node)
                    cost = self._euclidean(p_coord, d_coord)
                    cost_contributions.append((cost, req_id))

        cost_contributions.sort(key=lambda x: x[0], reverse=True)
        q = min(num_to_remove, len(cost_contributions))
        if q <= 0:
            return vehicles, []

        chosen_ids = set(rid for _, rid in cost_contributions[:q])
        removed_requests = [requests_dict[rid] for rid in chosen_ids if rid in requests_dict]

        for vehicle in vehicles.values():
            new_route = []
            new_route_nodes = []
            new_load = 0.0
            for rid in vehicle.route:
                if rid not in chosen_ids:
                    new_route.append(rid)
                    if rid in requests_dict:
                        req = requests_dict[rid]
                        new_route_nodes.extend([req.pickup_node, req.delivery_node])
                        new_load += req.demand
            vehicle.route = new_route
            vehicle.route_nodes = new_route_nodes
            vehicle.current_load = new_load

        return vehicles, removed_requests

    # ============================================================
    # REPAIR OPERATORS (Sửa chữa / Chèn lại nghiệm)
    # ============================================================

    def greedy_repair(
        self,
        vehicles: Dict[int, Vehicle],
        removed_requests: List[Request],
        frozen_commitments: Dict[int, int],
    ) -> Dict[int, Vehicle]:
        """Chèn lại các yêu cầu theo tiêu chuẩn chi phí tăng thêm nhỏ nhất (Greedy)."""
        unassigned = removed_requests.copy()

        while unassigned:
            best_req = None
            best_vid = None
            best_cost = float('inf')
            best_p = -1
            best_d = -1

            for req in unassigned:
                for vid, vehicle in vehicles.items():
                    if vehicle.current_load + req.demand > self.capacity_constraint:
                        continue

                    frozen_node = frozen_commitments.get(vid)
                    route_nodes = vehicle.route_node_sequence()
                    min_idx = 0
                    if frozen_node is not None and frozen_node in route_nodes:
                        min_idx = route_nodes.index(frozen_node) + 1

                    cost, p_pos, d_pos = self._best_insert_pos(req, vehicle, min_idx)
                    if cost < best_cost:
                        best_cost = cost
                        best_req = req
                        best_vid = vid
                        best_p = p_pos
                        best_d = d_pos

            if best_req is not None and best_vid is not None and best_p != -1:
                veh = vehicles[best_vid]
                veh.route_nodes.insert(best_p, best_req.pickup_node)
                veh.route_nodes.insert(best_d, best_req.delivery_node)
                veh.route.append(best_req.req_id)
                veh.current_load += best_req.demand
                unassigned.remove(best_req)
            else:
                break

        return vehicles

    def regret_repair(
        self,
        vehicles: Dict[int, Vehicle],
        removed_requests: List[Request],
        frozen_commitments: Dict[int, int],
    ) -> Dict[int, Vehicle]:
        """Chèn lại các yêu cầu theo giá trị hối tiếc Regret-2."""
        unassigned = removed_requests.copy()

        while unassigned:
            best_req = None
            best_vid = None
            best_p = -1
            best_d = -1
            max_regret = -1.0

            for req in unassigned:
                vehicle_costs = []
                for vid, vehicle in vehicles.items():
                    if vehicle.current_load + req.demand > self.capacity_constraint:
                        continue
                    frozen_node = frozen_commitments.get(vid)
                    route_nodes = vehicle.route_node_sequence()
                    min_idx = 0
                    if frozen_node is not None and frozen_node in route_nodes:
                        min_idx = route_nodes.index(frozen_node) + 1

                    cost, p_pos, d_pos = self._best_insert_pos(req, vehicle, min_idx)
                    if cost < float('inf') and p_pos != -1:
                        vehicle_costs.append((cost, vid, p_pos, d_pos))

                vehicle_costs.sort(key=lambda x: x[0])
                if not vehicle_costs:
                    continue
                elif len(vehicle_costs) == 1:
                    regret = float('inf')
                    b_cost, b_vid, b_p, b_d = vehicle_costs[0]
                else:
                    regret = vehicle_costs[1][0] - vehicle_costs[0][0]
                    b_cost, b_vid, b_p, b_d = vehicle_costs[0]

                if regret > max_regret:
                    max_regret = regret
                    best_req = req
                    best_vid = b_vid
                    best_p = b_p
                    best_d = b_d

            if best_req is not None and best_vid is not None and best_p != -1:
                veh = vehicles[best_vid]
                veh.route_nodes.insert(best_p, best_req.pickup_node)
                veh.route_nodes.insert(best_d, best_req.delivery_node)
                veh.route.append(best_req.req_id)
                veh.current_load += best_req.demand
                unassigned.remove(best_req)
            else:
                break

        return vehicles

    def _best_insert_pos(self, req: Request, vehicle: Vehicle, min_idx: int) -> Tuple[float, int, int]:
        route_nodes = vehicle.route_node_sequence()
        n = len(route_nodes)
        p_coord = self._get_coord(req.pickup_node)
        d_coord = self._get_coord(req.delivery_node)

        best_cost = float('inf')
        best_p = -1
        best_d = -1

        def prev_c(pos: int):
            if pos == 0:
                return self._get_coord(vehicle.current_node)
            return self._get_coord(route_nodes[pos - 1])

        def next_c(pos: int, length: int):
            if pos < length:
                return self._get_coord(route_nodes[pos])
            return None

        for p in range(min_idx, n + 1):
            pr_p = prev_c(p)
            nx_p = next_c(p, n)
            c_p = (self._euclidean(pr_p, p_coord) + self._euclidean(p_coord, nx_p) - self._euclidean(pr_p, nx_p)) if nx_p else self._euclidean(pr_p, p_coord)

            for d in range(p + 1, n + 2):
                pr_d = p_coord if d == p + 1 else self._get_coord(route_nodes[d - 2])
                nx_d = self._get_coord(route_nodes[d - 1]) if d <= n else None
                c_d = (self._euclidean(pr_d, d_coord) + self._euclidean(d_coord, nx_d) - self._euclidean(pr_d, nx_d)) if nx_d else self._euclidean(pr_d, d_coord)

                tot = c_p + c_d
                if tot < best_cost:
                    best_cost = tot
                    best_p = p
                    best_d = d

        return best_cost, best_p, best_d
