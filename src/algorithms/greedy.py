import math
from typing import List, Dict, Tuple, Optional
from src.simulation.entities import Request, Vehicle


class GreedyInsertion:
    def __init__(self, capacity_constraint: float, depot_xy: Tuple[float, float] = (0.0, 0.0)):
        self.capacity_constraint = capacity_constraint
        self.depot_xy = depot_xy
        self._node_coords: Dict[int, Tuple[float, float]] = {}

    @staticmethod
    def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    def _build_node_coords(self, pending_requests: List[Request], vehicles: Dict[int, Vehicle]) -> None:
        """Build a node-id → (x, y) lookup from depot, vehicles, and requests."""
        self._node_coords = {}
        # Depot node 0
        self._node_coords[0] = self.depot_xy
        # Vehicle start nodes (current positions)
        for vehicle in vehicles.values():
            if vehicle.current_x is not None and vehicle.current_y is not None:
                self._node_coords[vehicle.current_node] = (vehicle.current_x, vehicle.current_y)
        # All pending requests
        for req in pending_requests:
            if req.pickup_x is not None and req.pickup_y is not None:
                self._node_coords[req.pickup_node] = (req.pickup_x, req.pickup_y)
            if req.delivery_x is not None and req.delivery_y is not None:
                self._node_coords[req.delivery_node] = (req.delivery_x, req.delivery_y)

    def _get_coord(self, node_id: int) -> Tuple[float, float]:
        """Get coordinates for a node, defaulting to depot if unknown."""
        return self._node_coords.get(node_id, self.depot_xy)

    def solve(self, pending_requests: List[Request], vehicles: Dict[int, Vehicle], frozen_commitments: Dict[int, int]) -> List[Request]:
        """
        Greedy Insertion baseline:
        Repeatedly find and insert the request with the smallest insertion cost
        increase into available vehicles, respecting frozen commitments (H1).
        """
        self._build_node_coords(pending_requests, vehicles)

        # Also register coordinates from requests already in vehicle routes
        for vehicle in vehicles.values():
            for node_id in vehicle.route_nodes:
                if node_id not in self._node_coords:
                    # Try to find from known_requests if available; depot fallback
                    pass  # coords should already be populated from pending_requests

        unassigned = pending_requests.copy()

        while unassigned:
            best_req: Optional[Request] = None
            best_vehicle_id: Optional[int] = None
            best_cost_increase = float('inf')
            best_pickup_pos = -1
            best_delivery_pos = -1

            for req in unassigned:
                for vid, vehicle in vehicles.items():
                    frozen_node = frozen_commitments.get(vid)
                    result = self._evaluate_insertion(req, vehicle, frozen_node)
                    cost, pickup_pos, delivery_pos = result

                    if cost < best_cost_increase:
                        best_cost_increase = cost
                        best_req = req
                        best_vehicle_id = vid
                        best_pickup_pos = pickup_pos
                        best_delivery_pos = delivery_pos

            if best_req is not None and best_vehicle_id is not None:
                self._insert_request(vehicles[best_vehicle_id], best_req, best_pickup_pos, best_delivery_pos)
                unassigned.remove(best_req)
            else:
                break

        return unassigned

    def _evaluate_insertion(self, req: Request, vehicle: Vehicle, frozen_node: Optional[int]) -> Tuple[float, int, int]:
        """
        Evaluate the cheapest insertion of req into vehicle's route.
        Returns (cost_increase, pickup_position, delivery_position).
        Respects frozen_node constraint and capacity constraint.

        Tries all valid (pickup_pos, delivery_pos) pairs where
        pickup_pos < delivery_pos, with adjacent insertion as the
        primary strategy for greedy baseline simplicity.
        """
        # Capacity check: the vehicle must be able to carry the demand at peak
        # (demand is loaded at pickup, unloaded at delivery).
        # For a simple feasibility check, we verify that adding req.demand
        # doesn't exceed capacity at any point along the route.
        if vehicle.current_load + req.demand > self.capacity_constraint:
            return float('inf'), -1, -1

        route_nodes = vehicle.route_node_sequence()

        # Determine the minimum insertion index based on frozen_node
        min_allowed_idx = 0
        if frozen_node is not None and frozen_node in route_nodes:
            frozen_idx = route_nodes.index(frozen_node)
            min_allowed_idx = frozen_idx + 1

        pickup_coord = self._get_coord(req.pickup_node)
        delivery_coord = self._get_coord(req.delivery_node)

        best_cost = float('inf')
        best_p = -1
        best_d = -1

        n = len(route_nodes)

        # Build coord list for the current route: [depot/current, ...nodes..., depot/current]
        # The vehicle starts from its current position and the route ends
        # implicitly. We treat the route as a sequence that the vehicle
        # traverses, with the vehicle's current node as prefix context.
        # For insertion cost, we look at the neighbors in route_nodes.

        # Helper: get coord of the node at a given route position
        # If pos == 0: predecessor is vehicle.current_node
        # If pos == n (after all current nodes): there is no successor in route,
        #   so the insertion just extends the route.
        def node_coord_at(idx: int) -> Tuple[float, float]:
            """Coordinate of existing route_nodes[idx]."""
            return self._get_coord(route_nodes[idx])

        def prev_coord(pos: int) -> Tuple[float, float]:
            """Coordinate of the node before insertion position `pos`."""
            if pos == 0:
                return self._get_coord(vehicle.current_node)
            return self._get_coord(route_nodes[pos - 1])

        def next_coord(pos: int, route_len: int) -> Optional[Tuple[float, float]]:
            """Coordinate of the node after insertion position `pos`."""
            if pos < route_len:
                return self._get_coord(route_nodes[pos])
            return None  # inserting at the end, no successor

        # Try all valid (p, d) pairs with p >= min_allowed_idx and d > p
        for p in range(min_allowed_idx, n + 1):
            # Cost of inserting pickup at position p
            prev_p = prev_coord(p)
            next_p = next_coord(p, n)

            if next_p is not None:
                cost_pickup = (
                    self._euclidean(prev_p, pickup_coord)
                    + self._euclidean(pickup_coord, next_p)
                    - self._euclidean(prev_p, next_p)
                )
            else:
                # Inserting at end: only the detour from prev to pickup
                cost_pickup = self._euclidean(prev_p, pickup_coord)

            # After inserting pickup at p, the route has n+1 nodes.
            # Delivery must go at position d > p (at least p+1).
            # The route after pickup insertion looks like:
            #   [..., route_nodes[p-1], PICKUP, route_nodes[p], ...]
            # So for delivery positions, we need to account for the
            # shifted indices.

            for d in range(p + 1, n + 2):
                # After inserting pickup at p, the effective route is:
                #   route_nodes[0..p-1], pickup_node, route_nodes[p..n-1]
                # Delivery at position d in this new (n+1)-length route.

                # Previous node for delivery position d (in the modified route):
                if d == p + 1:
                    prev_d_coord = pickup_coord
                else:
                    # d > p+1: the node before d in the modified route
                    # is route_nodes[d - 2] (shifted by one due to pickup insertion)
                    prev_d_coord = self._get_coord(route_nodes[d - 2])

                # Next node for delivery position d (in the modified route):
                if d <= n:
                    # route_nodes[d - 1] in original (shifted by one for pickup)
                    next_d_coord = self._get_coord(route_nodes[d - 1])
                    cost_delivery = (
                        self._euclidean(prev_d_coord, delivery_coord)
                        + self._euclidean(delivery_coord, next_d_coord)
                        - self._euclidean(prev_d_coord, next_d_coord)
                    )
                else:
                    # Inserting delivery at the end
                    cost_delivery = self._euclidean(prev_d_coord, delivery_coord)

                total_cost = cost_pickup + cost_delivery
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_p = p
                    best_d = d

        if best_p == -1:
            return float('inf'), -1, -1

        return best_cost, best_p, best_d

    def _insert_request(self, vehicle: Vehicle, req: Request, pickup_pos: int, delivery_pos: int) -> None:
        """
        Insert pickup and delivery nodes into the vehicle's route at the
        specified positions. pickup_pos < delivery_pos is guaranteed.

        vehicle.route stores request IDs (one entry per request).
        vehicle.route_nodes stores the node visit sequence (pickup + delivery nodes).
        """
        # Insert pickup node first
        vehicle.route_nodes.insert(pickup_pos, req.pickup_node)
        # Insert delivery node (delivery_pos is relative to the route AFTER
        # pickup was inserted, so it's already correct)
        vehicle.route_nodes.insert(delivery_pos, req.delivery_node)

        # Append request ID to route (one entry per request, order of assignment)
        vehicle.route.append(req.req_id)

        # Update load: demand is loaded at pickup (delivery unloads it,
        # but current_load tracks the current cargo on the vehicle).
        # Since the vehicle hasn't physically visited the pickup yet,
        # we add the demand as a reservation to enforce capacity checks
        # for future insertions.
        vehicle.current_load += req.demand

        # Register coordinates for the newly inserted nodes
        if req.pickup_x is not None and req.pickup_y is not None:
            self._node_coords[req.pickup_node] = (req.pickup_x, req.pickup_y)
        if req.delivery_x is not None and req.delivery_y is not None:
            self._node_coords[req.delivery_node] = (req.delivery_x, req.delivery_y)
