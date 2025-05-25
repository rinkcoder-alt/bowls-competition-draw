import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re

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
current_year = datetime.now().year
default_season = str(current_year) if str(current_year) in available_seasons else available_seasons[-1]

selected_season = st.selectbox("Select Season", available_seasons, index=available_seasons.index(default_season))
season_id = season_map[selected_season]

stage_name = st.radio("Select Stage", ["Early Stages", "Final Stages"], index=0)
stage_id = "1" if stage_name == "Early Stages" else "2"

@st.cache_data(show_spinner=False)
def fetch_competitions(season_id, stage_id):
    """Fetch a dictionary of competition names and their URLs for a given season and stage."""
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    res = requests.get(url)
    if res.status_code != 200:
        return {}
    soup = BeautifulSoup(res.text, "html.parser")
    comp_links = soup.find_all("a", href=True)
    comps = {}
    for link in comp_links:
        if "/competition/" in link['href']:
            comp_name_div = link.find("div", class_="pull-left competition-name")
            if comp_name_div:
                comp_name = comp_name_div.find("strong").text.strip().replace('> ', '')
                comp_id = link['href'].split('/')[-1]
                full_url = f"https://bowlsenglandcomps.com{link['href']}"
                comps[comp_name] = (comp_id, full_url)
    return comps

@st.cache_data(show_spinner=False)
def fetch_counties(competition_url):
    """Fetch a dictionary of counties and their IDs from a given competition URL."""
    res = requests.get(competition_url)
    if res.status_code != 200:
        return {}
    soup = BeautifulSoup(res.text, "html.parser")
    county_links = soup.find_all("a", class_="area-fixture-link")
    counties = {}
    for link in county_links:
        name = link.text.strip()
        county_id = link['href'].split("/")[-1]
        counties[name] = county_id
    return counties

@st.cache_data(show_spinner=False)
def fetch_results(competition_url):
    """Fetch results table data and round headers from a county-specific competition URL."""
    res = requests.get(competition_url)
    if res.status_code != 200:
        return None, None
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", class_="table")
    if table:
        headers = [th.text.strip() for th in table.find("thead").find_all("th")]
        rows = []
        for row in table.find("tbody").find_all("tr"):
            data = [td.text.strip() for td in row.find_all("td")]
            rows.append(data)
        df = pd.DataFrame(rows, columns=headers)
        return df, headers
    return None, None

def extract_name_and_location(text):
    """Extracts and returns the name and location from a string formatted as 'Name (Location)'."""
    name = text.split('(')[0].strip()
    location = text[text.find('(')+1:text.rfind(')')].strip()
    return name, location

def reverse_score(score):
    """Reverses a score string from 'X - Y' to 'Y - X'."""
    if score != "No Score":
        parts = score.split(" - ")
        return f"{parts[1]} - {parts[0]}"
    return score

def parse_matchup_html(td):
    """
    Extract challenger, opponent, score, and ends from a <td> BeautifulSoup element.
    """
    spans = td.find_all("span")

    names = [s.get_text(strip=True) for s in spans if "team_name" in s.get("class", [])]
    locations = [s.get_text(strip=True) for s in spans if "team_name_line_2" in s.get("class", [])]
    result_text = next((s.get_text(strip=True) for s in spans if "fixture_result" in s.get("class", [])), "")
    ends_text = next((s.get_text(strip=True) for s in spans if "ends" in s.get("class", [])), None)

    midpoint = len(spans) // 2
    challenger_idx = None
    for i, span in enumerate(spans):
        if "challenger" in span.get("class", []):
            challenger_idx = 1 if i > midpoint else 0
            break

    if challenger_idx is None:
        challenger_idx = 1

    opponent_idx = 1 - challenger_idx

    # Safety checks
    if len(names) < 2 or len(locations) < 2:
        return {
            "Challenger": "N/A",
            "From (C)": "N/A",
            "Opponent": "N/A",
            "From (O)": "N/A",
            "Score": "N/A",
            "Ends": "N/A"
        }

    # Normalize score text
    if "-" not in result_text:
        result_text = "No Score"

    return {
        "Challenger": names[challenger_idx],
        "From (C)": locations[challenger_idx],
        "Opponent": names[opponent_idx],
        "From (O)": locations[opponent_idx],
        "Score": result_text,
        "Ends": ends_text or "N/A"
    }



# MAIN UI FLOW
with st.spinner("Fetching competitions..."):
    comps = fetch_competitions(season_id, stage_id)

if comps:
    selected_comp = st.selectbox("Select Competition", list(comps.keys()))
    selected_comp_id, selected_comp_url = comps[selected_comp]

    with st.spinner("Fetching counties..."):
        counties = fetch_counties(selected_comp_url)

    if counties:
        selected_county = st.selectbox("Select County", list(counties.keys()))
        selected_county_id = counties[selected_county]

        final_url = f"https://bowlsenglandcomps.com/competition/area-fixture/{selected_comp_id}/{selected_county_id}"
        with st.spinner("Fetching results..."):
            results_df, rounds = fetch_results(final_url)

        st.markdown(f"[🔗 View on Bowls England]({final_url})")

        if results_df is not None and rounds:
            selected_round = st.selectbox("Select Round", rounds[::-1])
            if selected_round in results_df.columns:
                selected_column = results_df[selected_round].dropna()
                parsed_data = []
                for _, row in results_df.iterrows():
                    raw_html = row[selected_round]
                    if pd.notna(raw_html):
                        soup = BeautifulSoup(raw_html, "html.parser")
                        td = soup.find("td")
                        if td:
                            parsed_data.append(parse_matchup_html(td))

                parsed_df = pd.DataFrame(parsed_data)
                st.dataframe(parsed_df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)
            else:
                st.warning(f"No data available for round: {selected_round}")
        else:
            st.warning("No results available for this selection.")
    else:
        st.warning("No counties found.")
else:
    st.warning("No competitions found.")
