import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

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

# Get the current year
current_year = datetime.now().year

# Default season is set to the current year
selected_season = str(current_year) if str(current_year) in available_seasons else available_seasons[-1]
season_id = season_map[selected_season]

# Select season, defaulting to the current year
selected_season = st.selectbox("Select Season", available_seasons, index=available_seasons.index(selected_season))
season_id = season_map[selected_season]

# Stage selection with default "Early Stages"
stage_name = st.radio("Select Stage", ["Early Stages", "Final Stages"], index=0)  # Default is "Early Stages"
stage_id = "1" if stage_name == "Early Stages" else "2"

# Fetch competition list from site
@st.cache_data(show_spinner=False)
def fetch_competitions(season_id, stage_id):
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Find all <a> tags with the class "competition-name" for competitions
    comp_links = soup.find_all("a", href=True)
    
    comps = {}
    for link in comp_links:
        # Check if the <a> tag is a competition link (contains "/competition/")
        if "/competition/" in link['href']:
            comp_name_div = link.find("div", class_="pull-left competition-name")
            if comp_name_div:
                # Extract competition name from the <strong> tag
                comp_name = comp_name_div.find("strong").text.strip().replace('> ', '')  # Clean up the name
                comp_url = link['href']
                comp_id = comp_url.split('/')[-1]  # Get competition ID
                full_url = f"https://bowlsenglandcomps.com{comp_url}"
                comps[comp_name] = (comp_id, full_url)
    
    return comps

# Fetch counties for the selected competition
@st.cache_data(show_spinner=False)
def fetch_counties(competition_url):
    res = requests.get(competition_url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Find all <a> tags with the class "area-fixture-link" for counties
    county_links = soup.find_all("a", class_="area-fixture-link")
    
    counties = {}
    for county_link in county_links:
        county_name = county_link.text.strip()
        county_url = county_link['href'].strip().split("/")[-1]  # Extract county_id from URL
        counties[county_name] = county_url
    
    return counties

# Fetch competition results (table)
@st.cache_data(show_spinner=False)
def fetch_results(competition_url):
    res = requests.get(competition_url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Find the table that contains the match results
    table = soup.find("table", class_="table")  # Replace 'table' and class name with correct class
    
    if table:
        headers = []
        rows = []
        
        # Extract headers (rounds)
        header_row = table.find("thead").find_all("th")
        headers = [header.text.strip() for header in header_row]
        
        # Extract rows (matches)
        body_rows = table.find("tbody").find_all("tr")
        for row in body_rows:
            columns = row.find_all("td")
            match_data = [col.text.strip() for col in columns]
            rows.append(match_data)
        
        # Create a dataframe for display
        df = pd.DataFrame(rows, columns=headers)
        return df, headers
    else:
        return None, None

# Fetch competitions for the selected season and stage
comps = fetch_competitions(season_id, stage_id)

# Competition selection with search functionality
if comps:
    selected_comp = st.selectbox("Select Competition (searchable)", list(comps.keys()))
    selected_comp_id, selected_comp_url = comps[selected_comp]

    # Fetch counties based on the selected competition
    counties = fetch_counties(selected_comp_url)
    
    # County selection with search functionality
    if counties:
        selected_county = st.selectbox("Select County (searchable)", list(counties.keys()))
        selected_county_id = counties[selected_county]

        # Construct the URL for the selected competition and county
        final_url = f"https://bowlsenglandcomps.com/competition/area-fixture/{selected_comp_id}/{selected_county_id}"

        # Fetch competition results
        results_df, rounds = fetch_results(final_url)

        st.write(f"You've selected **{selected_comp}** for **{selected_county}**.")
        st.write(f"Competition ID: {selected_comp_id} | County ID: {selected_county_id}")
        st.write(f"Final URL: [Click here to view the competition]({final_url})")

        # Check if results_df exists and display column names
        if results_df is not None and rounds:
            st.write("### Available Columns (Rounds):")
            st.write(results_df.columns)  # Display the column names for debugging
            
            # Allow user to select the round
            selected_round = st.selectbox("Select Round", rounds)
            
            # Check if the selected_round exists in columns
            if selected_round in results_df.columns:
                st.write(f"Displaying results for **{selected_round}**:")
                st.dataframe(results_df[["Matchup", selected_round]])  # Displaying only the selected round's data
            else:
                st.warning(f"⚠️ Selected round **{selected_round}** not found.")
        else:
            st.warning("⚠️ No results found for this competition and county.")
    else:
        st.warning("⚠️ No counties found for the selected competition.")
else:
    st.warning("⚠️ No competitions found for this season and stage.")
