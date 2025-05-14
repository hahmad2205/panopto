import streamlit as st

def processing_spinner_style():
    return st.markdown("""
        <style>
        .stSpinner > div > div {
            color: black !important;
        }
        </style>
        """, unsafe_allow_html=True)
