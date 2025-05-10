import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("Bowls England Competition Draw Viewer")

season = st.selectbox("Select Season", ["2020", "2021", "2022", "2023", "2024", "2025"], index=5)
competition = st.text_input("Enter Competition (exact name)")
county = st.text_input("Enter County")

if st.button("Fetch Draw"):
    st.write("Attempting to retrieve data...")

    # Placeholder logic — actual draw URL structure is dynamic
    base_url = f"https://bowlsenglandcomps.com/season/6"
    st.write(f"Go to: {base_url} and navigate manually for now (scraping not yet implemented).")