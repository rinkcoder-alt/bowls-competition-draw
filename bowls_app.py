import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# === FUNCTIONS ===

@st.cache_data
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

@st.cache_data
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

@st.cache_data
def fetch_results(competition_id, county_id):
    url = f"https://bowlsenglandcomps.com/competition/area-fixture/{competition_id}/{county_id}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", class_="table")
    if not table:
        return None, None
    headers = [th.text.strip() for th in table.find("thead").find_all("th")]
    rows = []
    for row in table.find("tbody").find_all("tr"):
        data = [str(td) for td in row.find_all("td")]
        rows.append(data)
    df = pd.DataFrame(rows, columns=headers)
    return df, headers

def parse_matchup_html(cell_html):
    soup = BeautifulSoup(cell_html, "html.parser")
    p = soup.find("p")
    if not p:
        return None

    spans = p.find_all("span")
    team_names = [s.get_text(strip=True) for s in spans if "team_name" in s.get("class", [])]
    locations = [s.get_text(strip=True) for s in spans if "team_name_line_2" in s.get("class", [])]
    scores = [s.get_text(strip=True) for s in spans if "fixture_result" in s.get("class", [])]
    challenger_index = next((i for i, s in enumerate(spans) if "challenger" in s.get("class", [])), None)
    team_name_indices = [i for i, s in enumerate(spans) if "team_name" in s.get("class", [])]

    # Check if we have valid teams
    if len(team_names) < 2:
        return None
    if all(name.upper() == "TBC" for name in team_names):
        return None

    # Determine challenger/opponent
    challenger_team = 0
    opponent_team = 1
    if challenger_index is not None and len(team_name_indices) >= 2:
        if challenger_index > team_name_indices[1]:
            challenger_team = 1
            opponent_team = 0

    ends_tag = p.find("small")
    ends_text = "N/A"
    if ends_tag:
        ends_text = ends_tag.get_text(strip=True).split(":")[-1].strip()

    return {
        "Challenger": team_names[challenger_team],
        "From (C)": locations[challenger_team] if len(locations) > challenger_team else "N/A",
        "Opponent": team_names[opponent_team],
        "From (O)": locations[opponent_team] if len(locations) > opponent_team else "N/A",
        "Score": scores[0] if scores else "N/A",
        "Ends": ends_text
    }


# === STREAMLIT UI ===

st.title("🏆 Bowls England Competition Viewer")

# User Inputs
season = st.selectbox("Season", ["2025", "2024", "2023"])
stage = st.selectbox("Stage", ["1 - Early Stages", "2 - National Finals"])
season_id = {"2025": "6", "2024": "5", "2023": "4"}[season]
stage_id = stage.split(" - ")[0]

comps = fetch_competitions(season_id, stage_id)
comp_name = st.selectbox("Competition", sorted(comps.keys()))
comp_id, comp_url = comps[comp_name]

counties = fetch_counties(comp_url)
county_name = st.selectbox("County", sorted(counties.keys()))
county_id = counties[county_name]

results_df, round_headers = fetch_results(comp_id, county_id)

if results_df is not None:
    round_choice = st.selectbox("Select Round", round_headers[1:])
    parsed_data = []
    for i, raw_html in enumerate(results_df[round_choice]):
        if pd.notna(raw_html):
            parsed = parse_matchup_html(raw_html)
            if parsed:  # Skip None returns
                parsed_data.append(parsed)


    parsed_df = pd.DataFrame(parsed_data)

    # === Filter out N/A Challenger ===
    parsed_df = parsed_df[parsed_df["Challenger"] != "N/A"]

    if not parsed_df.empty:
        st.dataframe(parsed_df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)
    else:
        st.info("No valid matchups to display for this round.")

    # === Optional Debugging ===
    if st.checkbox("🔍 Show Raw HTML for Debugging"):
        for i, raw_html in enumerate(results_df[round_choice]):
            st.markdown(f"**Row {i+1}:**")
            st.code(raw_html, language="html")

else:
    st.warning("⚠️ No results table found for this competition/county.")
