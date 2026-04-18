import pandas as pd
import os
import json

def ingest_data_mesh(folder_path):
    inventory_summary = []
    
    for file in os.listdir(folder_path):
        if file.endswith(('.csv', '.xlsx')):
            path = os.path.join(folder_path, file)
            # Load data
            df = pd.read_csv(path) if file.endswith('.csv') else pd.read_excel(path)
            
            # Profile the file
            profile = {
                "file_name": file,
                "columns": list(df.columns),
                "row_count": len(df),
                "sample_data": df.head(2).to_dict(orient='records')
            }
            inventory_summary.append(profile)
            
    return inventory_summary

# Usage
# summary = ingest_data_mesh('./data')
# print(json.dumps(summary, indent=2))
