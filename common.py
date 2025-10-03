# common.py
import streamlit as st

def set_page_config():
    st.set_page_config(
        page_title="🍽️ Nutrition Dashboard",
        layout="wide"
    )

def apply_custom_styles():
    PAGE_CSS = """
    <style>
    /* App background */
    [data-testid="stAppViewContainer"] {
        background-image: url("https://img.freepik.com/premium-photo/chicken-breast-with-fresh-vegetables-spices-cooking_266870-353.jpg?semt=ais_hybrid&w=740&q=80");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: rgba(255,255,255,0.9);
    }

    /* Headers */
    h1,h2,h3 {
        color: #2E3B4E !important;
        text-align: center;
        font-weight: bold;
    }

    /* General text */
    .block-container {
        background-color: rgba(255,255,255,0.8);
        border-radius: 10px;
        padding: 2rem;
    }
    </style>
    """
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
