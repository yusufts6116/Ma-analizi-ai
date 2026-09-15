import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Maç Analizi AI",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Maç Analizi AI")
st.caption("Takımların geçmiş performanslarını karşılaştıran istatistiksel analiz uygulaması.")

API_URL = "https://api.football-data.org/v4"


@st.cache_data(ttl=900)
def get_competitions(token):
    r = requests.get(
        f"{API_URL}/competitions",
        headers={"X-Auth-Token": token},
        timeout=15
    )
    r.raise_for_status()
    return r.json()["competitions"]


@st.cache_data(ttl=900)
def get_teams(token, competition_code):
    r = requests.get(
        f"{API_URL}/competitions/{competition_code}/teams",
        headers={"X-Auth-Token": token},
        timeout=15
    )
    r.raise_for_status()
    return r.json()["teams"]


@st.cache_data(ttl=900)
def get_matches(token, team_id, limit=20):
    r = requests.get(
        f"{API_URL}/teams/{team_id}/matches",
        headers={"X-Auth-Token": token},
        params={
            "status": "FINISHED",
            "limit": limit
        },
        timeout=15
    )
    r.raise_for_status()
    return r.json()["matches"]


def team_stats(matches, team_id):
    rows = []

    for m in matches:
        home = m["homeTeam"]["id"] == team_id

        if home:
            gf = m["score"]["fullTime"]["home"]
            ga = m["score"]["fullTime"]["away"]
            opponent = m["awayTeam"]["name"]
            location = "Ev"
        else:
            gf = m["score"]["fullTime"]["away"]
            ga = m["score"]["fullTime"]["home"]
            opponent = m["homeTeam"]["name"]
            location = "Deplasman"

        if gf is None or ga is None:
            continue

        if gf > ga:
            result = "G"
        elif gf == ga:
            result = "B"
        else:
            result = "M"

        rows.append({
            "Tarih": m["utcDate"][:10],
            "Rakip": opponent,
            "GF": gf,
            "GA": ga,
            "Sonuç": result,
            "Saha": location
        })

    return pd.DataFrame(rows)


def analyze_team(name, df):
    if df.empty:
        return {
            "name": name,
            "form": "-",
            "puan": 0,
            "gf": 0,
            "ga": 0,
            "mac": 0,
            "galibiyet": 0,
            "beraberlik": 0,
            "maglubiyet": 0,
            "gol_ort": 0,
            "yenen_ort": 0
        }

    points = sum(
        3 if x == "G" else 1 if x == "B" else 0
        for x in df["Sonuç"]
    )

    return {
        "name": name,
        "form": "".join(df["Sonuç"].tolist()[:5]),
        "puan": points,
        "gf": int(df["GF"].sum()),
        "ga": int(df["GA"].sum()),
        "mac": len(df),
        "galibiyet": int((df["Sonuç"] == "G").sum()),
        "beraberlik": int((df["Sonuç"] == "B").sum()),
        "maglubiyet": int((df["Sonuç"] == "M").sum()),
        "gol_ort": round(df["GF"].mean(), 2),
        "yenen_ort": round(df["GA"].mean(), 2)
    }


# API anahtarı
st.sidebar.header("⚙️ Ayarlar")

token = st.sidebar.text_input(
    "Football-Data API anahtarı",
    type="password",
    help="Football-Data.org API anahtarını buraya gir."
)

if not token:
    st.info("Başlamak için sol taraftaki API anahtarını gir.")
    st.stop()


# Ligleri getir
try:
    competitions = get_competitions(token)
except Exception:
    st.error("API anahtarı geçersiz olabilir veya API'ye ulaşılamadı.")
    st.stop()


competition_names = {
    c["name"]: c["code"]
    for c in competitions
}

selected_competition_name = st.selectbox(
    "Lig",
    list(competition_names.keys())
)

competition_code = competition_names[selected_competition_name]


# Takımları getir
try:
    teams = get_teams(token, competition_code)
except Exception:
    st.error("Bu ligdeki takımlar alınamadı.")
    st.stop()


team_names = {
    t["name"]: t["id"]
    for t in teams
}

if len(team_names) < 2:
    st.warning("Bu ligde yeterli takım bulunamadı.")
    st.stop()


# Takım seçimi
col1, col2 = st.columns(2)

with col1:
    team1_name = st.selectbox(
        "1. Takım",
        list(team_names.keys()),
        index=0
    )

with col2:
    team2_options = [
        x for x in team_names.keys()
        if x != team1_name
    ]

    team2_name = st.selectbox(
        "2. Takım",
        team2_options,
        index=0
    )


team1_id = team_names[team1_name]
team2_id = team_names[team2_name]


# Maçları getir
try:
    matches1 = get_matches(token, team1_id, 20)
    matches2 = get_matches(token, team2_id, 20)
except Exception:
    st.error("Maç verileri alınamadı.")
    st.stop()


df1 = team_stats(matches1, team1_id)
df2 = team_stats(matches2, team2_id)

stats1 = analyze_team(team1_name, df1)
stats2 = analyze_team(team2_name, df2)


# Başlık
st.divider()

st.header(
    f"⚽ {team1_name} vs {team2_name}"
)


# Genel form
col1, col2 = st.columns(2)

with col1:
    st.subheader(team1_name)

    st.metric(
        "Son 5 Form",
        stats1["form"]
    )

    st.metric(
        "Toplam Puan",
        stats1["puan"]
    )

    st.metric(
        "
