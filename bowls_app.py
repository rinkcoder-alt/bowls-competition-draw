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

from bs4 import BeautifulSoup

def parse_matchup_html(cell_html):
    soup = BeautifulSoup(cell_html, "html.parser")
    p = soup.find("p")
    if not p:
        return {
            "Challenger": "N/A",
            "From (C)": "N/A",
            "Opponent": "N/A",
            "From (O)": "N/A",
            "Score": "N/A",
            "Ends": "N/A"
        }

    # Extract all text spans with their class
    spans = p.find_all("span")

    # Extract team names and locations (in order)
    team_names = [span.get_text(strip=True) for span in spans if "team_name" in span.get("class", [])]
    locations = [span.get_text(strip=True) for span in spans if "team_name_line_2" in span.get("class", [])]
    scores = [span.get_text(strip=True) for span in spans if "fixture_result" in span.get("class", [])]
    challengers = [span for span in spans if "challenger" in span.get("class", [])]

    # Find which team is challenger by seeing where the challenger span is positioned
    # Usually challenger span is near one of the teams

    # By position, challenger span usually appears after the second team's name/location,
    # but it might be inside <strong> tag so let’s check text near each team

    # Because team_names and locations come in order, assume:
    # team_names[0], locations[0] = team 1
    # team_names[1], locations[1] = team 2

    # Determine challenger side:
    challenger_side = None
    # We try to find if challenger text is closer to first or second team
    # Let's get all texts inside <p> split by line breaks and find indices of challenger and team names

    p_texts = [str(elem).strip() for elem in p.contents if isinstance(elem, (str,)) or (hasattr(elem, 'name') and elem.name != 'br')]

    # But since contents may be mixed, safer approach is to see which team the challenger span is closest to by tag order
    # Alternatively, just check if "challenger" span appears after first team_name spans or second

    # We can locate the challenger span inside p, then find nearest preceding team_name span

    # Locate challenger span index among spans
    challenger_index = None
    for i, span in enumerate(spans):
        if "challenger" in span.get("class", []):
            challenger_index = i
            break

    # Now find indices of team_name spans
    team_name_indices = [i for i, span in enumerate(spans) if "team_name" in span.get("class", [])]

    # Determine which team_name span is closest but before challenger span
    challenger_side_idx = None
    if challenger_index is not None:
        # Find closest team_name index less than challenger_index
        possible_teams = [idx for idx in team_name_indices if idx < challenger_index]
        if possible_teams:
            challenger_side_idx = max(possible_teams)
        else:
            challenger_side_idx = team_name_indices[0] if team_name_indices else None

    # Based on that, challenger is:
    # If challenger_side_idx corresponds to team_names index 0 or 1

    # Map span index to team index:
    # team_name_indices list is ordered, so challenger_side_idx corresponds to team index by position
    if challenger_side_idx is not None and len(team_name_indices) >= 2:
        if challenger_side_idx == team_name_indices[0]:
            challenger_team = 0
            opponent_team = 1
        elif challenger_side_idx == team_name_indices[1]:
            challenger_team = 1
            opponent_team = 0
        else:
            challenger_team = 0
            opponent_team = 1
    else:
        challenger_team = 0
        opponent_team = 1

    # Score might be text like "21 - 20", "V", "W/O", etc.
    # There may be multiple fixture_result spans but usually one main score - pick the first or the one with dash

    score_text = None
    for score in scores:
        if "-" in score or score.upper() in ["V", "W/O"]:
            score_text = score
            break
    if not score_text and scores:
        score_text = scores[0]

    # Try to find Ends info - it's inside <small><b>Ends: XX</b></small> or may be missing
    ends_text = "N/A"
    ends_tag = p.find("small")
    if ends_tag:
        ends_text = ends_tag.get_text(strip=True)
        # Clean to just get the number after "Ends: "
        if ends_text.lower().startswith("ends:"):
            ends_text = ends_text.split(":")[1].strip()

    # Compose final dict
    return {
        "Challenger": team_names[challenger_team] if len(team_names) > challenger_team else "N/A",
        "From (C)": locations[challenger_team] if len(locations) > challenger_team else "N/A",
        "Opponent": team_names[opponent_team] if len(team_names) > opponent_team else "N/A",
        "From (O)": locations[opponent_team] if len(locations) > opponent_team else "N/A",
        "Score": score_text or "N/A",
        "Ends": ends_text
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
                parsed_data = []
            for _, row in results_df.iterrows():
                raw_html = row[selected_round]
                if pd.notna(raw_html):
                    parsed_data.append(parse_matchup_html(raw_html))
                else:
                    parsed_data.append({
                        "Challenger": "N/A",
                        "From (C)": "N/A",
                        "Opponent": "N/A",
                        "From (O)": "N/A",
                        "Score": "N/A",
                        "Ends": "N/A"
                    })

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
