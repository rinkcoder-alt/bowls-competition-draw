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

# Fetch county list from site
@st.cache_data(show_spinner=False)
def fetch_counties(season_id, stage_id):
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Find all <a> tags with the class "area-fixture-link" for counties
    county_links = soup.find_all("a", class_="area-fixture-link")
    
    counties = {}
    for county_link in county_links:
        county_name = county_link.text.strip()
        county_url = county_link['href']
        counties[county_name] = county_url
    
    return counties

# Fetch competition list from site
@st.cache_data(show_spinner=False)
def fetch_competitions(season_id, stage_id, county_url=None):
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    if county_url:
        url += f"/{county_url}"
    
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Select competition links and competition names
    comp_links = soup.find_all("a", href=True)  # Find all <a> tags with href
    
    comps = {}
    for link in comp_links:
        # Check if the <a> tag is a competition link (contains "/competition/")
        if "/competition/" in link['href']:
            comp_name_div = link.find("div", class_="pull-left competition-name")
            if comp_name_div:
                # Extract competition name from the <strong> tag
                comp_name = comp_name_div.find("strong").text.strip().replace('> ', '')  # Clean up the name
                comp_url = link['href']
                full_url = f"https://bowlsenglandcomps.com{comp_url}"
                comps[comp_name] = full_url
    
    return comps

# Fetch counties
counties = fetch_counties(season_id, stage_id)

# If counties are available, allow user to select a county
if counties:
    selected_county = st.selectbox("Select County", list(counties.keys()))
    county_url = counties[selected_county]
else:
    county_url = None

# Fetch competitions based on selected season, stage, and county
comps = fetch_competitions(season_id, stage_id, county_url)

if comps:
    # Create a selectable dropdown for competitions
    selected_comp = st.selectbox("Select Competition", list(comps.keys()))
    
    # Display the selected competition's link
    if selected_comp:
        st.write(f"### You selected: {selected_comp}")
        st.write(f"Link to competition: [Click here]({comps[selected_comp]})")
else:
    st.warning("⚠️ No competitions found for this season, stage, and county.")
