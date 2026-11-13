import osmnx as ox
import os
from pathlib import Path

def download_and_save_map():
    places = [
        "District 1, Ho Chi Minh City, Vietnam",
        "District 3, Ho Chi Minh City, Vietnam"
    ]
    
    print("Đang tải dữ liệu mạng lưới đường bộ từ OpenStreetMap...")
    ox.settings.log_console = True
    ox.settings.use_cache = True
    
    # Chỉ lấy đường xe cộ lưu thông được, loại bỏ hẻm nhỏ hoặc đường đi bộ
    G = ox.graph_from_place(places, network_type='drive')
    
    output_dir = Path("data/hcm/processed")
    os.makedirs(output_dir, exist_ok=True)
    filepath = output_dir / "q1_q3_hcmc.graphml"
    
    ox.save_graphml(G, filepath=filepath)
    print(f"Hoàn tất! Đã lưu đồ thị vào {filepath}")

if __name__ == "__main__":
    download_and_save_map()
