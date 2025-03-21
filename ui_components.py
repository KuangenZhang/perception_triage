# ui_components.py
"""UI components and display logic for the Streamlit application."""

import base64
import math
from typing import Any, List

import pandas as pd
import streamlit as st

from config import FRAME_LABELS
from data_manager import DataManager


class UIComponents:
    """Class encapsulating UI rendering and interaction logic."""

    @staticmethod
    def render_img_html(image_path: str) -> None:
        """Render image from file path as HTML in Streamlit.

        Args:
            image_path: Path to the image file
        """
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"<img style='max-width:100%max-height:100%;' src='data:image/png;base64,{image_b64}'/>",
                unsafe_allow_html=True,
            )

    @staticmethod
    def sidebar_controls() -> None:
        """Render sidebar navigation and pagination controls."""
        with st.sidebar:
            st.header("Navigation")
            selected_page = st.selectbox(
                "Select Page",
                ["Data Upload & Configuration", "Data Preview"],
                index=(
                    0 if st.session_state.page == "Data Upload & Configuration" else 1
                ),
            )

            if selected_page != st.session_state.page:
                st.session_state.page = selected_page
                st.rerun()

            if (
                st.session_state.page == "Data Preview"
                and st.session_state.current_df is not None
            ):
                st.header("Pagination Settings")
                new_rows = st.number_input(
                    "Rows per page",
                    min_value=1,
                    max_value=100,
                    value=st.session_state.rows_per_page,
                )
                if new_rows != st.session_state.rows_per_page:
                    st.session_state.rows_per_page = new_rows
                    st.session_state.current_page = 1

    @staticmethod
    def sql_configuration(
        sql_query: str, new_col_sql: str
    ) -> tuple[str, str, bool, bool]:
        """Render SQL configuration interface.

        Args:
            sql_query: Current SQL query string
            new_col_sql: Current new column SQL string

        Returns:
            tuple: Contains (new_query, new_col, apply_clicked, add_clicked)
        """
        st.header("2. SQL Configuration")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Column Selection")
            new_query = st.text_area("Input SQL Query", value=sql_query, height=100)
            apply_clicked = st.button("Apply SQL")

        with col2:
            st.subheader("Add Computed Column")
            new_col = st.text_input("SQL for new column", placeholder=new_col_sql)
            add_clicked = st.button("Add Column")

        return new_query, new_col, apply_clicked, add_clicked

    @staticmethod
    def display_settings() -> None:
        """Render column display type and label settings."""
        st.header("3. Display Settings")
        st.subheader("Column Display Types")

        cols = st.columns(3)
        for idx, col_name in enumerate(st.session_state.current_df.columns):
            with cols[idx % 3]:
                current_type = st.session_state.display_types.get(col_name, "Text")
                st.session_state.display_types[col_name] = st.selectbox(
                    f"Type for {col_name}",
                    ["Text", "Number", "Image"],
                    index=["Text", "Number", "Image"].index(current_type),
                    key=f"disp_{col_name}",
                )

        st.subheader("Column Labels")
        cols = st.columns(3)
        for idx, col_name in enumerate(st.session_state.current_df.columns):
            with cols[idx % 3]:
                current_label = st.session_state.labels.get(col_name, col_name)
                st.session_state.labels[col_name] = st.text_input(
                    f"Label for {col_name}",
                    value=current_label,
                    key=f"label_{col_name}",
                )

    @staticmethod
    def pagination_controls(df: pd.DataFrame) -> Any:
        """Render pagination controls and handle navigation.

        Args:
            df: Current DataFrame being displayed

        Returns:
            int: Total number of pages
        """
        total_pages = math.ceil(len(df) / st.session_state.rows_per_page)
        with st.sidebar:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
            st.write(
                f"Showing rows {(st.session_state.current_page-1)*st.session_state.rows_per_page + 1} - "
                f"{min(st.session_state.current_page*st.session_state.rows_per_page, len(df))} "
                f"of {len(df)} total rows"
            )

            if st.button("Previous") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()

            new_page = st.number_input(
                "Go to page",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.current_page,
                step=1,
                key="page_input",
            )

            if new_page != st.session_state.current_page:
                st.session_state.current_page = new_page
                st.rerun()

            if st.button("Next") and st.session_state.current_page < total_pages:
                st.session_state.current_page += 1
                st.rerun()

        return total_pages

    @staticmethod
    def display_data_preview() -> None:
        """Main entry point for data preview display."""
        st.header("Data Preview")
        if st.session_state.current_df is None:
            st.warning("Upload data first!")
            return

        df = st.session_state.current_df
        if st.session_state.sort_column:
            df = UIComponents.sort_dataframe(df)

        UIComponents.pagination_controls(df)
        column_widths = UIComponents.calc_column_widths(df)
        UIComponents.display_column_headers(df, column_widths)

        start_idx = (st.session_state.current_page - 1) * st.session_state.rows_per_page
        end_idx = start_idx + st.session_state.rows_per_page
        page_df = df.iloc[start_idx:end_idx]

        for r_idx, row in page_df.iterrows():
            cols = st.columns(column_widths)
            for idx, col_name in enumerate(df.columns):
                with cols[idx]:
                    UIComponents.render_column_content(col_name, row, r_idx)
            st.divider()

    @staticmethod
    def render_column_content(col_name: str, row: pd.Series, r_idx: int) -> None:
        """Render individual column content based on display type.

        Args:
            col_name: Name of the column
            row: DataFrame row containing the data
            r_idx: Row index in the DataFrame
        """
        label = st.session_state.labels.get(col_name, col_name)
        value = row[col_name]
        display_type = st.session_state.display_types.get(col_name, "Text")

        st.markdown(f"**{label}**")

        if display_type == "Image":
            UIComponents.handle_image_display(value)
        elif col_name == "label":
            UIComponents.handle_label_edit(value, row, r_idx)
        else:
            st.write(value)

    @staticmethod
    def handle_image_display(value: str) -> None:
        """Handle image path(s) display logic.

        Args:
            value: Comma-separated image paths
        """
        try:
            img_paths = value.split(",")
            for img_path in img_paths:
                UIComponents.render_img_html(img_path)
        except Exception as e:
            st.write(value)

    @staticmethod
    def handle_label_edit(current_value: str, row: pd.Series, r_idx: int) -> None:
        """Handle label editing interface.

        Args:
            current_value: Current label value
            row: DataFrame row being edited
            r_idx: Row index in the DataFrame
        """
        new_label = st.selectbox(
            "label",
            FRAME_LABELS,
            index=FRAME_LABELS.index(current_value),
            key=f"label_select_{r_idx}",
            label_visibility="collapsed",
        )
        if new_label != current_value:
            frame_uuid = DataManager.get_frame_uuid(row)
            st.session_state.frame_labels[frame_uuid] = new_label
            DataManager.save_frame_labels()
            st.session_state.current_df.at[r_idx, "label"] = new_label

    @staticmethod
    def calc_column_widths(df: pd.DataFrame) -> List[float]:
        """Calculate column widths based on display types.

        Args:
            df: DataFrame being displayed

        Returns:
            List[float]: List of width ratios for each column
        """
        n_img_cols = sum(
            1
            for col in df.columns
            if st.session_state.display_types.get(col, "Text") == "Image"
        )
        n_non_img = len(df.columns) - n_img_cols

        img_width = 0.5 / n_img_cols if n_img_cols else 0
        non_img_width = (1 - 0.5) / n_non_img if n_non_img else 0

        return [
            (
                img_width
                if st.session_state.display_types.get(col, "Text") == "Image"
                else non_img_width
            )
            for col in df.columns
        ]

    @staticmethod
    def display_column_headers(df: pd.DataFrame, column_widths: List[float]) -> None:
        """Render clickable column headers with sorting indicators.

        Args:
            df: DataFrame being displayed
            column_widths: List of width ratios for columns
        """
        cols = st.columns(column_widths)
        for idx, col_name in enumerate(df.columns):
            with cols[idx]:
                label = st.session_state.labels.get(col_name, col_name)
                if st.session_state.sort_column == col_name:
                    indicator = "▲" if st.session_state.sort_ascending else "▼"
                    label += f" {indicator}"

                if st.button(label, key=f"sort_{col_name}"):
                    UIComponents.handle_sort_click(col_name)

    @staticmethod
    def handle_sort_click(col_name: str) -> None:
        """Handle sorting logic when column header is clicked.

        Args:
            col_name: Name of the column to sort by
        """
        if st.session_state.sort_column == col_name:
            st.session_state.sort_ascending = not st.session_state.sort_ascending
        else:
            st.session_state.sort_column = col_name
            st.session_state.sort_ascending = True
        st.rerun()

    @staticmethod
    def sort_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Sort DataFrame based on current sort configuration.

        Args:
            df: DataFrame to sort

        Returns:
            pd.DataFrame: Sorted DataFrame

        Raises:
            ValueError: If sorting fails
        """
        try:
            return df.sort_values(
                by=st.session_state.sort_column,
                ascending=st.session_state.sort_ascending,
            )
        except Exception as e:
            st.error(f"Sorting error: {str(e)}")
            return df
