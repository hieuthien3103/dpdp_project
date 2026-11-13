import numpy as np
from typing import List, Dict, Tuple
from src.simulation.entities import Request

def parse_and_dynamize_li_lim(filepath: str, rho: float = 0.5, lead_time: float = 15.0, seed: int = 42) -> Tuple[List[Request], Dict, float]:
    """
    Đọc file Li & Lim tĩnh, ghép cặp điểm lấy-giao và động hoá thời điểm xuất hiện (tau_r).
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Đọc thông số xe và tải trọng từ dòng đầu tiên
    vehicle_info = lines[0].strip().split()
    capacity = float(vehicle_info[1])
    
    nodes = {}
    for line in lines[1:]:
        parts = line.strip().split()
        if not parts:
            continue
        node_id = int(parts[0])
        nodes[node_id] = {
            'x': float(parts[1]),
            'y': float(parts[2]),
            'demand': float(parts[3]),
            'ready_time': float(parts[4]),
            'due_date': float(parts[5]),
            'service_time': float(parts[6]),
            'pickup_idx': int(parts[7]),
            'delivery_idx': int(parts[8])
        }
        
    depot = nodes[0]
    requests = []
    
    # Phân tích các nút thành từng cặp Request (Điểm Lấy -> Điểm Giao)
    for node_id, data in nodes.items():
        if node_id != 0 and data['delivery_idx'] != 0:
            d_id = data['delivery_idx']
            d_data = nodes[d_id]
            
            # Tính khoảng cách đường chim bay từ kho đến điểm lấy (t_0r)
            t_0r = np.hypot(data['x'] - depot['x'], data['y'] - depot['y'])
            
            req = Request(
                req_id=node_id,
                pickup_node=node_id,
                delivery_node=d_id,
                demand=data['demand'],
                service_time=data['service_time'],
                e_pickup=data['ready_time'],
                l_pickup=data['due_date'],
                e_delivery=d_data['ready_time'],
                l_delivery=d_data['due_date']
            )
            req._t_0r = t_0r  # Biến tạm để hỗ trợ tính toán động hoá
            requests.append(req)
            
    # ==========================================
    # ĐỘNG HOÁ YÊU CẦU THEO CÔNG THỨC (1.3)
    # ==========================================
    rng = np.random.default_rng(seed)
    n = len(requests)
    n_dyn = int(np.ceil(rho * n))
    
    # Chọn ngẫu nhiên trích xuất đơn hàng động
    dyn_indices = set(rng.choice(n, size=n_dyn, replace=False))
    
    for idx, req in enumerate(requests):
        if idx in dyn_indices:
            req.is_dynamic = True
            # Tính tau_r ~ U(0, max{0, l_r - t_0r - Lambda})
            upper_bound = max(0.0, req.l_pickup - req._t_0r - lead_time)
            req.tau_r = round(float(rng.uniform(0.0, upper_bound)), 2)
        else:
            req.is_dynamic = False
            req.tau_r = 0.0
            
    # Xoá biến tạm
    for req in requests:
        delattr(req, '_t_0r')
        
    depot_info = {'x': depot['x'], 'y': depot['y'], 'due_date': depot['due_date']}
    return requests, depot_info, capacity
