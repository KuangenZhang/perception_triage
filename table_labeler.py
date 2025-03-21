import streamlit as st
import pandas as pd
import duckdb
from PIL import Image
import math
import os
import base64
from data_utils import copy_src_imgs_to_dst

FRAME_LABELS = ["Pred:Bias", "Pred:FN", "Pred:FP", "Pred:Curve", "Pred:Occ", "Pred:Branch", "Pred:Merge",
                "GT:Bias", "GT:FN", "GT:FP", "GT:Elev", "GT:Incomp", "Normal"]
LABEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "labels.csv")
ARTIFACTS_FOLDER = os.path.join(os.path.dirname(__file__), "artifacts")

def render_img_html(image_path: str):
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"<img style='max-width:100%max-height:100%;' src = 'data:image/png;base64, {image_b64}'/>", 
                    unsafe_allow_html=True)

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
        'sql_query': None,
        'new_col_sql': None,
        'uploaded_file': None,
        "frame_labels": {},
        "model_versions": [],
    }
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def sidebar_controls():
    with st.sidebar:
        st.header("Navigation")
        selected_page = st.selectbox(
            "Select Page",
            ['Data Upload & Configuration', 'Data Preview'],
            index=0 if st.session_state.page == 'Data Upload & Configuration' else 1
        )
        
        # Check if the selected page has changed
        if selected_page != st.session_state.page:
            st.session_state.page = selected_page
            st.rerun()
        
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
    if uploaded_file and uploaded_file != st.session_state.uploaded_file:
        if os.path.exists(LABEL_FILE_PATH):
            label_df = pd.read_csv(LABEL_FILE_PATH)
            st.session_state.frame_labels = dict(zip(label_df["uuid"], label_df["label"]))
        
        st.session_state.df = pd.read_csv(uploaded_file)
        init_model_versions()
        init_frame_labels()
        
        st.session_state.current_df = st.session_state.df.copy()
        st.session_state.display_types = {}
        st.session_state.labels = {}
        st.session_state.current_page = 1  # Reset pagination on new upload
        st.session_state.uploaded_file = uploaded_file

def init_model_versions():
    assert len(st.session_state.df) > 0, "The current dataframe is empty"
    if "model_version" in st.session_state.df.columns:
        # single table
        st.session_state.model_versions = [st.session_state.df["model_version"][0]]
    else:
        # diff table
        st.session_state.model_versions = [st.session_state.df["model_version_0"][0], st.session_state.df["model_version_1"][0]]

def init_frame_labels():
    st.session_state.df["label"] = FRAME_LABELS[0]
    for r_idx, row in st.session_state.df.iterrows():
        frame_uuid = get_frame_uuid(row)
        if frame_uuid in st.session_state.frame_labels:
            st.session_state.df.at[r_idx, "label"] = st.session_state.frame_labels[frame_uuid]

def get_frame_uuid(row):
    frame_id = get_frame_id(row)
    frame_uuid = "_".join(st.session_state.model_versions + [frame_id])
    return frame_uuid

def get_frame_id(row):
    frame_id_keys = ["frame_id", "frame_id_0"] # single table and diff table.
    for key in frame_id_keys:
        if key in row:
            return str(row[key])
    raise Exception("No frame id in the table!")

def sql_configuration(sql_query: str = None, new_col_sql: str = None):
    if sql_query is None:
        sql_query = "SELECT img_cache, frame_id, label FROM current_df"
    if new_col_sql is None:
        new_col_sql = "SELECT *, salary*2 AS bonus FROM current_df"
    
    st.header("2. SQL Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Column Selection")
        sql_query = st.text_area(
            "Input SQL Query",
            value=sql_query,
            height=100
        )
        if st.button("Apply SQL"):
            apply_sql_query(sql_query)
    
    with col2:
        st.subheader("Add Computed Column")
        new_col_sql = st.text_input(
            "SQL for new column",
            placeholder=new_col_sql
        )
        if st.button("Add Column"):
            add_computed_column(new_col_sql)
    return sql_query, new_col_sql

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
    except Exception as e:
        st.error(f"SQL Error: {str(e)}")

def add_computed_column(query):
    try:
        conn = duckdb.connect()
        conn.register('current_df', st.session_state.current_df)
        new_df = conn.execute(query).fetchdf()
        st.session_state.current_df = new_df
        st.session_state.current_page = 1  # Reset pagination
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
        with st.sidebar:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
            st.write(f"Showing rows {(st.session_state.current_page-1)*st.session_state.rows_per_page + 1} - "
                        f"{min(st.session_state.current_page*st.session_state.rows_per_page, len(df))} "
                        f"of {len(df)} total rows")
            
            if st.button("Previous") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()
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
    
    pagination_controls(df)
    save_current_df(df)
    
    column_widths = calc_column_widths(df)
    # Display headers with sorting controls
    display_column_headers(df, column_widths)
    
    # Get current page slice
    start_idx = (st.session_state.current_page - 1) * st.session_state.rows_per_page
    end_idx = start_idx + st.session_state.rows_per_page
    page_df = df.iloc[start_idx:end_idx]
    
    
    # Display columns with proper formatting
    for r_idx, row in page_df.iterrows():
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
                                render_img_html(img_path)
                    except Exception as e:
                        print(e)
                        st.write(value)
                elif col_name == 'label':
                    new_frame_label = st.selectbox(
                        "label",
                        FRAME_LABELS,
                        index=FRAME_LABELS.index(value),
                        key=f"label_select_{r_idx}",
                        label_visibility="collapsed",
                    )
                    if new_frame_label != value:
                        frame_uuid = get_frame_uuid(row)
                        st.session_state.frame_labels[frame_uuid] = new_frame_label
                        save_frame_labels()
                        st.session_state.current_df.at[r_idx, 'label'] = new_frame_label
                else:
                    st.write(value)
        st.divider()

def save_current_df(df):
    dst_img_folder = os.path.join(ARTIFACTS_FOLDER, "important_imgs")
    file_name = st.sidebar.text_input("Enter CSV file name:", "labeled_table.csv")
    
    if st.sidebar.button("Download table"):
        processed_df = df.copy()
        processed_df = split_img_paths(processed_df)
        processed_df = add_img_dst_paths(processed_df, dst_img_folder)
        for i in range(len(st.session_state.model_versions)):
            copy_src_imgs_to_dst(processed_df[f"img_cache_{i}"], processed_df[f"img_dst_{i}"])
        
        # 3. Convert processed DF to CSV
        csv_path = os.path.join(ARTIFACTS_FOLDER, file_name)
        processed_df.to_csv(csv_path, index=False)
        st.success(f"CSV is successfully downloaded to {csv_path}. Images are copied to {dst_img_folder}")

def split_img_paths(processed_df: pd.DataFrame):
    if "img_cache" in processed_df.columns:
        processed_df["img_cache_0"] = processed_df["img_cache"]
    else:
        for r_idx, row in processed_df.iterrows():
            img_paths = row["img_cache_combined"].split(",")
            for i, img_path in enumerate(img_paths):
                processed_df.at[r_idx, f"img_cache_{i}"] = img_path
    return processed_df
    
def add_img_dst_paths(processed_df: pd.DataFrame, dst_img_folder:str):
    for i, model_version in enumerate(st.session_state.model_versions):
        processed_df[f"img_uuid_{i}"] = model_version + "_" + processed_df["frame_id"].astype(str)
        processed_df[f"img_dst_{i}"] = dst_img_folder + "/" + processed_df[f"img_uuid_{i}"] + ".png"
    return processed_df

def save_frame_labels():
    os.makedirs(os.path.dirname(LABEL_FILE_PATH), exist_ok=True)
    with open(LABEL_FILE_PATH, "w") as label_file:
        df = pd.DataFrame(list(st.session_state.frame_labels.items()), columns = ["uuid", "label"])
        df.to_csv(label_file, index=False)

def main():
    st.set_page_config(layout="wide")
    init_session_state()
    sidebar_controls()
    
    if st.session_state.page == 'Data Upload & Configuration':
        st.title("Data Configuration")
        handle_file_upload()
        if st.session_state.current_df is not None:
            st.session_state.sql_query, st.session_state.new_col_sql = \
                sql_configuration(st.session_state.sql_query, st.session_state.new_col_sql)
            display_settings()
    else:
        st.title("Data Preview")
        display_data_preview()

if __name__ == "__main__":
    main()