""" 
python download_table.py -m laneatt_tusimple_resnet18_20250202_133647 laneatt_tusimple_resnet18_20250202_133647 -r 71dd2pnq gkhtc7x4 -d mean_iou

SQL:
SELECT img_cache_combined, mean_iou_diff, frame_id_0 as frame_id,  mean_iou_0 , mean_iou_1
FROM current_df
"""

from data_utils import download_files, wandb_table_to_csv, copy_src_imgs_to_dst
import os
import argparse
import pandas as pd


def combine_tables(df_list, cache_img_column_name: str, metrics_for_diff: str) -> pd.DataFrame:
    assert len(df_list) == 2
    df_combined = pd.concat(df_list, axis=1, keys=[0, 1])
    df_combined.columns = [f"{col[1]}_{col[0]}" for col in df_combined.columns]
    # Combine cache image paths from both DataFrames
    df_combined[f"{cache_img_column_name}"] = (
        df_list[0][cache_img_column_name].astype(str) + "," + df_list[1][cache_img_column_name].astype(str)
    )

    # Calculate the difference between metrics in the two DataFrames
    df_combined[f"{metrics_for_diff}_diff"] = (
        df_list[1][metrics_for_diff] - df_list[0][metrics_for_diff]
    )
    df_combined["frame_id"] = df_combined["frame_id_0"]
    return df_combined

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model_versions", type=str, nargs='+', required=True, help="Versions the model")
    parser.add_argument("-r", "--run_ids", type=str, nargs='+', required=True, help="Run ids of the test.")
    parser.add_argument("-d", "--metrics_for_diff", type=str, required=True, help="The metrics to calculate diff")
    parser.add_argument("-e", "--entity", type=str, default="zhangkevin", help="Entity name")
    parser.add_argument("-p", "--project", type=str, default="LaneDetection2D", help="Project name")
    parser.add_argument("-i", "--img_column_idx", type=int, default=0, help="Image column idx in the table")
    parser.add_argument("-t", "--table_name", type=str, default="predictions_table.table.json", help="Table name")
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    cache_img_column_name = "img_cache"
    print(args.model_versions)
    df_list = []
    for model_version, run_id in zip(args.model_versions, args.run_ids):
        # download the tables
        table_name = args.table_name
        csv_name = "predictions_table.csv"
        artifact_dir = download_files(args.entity, args.project, run_id, path_prefix=table_name)
        
        artifact_root_dir = os.path.dirname(artifact_dir)
        model_artifact_dir = os.path.join(artifact_root_dir, model_version)
        
        csv_path = os.path.join(artifact_dir, csv_name)
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        else:
            wandb_table_to_csv(artifact_dir, table_name, csv_name, img_column_idx=args.img_column_idx)
            df = pd.read_csv(csv_path)
            img_column_name = df.columns[args.img_column_idx]
            assert "frame_id" in df.columns, "Error: 'frame_id' column is missing in the DataFrame."
            df[cache_img_column_name] = df["frame_id"].apply(lambda x: os.path.join(model_artifact_dir, "media", f"{x}.png"))
            df["model_version"] = model_version
            df.to_csv(csv_path, index=False)
        
            if not os.path.exists(model_artifact_dir):
                download_files(args.entity, args.project, run_id, path_prefix="media/")
                # copy imgs from df[img_column_name] to df[cache_img_column_name]
                copy_src_imgs_to_dst(df[img_column_name], df[cache_img_column_name])

        df_list.append(df)
    
    print(len(df_list))
     
    df_combined = combine_tables(df_list, cache_img_column_name, args.metrics_for_diff)
    print(f"Downloaded table to {csv_path}")
    df_combined_path = os.path.join(artifact_root_dir, "_".join(args.model_versions) + ".csv")
    df_combined.to_csv(df_combined_path, index=False)
    print(f"Saved combined dataframe to {df_combined_path}")
    

if __name__ == "__main__":
    main()
    


