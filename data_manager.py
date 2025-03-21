# data_manager.py
"""Data management and processing operations for the Streamlit application."""

from pathlib import Path
from typing import Any, Dict, Optional

import duckdb
import pandas as pd
import streamlit as st

from config import ARTIFACTS_FOLDER, FRAME_LABELS, LABEL_FILE_PATH
from data_utils import copy_src_imgs_to_dst


class DataManager:
    """Class encapsulating data management and processing operations."""

    @staticmethod
    def init_session_state() -> None:
        """Initialize Streamlit session state with default values.

        Sets up default values for various session state variables including:
        - DataFrames (df, current_df)
        - Display configurations (display_types, labels)
        - Pagination settings (current_page, rows_per_page)
        - SQL configurations (sql_query, new_col_sql)
        """
        session_defaults: Dict[str, Any] = {
            "df": None,
            "current_df": None,
            "display_types": {},
            "labels": {},
            "current_page": 1,
            "rows_per_page": 10,
            "page": "Data Upload & Configuration",
            "sort_column": None,
            "sort_ascending": True,
            "sql_query": None,
            "new_col_sql": None,
            "uploaded_file": None,
            "frame_labels": {},
            "model_versions": [],
        }
        for key, value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def handle_file_upload(uploaded_file: Optional[Any]) -> None:
        """Handle CSV file upload and initialize data structures.

        Args:
            uploaded_file: Streamlit UploadedFile object or None

        Processes uploaded CSV file:
        1. Loads existing labels if available
        2. Initializes model versions from the data
        3. Sets up frame labels from historical data
        """
        if uploaded_file and uploaded_file != st.session_state.uploaded_file:
            if LABEL_FILE_PATH.exists():
                label_df = pd.read_csv(LABEL_FILE_PATH)
                st.session_state.frame_labels = dict(
                    zip(label_df["uuid"], label_df["label"])
                )

            st.session_state.df = pd.read_csv(uploaded_file)
            DataManager.init_model_versions()
            DataManager.init_frame_labels()

            st.session_state.current_df = st.session_state.df.copy()
            st.session_state.display_types = {}
            st.session_state.labels = {}
            st.session_state.current_page = 1
            st.session_state.uploaded_file = uploaded_file

    @staticmethod
    def init_model_versions() -> None:
        """Initialize model versions from the uploaded DataFrame.

        Raises:
            AssertionError: If the DataFrame is empty
        """
        assert not st.session_state.df.empty, "The current dataframe is empty"
        if "model_version" in st.session_state.df.columns:
            st.session_state.model_versions = [st.session_state.df["model_version"][0]]
        else:
            st.session_state.model_versions = [
                st.session_state.df["model_version_0"][0],
                st.session_state.df["model_version_1"][0],
            ]

    @staticmethod
    def init_frame_labels() -> None:
        """Initialize frame labels from historical data or default values."""
        st.session_state.df["label"] = FRAME_LABELS[0]
        for r_idx, row in st.session_state.df.iterrows():
            frame_uuid = DataManager.get_frame_uuid(row)
            if frame_uuid in st.session_state.frame_labels:
                st.session_state.df.at[r_idx, "label"] = st.session_state.frame_labels[
                    frame_uuid
                ]

    @staticmethod
    def get_frame_uuid(row: pd.Series) -> str:
        """Generate unique frame identifier.

        Args:
            row: DataFrame row containing frame information

        Returns:
            str: Unique identifier string combining model versions and frame ID
        """
        frame_id = str(row["frame_id"])
        return "_".join(st.session_state.model_versions + [frame_id])

    @staticmethod
    def apply_sql_query(query: Optional[str]) -> None:
        """Apply SQL query to the current DataFrame.

        Args:
            query: SQL query string to execute

        Raises:
            duckdb.Error: If there's an error in the SQL query
        """
        try:
            DataManager.copy_original_to_current()
            conn = duckdb.connect()
            conn.register("current_df", st.session_state.current_df)
            result = conn.execute(query).fetchdf()
            st.session_state.current_df = result
            st.session_state.current_page = 1
        except Exception as e:
            st.error(f"SQL Error: {str(e)}")

    @staticmethod
    def add_computed_column(query: Optional[str]) -> None:
        """Add computed column using SQL query.

        Args:
            query: SQL query string for column creation

        Raises:
            duckdb.Error: If there's an error in the SQL query
        """
        try:
            conn = duckdb.connect()
            conn.register("current_df", st.session_state.current_df)
            new_df = conn.execute(query).fetchdf()
            st.session_state.current_df = new_df
            st.session_state.current_page = 1
        except Exception as e:
            st.error(f"Column Error: {str(e)}")

    @staticmethod
    def copy_original_to_current() -> None:
        """Reset current DataFrame to original uploaded data."""
        st.session_state.current_df = st.session_state.df.copy()
        st.session_state.current_page = 1

    @staticmethod
    def save_current_df(df: pd.DataFrame) -> None:
        """Save current DataFrame to CSV and copy related images.

        Args:
            df: DataFrame to save

        Processes:
        1. Splits image paths into separate columns
        2. Adds destination paths for images
        3. Copies images to destination folder
        4. Saves processed DataFrame to CSV
        """
        dst_img_folder = ARTIFACTS_FOLDER / "important_imgs"
        processed_df = df.copy()
        processed_df = DataManager.split_img_paths(processed_df)
        processed_df = DataManager.add_img_dst_paths(processed_df, dst_img_folder)

        for i in range(len(st.session_state.model_versions)):
            copy_src_imgs_to_dst(
                processed_df[f"img_cache_{i}"], processed_df[f"img_dst_{i}"]
            )

        csv_path = ARTIFACTS_FOLDER / "labeled_table.csv"
        processed_df.to_csv(csv_path, index=False)
        st.success(f"CSV saved to {csv_path}. Images copied to {dst_img_folder}")

    @staticmethod
    def split_img_paths(df: pd.DataFrame) -> pd.DataFrame:
        """Split comma-separated image paths into separate columns.

        Args:
            df: DataFrame containing image paths

        Returns:
            pd.DataFrame: Modified DataFrame with split image paths
        """
        for r_idx, row in df.iterrows():
            img_paths = row["img_cache"].split(",")
            for i, img_path in enumerate(img_paths):
                df.at[r_idx, f"img_cache_{i}"] = img_path
        return df

    @staticmethod
    def add_img_dst_paths(df: pd.DataFrame, dst_folder: Path) -> pd.DataFrame:
        """Add destination paths for images based on model versions.

        Args:
            df: DataFrame containing image information
            dst_folder: Destination directory for images

        Returns:
            pd.DataFrame: Modified DataFrame with destination paths
        """
        for i, model_version in enumerate(st.session_state.model_versions):
            df[f"img_uuid_{i}"] = model_version + "_" + df["frame_id"].astype(str)
            df[f"img_dst_{i}"] = dst_folder / (df[f"img_uuid_{i}"] + ".png")
        return df

    @staticmethod
    def save_frame_labels() -> None:
        """Save current frame labels to CSV file."""
        LABEL_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            list(st.session_state.frame_labels.items()), columns=["uuid", "label"]
        )
        df.to_csv(LABEL_FILE_PATH, index=False)
