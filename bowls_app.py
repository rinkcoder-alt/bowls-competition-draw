import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("🏆 Bowls England Competition Draw Viewer")

# Map seasons to IDs used in the URL
season_map = {
    "2020": "1",
    "2021": "2",
    "2022": "3",
    "2023": "4",
    "2024": "5",
    "2025": "6"
}

# Dropdown to select season
selected_season = st.selectbox("Select Season", list(season_map.keys()), index=5)
season_id = season_map[selected_season]

# Scrape competitions for the selected season
@st.cache_data(show_spinner=False)
def fetch_competitions(season_id):
    url = f"https://bowlsenglandcomps.com/season/{season_id}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    comp_links = soup.select("a.card-body")
    comps = {link.text.strip(): link['href'] for link in comp_links}
    return comps

comps = fetch_competitions(season_id)

if comps:
    selected_competition = st.selectbox("Select Competition", list(comps.keys()))
    comp_url = f"https://bowlsenglandcomps.com{comps[selected_competition]}"

    # Scrape counties from selected competition
    @st.cache_data(show_spinner=False)
    def fetch_counties(comp_url):
        res = requests.get(comp_url)
        soup = BeautifulSoup(res.text, "html.parser")
        county_links = soup.select("a.card-body")
        counties = {link.text.strip(): link['href'] for link in county_links}
        return counties

    counties = fetch_counties(comp_url)

    if counties:
        selected_county = st.selectbox("Select County", list(counties.keys()))
        county_url = f"https://bowlsenglandcomps.com{counties[selected_county]}"

        if st.button("Show Draw"):
            st.success("Opening draw page below 👇")
            st.markdown(f"[Click here to view draw for {selected_county}]({county_url})", unsafe_allow_html=True)
    else:
        st.warning("No counties found for this competition.")
else:
    st.warning("No competitions found for this season.")