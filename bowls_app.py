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

def extract_name_and_location(text):
    name = text.split('(')[0].strip()
    location = text[text.find('(')+1:text.rfind(')')].strip()
    return name, location

def parse_matchup(matchup):
    original_text = matchup  # Keep the original text for debugging

    # First, extract and save the 'Ends:' value (if it exists)
    ends_match = re.search(r"Ends:\s*(\d+)", matchup)
    ends = "N/A"
    if ends_match:
        ends = ends_match.group(1)
        # Remove the 'Ends' part from the matchup string
        matchup = re.sub(r"Ends:\s*\d+", "", matchup)

    # Extract the score (if it exists) but do not remove it
    score_match = re.search(r"(\d+)\s*-\s*(\d+)", matchup)
    score = "No Score"
    if score_match:
        score = f"{score_match.group(1)} - {score_match.group(2)}"

    # Now, depending on the presence of the score, we split
    if score != "No Score":
        # Split by score first (if score exists) and keep the score
        parts = matchup.split(score, 1)
    elif "V" in matchup:
        # If there's no score, use 'V' as delimiter
        parts = matchup.split("V", 1)
    elif "W/O" in matchup:
        # If there's no score and no 'V', use 'W/O' as delimiter (Walkover)
        parts = matchup.split("W/O", 1)
    else:
        # If none of the above, it's an invalid format
        return {"Full Text": original_text, "Challenger": "Invalid", "From (C)": "Invalid", "Opponent": "Invalid", "From (O)": "Invalid", "Score": "Invalid", "Ends": "Invalid"}

    # Clean up the parts and ensure both parts exist
    part_1 = parts[0].strip()
    part_2 = parts[1].strip() if len(parts) > 1 else ""

    # Identify the Challenger and Opponent
    clean_part_1 = part_1.replace("(Challenger)", "").strip()
    clean_part_2 = part_2.replace("(Challenger)", "").strip()

    if "(Challenger)" in part_1:
        challenger = clean_part_1.split('(')[0].strip()
        from_challenger = clean_part_1[clean_part_1.find('(')+1 : clean_part_1.rfind(')')].strip()
        if "BYE" not in part_2:
            opponent = clean_part_2.split('(')[0].strip()
            from_opponent = clean_part_2[clean_part_2.find('(')+1 : clean_part_2.rfind(')')].strip()
        else:
            opponent = "BYE"
            from_opponent = "N/A"

    elif "(Challenger)" in part_2:
        if "BYE" not in part_2:
            challenger = clean_part_2.split('(')[0].strip()
            from_challenger = clean_part_2[clean_part_2.find('(')+1 : clean_part_2.rfind(')')].strip()
            opponent = clean_part_1.split('(')[0].strip()
            from_opponent = clean_part_1[clean_part_1.find('(')+1 : clean_part_1.rfind(')')].strip()
        else:
            challenger = clean_part_2.split('(')[0].strip()
            from_challenger = clean_part_1[clean_part_1.find('(')+1 : clean_part_1.rfind(')')].strip()
            opponent = "BYE"
            from_opponent = "N/A"

    else:
        # If no challenger marked, assume left side is opponent and right side is challenger
        opponent = clean_part_1.split('(')[0].strip()
        from_opponent = clean_part_1[clean_part_1.find('(')+1 : clean_part_1.rfind(')')].strip()
        challenger = clean_part_2.split('(')[0].strip()
        from_challenger = clean_part_2[clean_part_2.find('(')+1 : clean_part_2.rfind(')')].strip()


    # Reverse the score if the challenger is in the second part
    if "(Challenger)" in part_2 and score != "No Score":
        score = reverse_score(score)

    return {
        "Full Text": original_text,
        "Challenger": challenger,
        "From (C)": from_challenger,
        "Opponent": opponent,
        "From (O)": from_opponent,
        "Score": score,
        "Ends": ends
    }

def reverse_score(score):
    """Reverse the score if the challenger is in the second part of the string."""
    if score != "No Score":
        parts = score.split(" - ")
        return f"{parts[1]} - {parts[0]}"
    return score

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
                selected_column = results_df[selected_round].dropna()
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
