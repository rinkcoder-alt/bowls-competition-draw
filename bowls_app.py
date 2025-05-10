import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Bowls England Draw Viewer", layout="centered")
st.title("🏆 Bowls England Competition Draw Viewer")

# Season mapping
season_map = {
    "2020": "1",
    "2021": "2",
    "2022": "3",
    "2023": "4",
    "2024": "5",
    "2025": "6"
}

available_seasons = list(season_map.keys())
selected_season = st.selectbox("Select Season", available_seasons, index=4)
season_id = season_map[selected_season]

# Stage selection
stage_name = st.radio("Select Stage", ["Early Stages", "Final Stages"])
stage_id = "1" if stage_name == "Early Stages" else "2"

# Fetch competition list from site
@st.cache_data(show_spinner=False)
def fetch_competitions(season_id, stage_id):
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Updated selector for competition links (using the correct class)
    comp_links = soup.select("a.pull-left.competition-name")
    
    # Debug: Print out the fetched links for inspection
    st.write("Fetched competition links:", comp_links)
    
    return {link.text.strip(): link['href'] for link in comp_links}

comps = fetch_competitions(season_id, stage_id)

if comps:
    selected_comp = st.selectbox("Select Competition", list(comps.keys()))
    
    # Fix the URL format by stripping the season part
    raw_href = comps[selected_comp]
    comp_id = raw_href.split("/")[-1]  # Get the competition ID
    comp_url = f"https://bowlsenglandcomps.com/competition/{comp_id}"  # Correct format

    # Fetch counties for selected competition
    @st.cache_data(show_spinner=False)
    def fetch_counties(comp_url):
        res = requests.get(comp_url)
        soup = BeautifulSoup(res.text, "html.parser")
        county_links = soup.select("a.card-body")
        return {link.text.strip(): link['href'] for link in county_links}

    counties = fetch_counties(comp_url)

    if counties:
        selected_county = st.selectbox("Select County", list(counties.keys()))
        full_url = f"https://bowlsenglandcomps.com{counties[selected_county]}"

        # Display constructed URL
        st.markdown(f"🔗 **Draw URL:** [Open Draw Page]({full_url})", unsafe_allow_html=True)

        # Button to show draw
        if st.button("Show Draw"):
            st.success("Opening draw page below 👇")
            st.markdown(f"[View Draw for {selected_county} - {stage_name}]({full_url})", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No counties found for this competition.")
else:
    st.warning("⚠️ No competitions found for this season and stage.")
