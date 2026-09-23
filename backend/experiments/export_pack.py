import os
import csv
import json
import shutil

def export_final_research_pack():
    exp_dir = os.path.join(os.path.dirname(__file__), "..", "data", "experiments")
    final_dir = os.path.join(exp_dir, "final_results")
    os.makedirs(final_dir, exist_ok=True)
    
    summary_path = os.path.join(exp_dir, "statistical_summary.json")
    if not os.path.exists(summary_path):
        print(f"[WARN] {summary_path} not found.")
        return
        
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 1. exact_vrp_summary.csv
    exact_data = data.get("vrp_exact_summary", [])
    if exact_data:
        csv_path = os.path.join(final_dir, "exact_vrp_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=exact_data[0].keys())
            writer.writeheader()
            writer.writerows(exact_data)
        print(f"[OK] Exported: {csv_path}")
        
    # 2. vrp_scalability_summary.csv
    vrp_scale = data.get("vrp_scalability_summary", [])
    if vrp_scale:
        csv_path = os.path.join(final_dir, "vrp_scalability_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=vrp_scale[0].keys())
            writer.writeheader()
            writer.writerows(vrp_scale)
        print(f"[OK] Exported: {csv_path}")
        
    # 3. dynamic_traffic_summary.csv
    dyn_data = data.get("dynamic_traffic_summary", [])
    if dyn_data:
        csv_path = os.path.join(final_dir, "dynamic_traffic_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=dyn_data[0].keys())
            writer.writeheader()
            writer.writerows(dyn_data)
        print(f"[OK] Exported: {csv_path}")
        
    # 4. parameter_sensitivity_summary.csv
    sens_data = data.get("parameter_sensitivity_summary", [])
    if sens_data:
        csv_path = os.path.join(final_dir, "parameter_sensitivity_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sens_data[0].keys())
            writer.writeheader()
            writer.writerows(sens_data)
        print(f"[OK] Exported: {csv_path}")
        
    # 5. point_to_point_summary.csv
    p2p_data = data.get("scalability_summary", [])
    if p2p_data:
        csv_path = os.path.join(final_dir, "point_to_point_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=p2p_data[0].keys())
            writer.writeheader()
            writer.writerows(p2p_data)
        print(f"[OK] Exported: {csv_path}")
        
    # 6. memetic_vs_qpso_summary.csv
    memetic_data = data.get("memetic_vs_qpso_summary", [])
    if memetic_data:
        csv_path = os.path.join(final_dir, "memetic_vs_qpso_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=memetic_data[0].keys())
            writer.writeheader()
            writer.writerows(memetic_data)
        print(f"[OK] Exported: {csv_path}")

    # 7. final_statistical_summary.json
    final_json_path = os.path.join(final_dir, "final_statistical_summary.json")
    shutil.copyfile(summary_path, final_json_path)
    print(f"[OK] Exported: {final_json_path}")
    
    print("\n[OK] FINAL RESEARCH RESULTS PACK CREATED IN backend/data/experiments/final_results/")

if __name__ == "__main__":
    export_final_research_pack()
