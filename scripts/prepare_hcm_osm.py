import os
import osmnx as ox
import networkx as nx
from pathlib import Path

def build_hcm_dataset():
    out_dir = Path("data/network_hcm")
    os.makedirs(out_dir, exist_ok=True)
    
    print("Đang tải dữ liệu mạng lưới đường bộ Quận 1 & 3 từ OpenStreetMap...")
    # Bounding box khu vực trung tâm Quận 1 & 3 (Bắc, Nam, Đông, Tây)
    north, south, east, west = 10.795, 10.755, 10.715, 10.670
    
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive', simplify=True)
    G = ox.truncate.largest_component(G, strongly=True)
    G = ox.routing.add_edge_speeds(G, fallback=30)
    G = ox.routing.add_edge_travel_times(G)
    
    # Lưu đồ thị dưới dạng .graphml (siêu nhẹ, sẵn sàng cho NetworkX)
    graph_path = out_dir / "q1_q3_hcmc.graphml"
    ox.save_graphml(G, filepath=graph_path)
    
    print(f"Hoàn tất! Đã lưu đồ thị vào {graph_path}")
    print(f"Số lượng nút (giao lộ): {len(G.nodes)}")
    print(f"Số lượng cạnh (đoạn đường): {len(G.edges)}")

if __name__ == "__main__":
    ox.settings.log_console = True
    ox.settings.use_cache = True
    build_hcm_dataset()
