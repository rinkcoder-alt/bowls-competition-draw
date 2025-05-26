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

def parse_matchup(text):
    """Parses a match string and extracts challenger, opponent, score, and ends information."""
    original = text
    ends = re.search(r"Ends:\s*(\d+)", text)
    ends_val = ends.group(1) if ends else "N/A"
    text = re.sub(r"Ends:\s*\d+", "", text)

    score_match = re.search(r"(\d+)\s*-\s*(\d+)", text)
    score_val = f"{score_match.group(1)} - {score_match.group(2)}" if score_match else "No Score"

    splitters = [score_val, "V", "W/O"]
    for splitter in splitters:
        if splitter in text:
            parts = text.split(splitter)
            if len(parts) == 2:
                part1, part2 = parts
                break
    else:
        return {
            "Challenger": "Invalid", "From (C)": "Invalid",
            "Opponent": "Invalid", "From (O)": "Invalid",
            "Score": "Invalid", "Ends": "Invalid"
        }

    def clean_part(part):
        part = part.replace("(Challenger)", "").strip()
        return extract_name_and_location(part)

    if "(Challenger)" in part1:
        challenger, from_c = clean_part(part1)
        if "BYE" in part2:
            opponent, from_o = "BYE", "N/A"
        else:
            opponent, from_o = clean_part(part2)
    elif "(Challenger)" in part2:
        challenger, from_c = clean_part(part2)
        opponent, from_o = clean_part(part1)
        if score_val != "No Score":
            score_val = reverse_score(score_val)
    else:
        opponent, from_o = clean_part(part1)
        challenger, from_c = clean_part(part2)

    return {
        "Challenger": challenger,
        "From (C)": from_c,
        "Opponent": opponent,
        "From (O)": from_o,
        "Score": score_val,
        "Ends": ends_val
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
                parsed_data = selected_column.apply(parse_matchup)
                parsed_df = pd.DataFrame(parsed_data.tolist())
                st.dataframe(parsed_df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)
            else:
                st.warning(f"No data available for round: {selected_round}")
        else:
            st.warning("No results available for this selection.")
    else:
        st.warning("No counties found.")
else:
    st.warning("No competitions found.")
