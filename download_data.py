import wandb
import os
import pandas as pd
import json
import shutil
from tqdm import tqdm 

def wandb_table_to_csv(artifact_dir:str, table_name:str, csv_name:str, img_column_idx: int = 0):
    # Load the JSON file
    with open(os.path.join(artifact_dir, table_name), "r") as f:
        data = json.load(f)

    assert "data" in data and "columns" in data
    # Extract the table data
    # Convert to pandas DataFrame
    columns = data["columns"]
    rows = data["data"]
    for row in rows:
        img_pred = row[img_column_idx]
        if isinstance(img_pred, dict) and img_pred.get("_type") == "image-file":
            row[img_column_idx] = os.path.join(artifact_dir, img_pred['path'])
    df = pd.DataFrame(rows, columns=columns)
    # Export to CSV
    df.to_csv(os.path.join(artifact_dir, csv_name), index=False)

def download_files(entity: str, project: str, run_id: str = "6ec5t9eu", path_prefix: str = "predictions_table.table.json"):
    run_folder_name = f"run-{run_id}-predictions_table:v0"
    # if not os.path.exists(run_folder):
    run = wandb.init()
    artifact = run.use_artifact(f'{entity}/{project}/{run_folder_name}', type='run_table')
    artifact_dir = artifact.download(path_prefix=path_prefix)
    return artifact_dir


def copy_src_imgs_to_cache(df, img_column_name, cache_img_column_name):
    """
    Copy images from the source path (df[img_column_name]) to the cache path (df[cache_img_column_name]).
    
    Args:
        df (pd.DataFrame): The DataFrame containing image paths.
        img_column_name (str): The column name for source image paths.
        cache_img_column_name (str): The column name for cache image paths.
    """
    for src_path, cache_path in tqdm(zip(df[img_column_name], df[cache_img_column_name])):
        # Ensure the source image exists
        if not os.path.exists(src_path):
            print(f"Warning: Source image not found: {src_path}")
            continue
        
        # Create the cache directory if it doesn't exist
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        # Copy the image from source to cache
        shutil.copy(src_path, cache_path)