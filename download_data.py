import wandb
import os
import pandas as pd
import json

def wandb_json_to_csv(run_folder, json_name, csv_name, img_column_idx = 0):
    # Load the JSON file
    with open(os.path.join(run_folder, json_name), "r") as f:
        data = json.load(f)

    # Extract the table data
    if "data" in data and "columns" in data:
        # Convert to pandas DataFrame
        columns = data["columns"]
        rows = data["data"]
        for row in rows:
            img_pred = row[img_column_idx]
            if isinstance(img_pred, dict) and img_pred.get("_type") == "image-file":
                row[img_column_idx] = os.path.join(run_folder, img_pred['path'])
        df = pd.DataFrame(rows, columns=columns)
        # Export to CSV
        df.to_csv(os.path.join(run_folder, csv_name), index=False)

run_id = "6ec5t9eu"
run_folder_name = f"run-{run_id}-predictions_table:v0"
run_folder = os.path.join("artifacts", run_folder_name)
if not os.path.exists(run_folder):
    run = wandb.init()
    artifact = run.use_artifact(f'zhangkevin/LaneDetection2D/{run_folder_name}', type='run_table')
    artifact_dir = artifact.download()

wandb_json_to_csv(run_folder, "predictions_table.table.json", "predictions_table.csv")