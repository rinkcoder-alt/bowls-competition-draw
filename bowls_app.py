import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Bowls England Draw Viewer")
st.title("Bowls England Competition Draw Viewer")

# --- Utility functions ---
def get_competitions(season: str, stage: str):
    url = f"https://bowlsenglandcomps.com/season/{season}/{stage}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    comps = soup.find_all("a", href=True)
    comp_dict = {}
    for a in comps:
        if "/competition/" in a['href'] and a.find("div", class_="pull-left competition-name"):
            name = a.find("div", class_="pull-left competition-name").get_text(strip=True).replace(">", "").strip()
            comp_id = a['href'].split("/")[-1]
            comp_dict[name] = comp_id
    return comp_dict

def get_counties(comp_id):
    url = f"https://bowlsenglandcomps.com/competition/{comp_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    areas = soup.find_all("a", class_="area-fixture-link")
    county_dict = {}
    for area in areas:
        name = area.get_text(strip=True)
        county_id = area['href'].split("/")[-1]
        county_dict[name] = county_id
    return county_dict

def get_results_table(comp_id, county_id):
    url = f"https://bowlsenglandcomps.com/competition/area-fixture/{comp_id}/{county_id}"
    st.markdown(f"[🔗 View Full Table]({url})")

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if table:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) == len(headers):
                rows.append(cells)
        df = pd.DataFrame(rows, columns=headers)
        return df
    else:
        return None

# --- UI ---
current_year = str(datetime.now().year)
year_options = ["2020", "2021", "2022", "2023", "2024", "2025"]
season_index = year_options.index(current_year) if current_year in year_options else len(year_options)-1
season = st.selectbox("Select Season", year_options, index=season_index)

stage = st.selectbox("Select Stage", {"Early Stages": "1", "Final Stages": "2"})

competitions = get_competitions(season, stage)
if not competitions:
    st.warning("No competitions found for this season and stage.")
    st.stop()

selected_competition = st.selectbox("Select Competition", list(competitions.keys()), index=0)
comp_id = competitions[selected_competition]

counties = get_counties(comp_id)
if not counties:
    st.warning("No counties found for this competition.")
    st.stop()

selected_county = st.selectbox("Select County", list(counties.keys()), index=0)
county_id = counties[selected_county]

# --- Results ---
results_df = get_results_table(comp_id, county_id)
if results_df is not None and not results_df.empty:
    round_options = results_df.columns[1:]  # Skip the matchup column
    selected_round = st.selectbox("Select Round", round_options)

    if selected_round in results_df.columns:
        st.dataframe(results_df[[selected_round]])
    else:
        st.warning(f"Round '{selected_round}' not found in the data.")
else:
    st.warning("No result table found for this selection.")
