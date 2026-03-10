# coding:utf-8

import streamlit as st
import pandas as pd
import chardet


# ====================================
# Read CSV files
# ====================================
def read_csv_file(file):
    # Detect file encoding
    raw_data = file.read()
    result = chardet.detect(raw_data)
    encoding = result["encoding"]
    file.seek(0)

    try:
        df = pd.read_csv(
            file,
            encoding= encoding,
            sep= None,
            engine= "python",
        )
        return df
    except Exception as e:
        st.error(f"Error reading CSV file : {e}")
        return None


# ====================================
# Read EXCEL files
# ====================================
def read_excel_file(file):
    try:
        excel_file = pd.ExcelFile(file)
        sheets = excel_file.sheet_names
        return excel_file, sheets
    except Exception as e:
        st.error(f"Error reading Excel file : {e}")
        return None, None