# main.py
"""Main entry point for the Streamlit application."""

import streamlit as st

from data_manager import DataManager
from ui_components import UIComponents


def main() -> None:
    """Main application entry point."""
    st.set_page_config(layout="wide")
    DataManager.init_session_state()
    UIComponents.sidebar_controls()

    if st.session_state.page == "Data Upload & Configuration":
        st.title("Data Configuration")
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
        DataManager.handle_file_upload(uploaded_file)

        if st.session_state.current_df is not None:
            new_query, new_col, apply_clicked, add_clicked = (
                UIComponents.sql_configuration(
                    st.session_state.sql_query, st.session_state.new_col_sql
                )
            )

            if apply_clicked:
                DataManager.apply_sql_query(new_query)
                st.session_state.sql_query = new_query
            if add_clicked:
                DataManager.add_computed_column(new_col)
                st.session_state.new_col_sql = new_col

            UIComponents.display_settings()
    else:
        st.title("Data Preview")
        UIComponents.display_data_preview()

        if st.sidebar.button("Download table"):
            DataManager.save_current_df(st.session_state.current_df)


if __name__ == "__main__":
    main()
