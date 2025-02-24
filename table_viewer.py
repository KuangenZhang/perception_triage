import streamlit as st
import pandas as pd
import duckdb
from PIL import Image
import math
import os

def init_session_state():
    session_defaults = {
        'df': None,
        'current_df': None,
        'display_types': {},
        'labels': {},
        'current_page': 1,
        'rows_per_page': 10,
        'page': 'Data Upload & Configuration',
        'sort_column': None,
        'sort_ascending': True,
    }
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def sidebar_controls():
    with st.sidebar:
        st.header("Navigation")
        st.session_state.page = st.selectbox(
            "Select Page",
            ['Data Upload & Configuration', 'Data Preview'],
            index=0 if st.session_state.page == 'Data Upload & Configuration' else 1
        )
        
        if st.session_state.page == 'Data Preview' and st.session_state.current_df is not None:
            st.header("Pagination Settings")
            new_rows = st.number_input(
                "Rows per page",
                min_value=1,
                max_value=100,
                value=st.session_state.rows_per_page
            )
            if new_rows != st.session_state.rows_per_page:
                st.session_state.rows_per_page = new_rows
                st.session_state.current_page = 1  # Reset to first page

def handle_file_upload():
    st.header("1. Data Upload")
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.session_state.current_df = st.session_state.df.copy()
        st.session_state.display_types = {}
        st.session_state.labels = {}
        st.session_state.current_page = 1  # Reset pagination on new upload

def sql_configuration():
    st.header("2. SQL Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Column Selection")
        sql_query = st.text_area(
            "Input SQL Query",
            value="SELECT * FROM current_df",
            height=100
        )
        if st.button("Apply SQL"):
            apply_sql_query(sql_query)
    
    with col2:
        st.subheader("Add Computed Column")
        new_col_sql = st.text_input(
            "SQL for new column",
            placeholder="SELECT *, salary*2 AS bonus FROM current_df"
        )
        if st.button("Add Column"):
            add_computed_column(new_col_sql)

def copy_original_to_current():
    """Copy original_df to current_df"""
    st.session_state.current_df = st.session_state.df.copy()
    st.session_state.current_page = 1

def apply_sql_query(query):
    try:
        copy_original_to_current()
        conn = duckdb.connect()
        conn.register('current_df', st.session_state.current_df)
        result = conn.execute(query).fetchdf()
        st.session_state.current_df = result
        st.session_state.current_page = 1  # Reset pagination
        st.rerun()
    except Exception as e:
        st.error(f"SQL Error: {str(e)}")

def add_computed_column(query):
    try:
        conn = duckdb.connect()
        conn.register('current_df', st.session_state.current_df)
        new_df = conn.execute(query).fetchdf()
        st.session_state.current_df = new_df
        st.session_state.current_page = 1  # Reset pagination
        st.rerun()
    except Exception as e:
        st.error(f"Column Error: {str(e)}")

def display_settings():
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
                key=f"disp_{col_name}"
            )
    
    st.subheader("Column Labels")
    cols = st.columns(3)
    for idx, col_name in enumerate(st.session_state.current_df.columns):
        with cols[idx % 3]:
            current_label = st.session_state.labels.get(col_name, col_name)
            st.session_state.labels[col_name] = st.text_input(
                f"Label for {col_name}",
                value=current_label,
                key=f"label_{col_name}"
            )

def pagination_controls(df):
    if df is not None:
        total_pages = math.ceil(len(df) / st.session_state.rows_per_page)
        
        col1, col2, col3 = st.columns([2, 4, 2])
        with col1:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
        with col2:
            st.write(f"Showing rows {(st.session_state.current_page-1)*st.session_state.rows_per_page + 1} - "
                    f"{min(st.session_state.current_page*st.session_state.rows_per_page, len(df))} "
                    f"of {len(df)} total rows")
        with col3:
            prev, page_input, next = st.columns([2, 4, 2])
            with prev:
                if st.button("Previous") and st.session_state.current_page > 1:
                    st.session_state.current_page -= 1
                    st.rerun()
            with page_input:
                # Add a numeric input for direct page navigation
                new_page = st.number_input(
                    "Go to page",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.current_page,
                    step=1,
                    key="page_input"
                )
                if new_page != st.session_state.current_page:
                    st.session_state.current_page = new_page
                    st.rerun()
            with next:
                if st.button("Next") and st.session_state.current_page < total_pages:
                    st.session_state.current_page += 1
                    st.rerun()
        return total_pages


def sort_dataframe(df, column, ascending):
    """Sort dataframe while preserving categorical order"""
    try:
        return df.sort_values(by=column, ascending=ascending)
    except Exception as e:
        st.error(f"Sorting error: {str(e)}")
        return df

def display_column_headers(df, column_widths):
    """Create clickable column headers with sorting indicators"""
    cols = st.columns(column_widths)
    for idx, col_name in enumerate(df.columns):
        with cols[idx]:
            label = st.session_state.labels.get(col_name, col_name)
            
            # Add sorting indicator
            if st.session_state.sort_column == col_name:
                indicator = "▲" if st.session_state.sort_ascending else "▼"
                label += f" {indicator}"
            
            # Create clickable header
            if st.button(label, key=f"sort_{col_name}"):
                if st.session_state.sort_column == col_name:
                    # Toggle direction if same column clicked
                    st.session_state.sort_ascending = not st.session_state.sort_ascending
                else:
                    # New column, default to ascending
                    st.session_state.sort_column = col_name
                    st.session_state.sort_ascending = True
                st.rerun()

def calc_column_widths(df, img_column_width_sum = 0.5):
    n_column = len(df.columns)
    n_img_column = 0
    for col_name in df.columns:
        display_type = st.session_state.display_types.get(col_name, "Text")
        if display_type == "Image":
            n_img_column += 1
    n_non_img_column = n_column - n_img_column
    
    if n_img_column > 0:
        img_column_width = img_column_width_sum / n_img_column
    else:
        img_column_width = 0
    if n_non_img_column > 0:
        non_img_column_width = (1-img_column_width_sum) / n_non_img_column
    else:
        non_img_column_width = 0
    
    column_widths = []
    for col_name in df.columns:
        display_type = st.session_state.display_types.get(col_name, "Text")
        if display_type == "Image":
            column_widths.append(img_column_width)
        else:
            column_widths.append(non_img_column_width)
    return column_widths

def display_data_preview():
    st.header("Data Preview")
    
    if st.session_state.current_df is None:
        st.warning("Upload data first!")
        return
    
    df = st.session_state.current_df
    
    # Apply sorting
    if st.session_state.sort_column:
        df = sort_dataframe(df, 
                           st.session_state.sort_column,
                           st.session_state.sort_ascending)
    
    total_pages = pagination_controls(df)
    
    column_widths = calc_column_widths(df)
    # Display headers with sorting controls
    display_column_headers(df, column_widths)
    
    # Get current page slice
    start_idx = (st.session_state.current_page - 1) * st.session_state.rows_per_page
    end_idx = start_idx + st.session_state.rows_per_page
    page_df = df.iloc[start_idx:end_idx]
    
    
    # Display columns with proper formatting
    for _, row in page_df.iterrows():
        cols = st.columns(column_widths)
        for idx, col_name in enumerate(df.columns):
            with cols[idx]:
                label = st.session_state.labels.get(col_name, col_name)
                value = row[col_name]
                display_type = st.session_state.display_types.get(col_name, "Text")
                
                st.markdown(f"**{label}**")
                if display_type == "Image":
                    try:
                        img_paths = value.split(",")
                        with st.container():
                            for img_path in img_paths:
                                st.image(Image.open(img_path), use_container_width=True)
                    except Exception as e:
                        print(e)
                        st.write(value)
                else:
                    st.write(value)
        st.divider()

def main():
    st.set_page_config(layout="wide")
    init_session_state()
    sidebar_controls()
    
    if st.session_state.page == 'Data Upload & Configuration':
        st.title("Data Configuration")
        handle_file_upload()
        if st.session_state.current_df is not None:
            sql_configuration()
            display_settings()
    else:
        st.title("Data Preview")
        display_data_preview()

if __name__ == "__main__":
    main()