import psutil
import os
import pandas as pd

def get_ram_usage():
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

def get_local_mesh_profile(data_dir="data"):
    profiles = []
    if not os.path.exists(data_dir): return "No data directory found."
    for file in os.listdir(data_dir):
        if file.endswith('.csv'):
            path = os.path.join(data_dir, file)
            # Peek only header + 2 rows
            df = pd.read_csv(path, nrows=2)
            profiles.append({
                "file": file,
                "columns": list(df.columns),
                "sample": df.to_dict(orient='records')
            })
    return profiles
