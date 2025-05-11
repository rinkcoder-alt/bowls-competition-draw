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

# Default to current year
current_year = datetime.now().year
default_season = str(current_year) if str(current_year) in available_seasons else available_seasons[-1]

selected_season = st.selectbox("Select Season", available_seasons, index=available_seasons.index(default_season))
season_id = season_map[selected_season]

stage_name = st.radio("Select Stage", ["Early Stages", "Final Stages"], index=0)
stage_id = "1" if stage_name == "Early Stages" else "2"

@st.cache_data(show_spinner=False)
def fetch_competitions(season_id, stage_id):
    url = f"https://bowlsenglandcomps.com/season/{season_id}/{stage_id}"
    res = requests.get(url)
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
    res = requests.get(competition_url)
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
    res = requests.get(competition_url)
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

def parse_matchup(matchup):
    # Check for BYE
    if "BYE" in matchup:
        players = re.split(r"V|v|W/O", matchup)
        for player in players:
            if "(Challenger)" in player:
                challenger = player.replace("(Challenger)", "").strip()
                opponent = "BYE"
                return {
                    "Challenger": challenger,
                    "Opponent": opponent,
                    "Score": "No Score",
                    "Ends": "N/A"
                }
        return {"Challenger": "Unknown", "Opponent": "Unknown", "Score": "No Score", "Ends": "N/A"}

    # Check for Walkover
    if "W/O" in matchup:
        parts = matchup.split("W/O")
        if len(parts) == 2:
            p1, p2 = parts[0].strip(), parts[1].strip()
            if "(Challenger)" in p1:
                challenger = p1.replace("(Challenger)", "").strip()
                opponent = p2.strip()
            else:
                challenger = p2.replace("(Challenger)", "").strip()
                opponent = p1.strip()
            return {
                "Challenger": challenger,
                "Opponent": opponent,
                "Score": "Walkover",
                "Ends": "N/A"
            }

    # Check for score
    score_match = re.search(r"(\d+)\s*-\s*(\d+)", matchup)
    ends_match = re.search(r"Ends:\s*(\d+)", matchup)
    score = "No Score"
    ends = "N/A"

    if score_match:
        score = f"{score_match.group(1)} - {score_match.group(2)}"
    if ends_match:
        ends = ends_match.group(1)

    # Remove ends from text before splitting
    matchup_clean = re.sub(r"Ends:\s*\d+", "", matchup)
    matchup_clean = matchup_clean.replace("Ends:", "")

    # Split by score or V or W/O to extract names
    parts = re.split(r"\d+\s*-\s*\d+|V|v|W/O", matchup_clean)
    players = [p.strip() for p in parts if p.strip() != ""]

    challenger = opponent = "Unknown"
    for player in players:
        if "(Challenger)" in player:
            challenger = player.replace("(Challenger)", "").strip()
        else:
            opponent = player.strip()

    # Ensure score is shown as challenger - opponent
    if score_match and "(Challenger)" in players[-1]:
        score = f"{score_match.group(2)} - {score_match.group(1)}"

    return {
        "Challenger": challenger,
        "Opponent": opponent,
        "Score": score,
        "Ends": ends
    }

comps = fetch_competitions(season_id, stage_id)

if comps:
    selected_comp = st.selectbox("Select Competition", list(comps.keys()))
    selected_comp_id, selected_comp_url = comps[selected_comp]

    counties = fetch_counties(selected_comp_url)

    if counties:
        selected_county = st.selectbox("Select County", list(counties.keys()))
        selected_county_id = counties[selected_county]

        final_url = f"https://bowlsenglandcomps.com/competition/area-fixture/{selected_comp_id}/{selected_county_id}"
        results_df, rounds = fetch_results(final_url)

        st.markdown(f"[🔗 View on Bowls England]({final_url})")

        if results_df is not None and rounds:
            selected_round = st.selectbox("Select Round", rounds)
            if selected_round in results_df.columns:
                # Filtering the selected round and applying the parse_matchup function
                selected_column = results_df[selected_round].dropna()  # Remove any empty values
                parsed_data = selected_column.apply(parse_matchup)
                parsed_df = pd.DataFrame(parsed_data.tolist())
                st.dataframe(parsed_df)
            else:
                st.warning(f"No data available for round: {selected_round}")
        else:
            st.warning("No results available for this selection.")
    else:
        st.warning("No counties found.")
else:
    st.warning("No competitions found.")
