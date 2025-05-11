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
    original_text = matchup  # Keep the original text for debugging

    # Normalize spacing
    matchup = re.sub(r'\s+', ' ', matchup).strip()

    # Check for BYE
    if "BYE" in matchup:
        if "(Challenger)" in matchup:
            # If BYE is followed by (Challenger), challenger is BYE
            players = matchup.split("BYE(Challenger)")
            challenger = "BYE"
            opponent = players[0].strip() if players[0].strip() else "Unknown"
            return {
                "Full Text": original_text,
                "Challenger": challenger,
                "Opponent": opponent,
                "Score": "No Score",
                "Ends": "N/A"
            }
        else:
            # If BYE is anywhere else, it's the opponent
            players = matchup.split("BYE")
            challenger = players[0].strip() if players[0].strip() else "Unknown"
            opponent = "BYE"
            return {
                "Full Text": original_text,
                "Challenger": challenger,
                "Opponent": opponent,
                "Score": "No Score",
                "Ends": "N/A"
            }

    # Check for Walkover (W/O)
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
                "Full Text": original_text,
                "Challenger": challenger,
                "Opponent": opponent,
                "Score": "Walkover",
                "Ends": "N/A"
            }

    # Extract score and ends (if any)
    score_match = re.search(r"(\d+)\s*-\s*(\d+)", matchup)
    ends_match = re.search(r"Ends:\s*(\d+)", matchup)
    score = "No Score"
    ends = "N/A"

    if score_match:
        score = f"{score_match.group(1)} - {score_match.group(2)}"
    if ends_match:
        ends = ends_match.group(1)

    # Extract challenger (the name immediately before (Challenger))
    challenger_match = re.search(r"([^(]+)\s*\(Challenger\)", matchup)
    challenger = challenger_match.group(1).strip() if challenger_match else "Unknown"

    # Get all players with club (handling the outermost parentheses)
    all_players = re.findall(r"([A-Z][a-zA-Z' .-]+(?:\(.*?\))?)", matchup)
    opponent = next((p for p in all_players if p != challenger), "Unknown")

    # If (Challenger) is at the end, reverse the score
    if "(Challenger)" in matchup and matchup.endswith("(Challenger)"):
        score = f"{score_match.group(2)} - {score_match.group(1)}" if score_match else "No Score"

    return {
        "Full Text": original_text,
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
