import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Maç Analiz AI", page_icon="⚽", layout="wide")

st.title("⚽ Maç Analiz AI")
st.caption("Takımların geçmiş performanslarını karşılaştıran ücretsiz ilk sürüm.")

API_URL = "https://api.football-data.org/v4"

@st.cache_data(ttl=900)
def get_competitions(token):
    r = requests.get(f"{API_URL}/competitions", headers={"X-Auth-Token": token}, timeout=15)
    r.raise_for_status()
    return r.json()["competitions"]

@st.cache_data(ttl=900)
def get_teams(token, competition_code):
    r = requests.get(f"{API_URL}/competitions/{competition_code}/teams",
                     headers={"X-Auth-Token": token}, timeout=15)
    r.raise_for_status()
    return r.json()["teams"]

@st.cache_data(ttl=900)
def get_matches(token, team_id, limit=20):
    r = requests.get(f"{API_URL}/teams/{team_id}/matches",
                     headers={"X-Auth-Token": token},
                     params={"status": "FINISHED", "limit": limit},
                     timeout=15)
    r.raise_for_status()
    return r.json()["matches"]

def team_stats(matches, team_id):
    rows = []
    for m in matches:
        home = m["homeTeam"]["id"] == team_id
        gf = m["score"]["fullTime"]["home"] if home else m["score"]["fullTime"]["away"]
        ga = m["score"]["fullTime"]["away"] if home else m["score"]["fullTime"]["home"]
        result = "G" if gf > ga else ("B" if gf == ga else "M")
        rows.append({
            "Tarih": m["utcDate"][:10],
            "Rakip": m["awayTeam"]["name"] if home else m["homeTeam"]["name"],
            "GF": gf, "GA": ga, "Sonuç": result,
            "Ev/Dep": "Ev" if home else "Dep"
        })
    return pd.DataFrame(rows)

def analyze(name, df):
    if df.empty:
        return {"name": name, "form": "-", "puan": 0, "gf": 0, "ga": 0, "mac": 0}
    points = sum(3 if x=="G" else 1 if x=="B" else 0 for x in df["Sonuç"])
    return {
        "name": name,
        "form": "".join(df["Sonuç"].tolist()[:5]),
        "puan": points,
        "gf": int(df["GF"].sum()),
        "ga": int(df["GA"].sum()),
        "mac": len(df)
    }

st.sidebar.header("⚙️ Ayarlar")
token = st.sidebar.text_input("Football-Data API anahtarı", type="password",
                              help="Ücretsiz API anahtarını football-data.org hesabından alabilirsin.")

if not token:
    st.info("Başlamak için sol taraftaki API anahtarını gir.")
    st.markdown("""
### Bu sürüm ne yapıyor?
- Lig seçimi
- Takım seçimi
- Son maçları çekme
- Son 5 maç formu
- Atılan / yenilen gol
- Basit karşılaştırma ve otomatik analiz

**Not:** Bu uygulama bahis/tahmin sistemi değildir; istatistiksel maç analizi yapar.
""")
    st.stop()

try:
    competitions = get_competitions(token)
    preferred = ["Süper Lig", "Premier League", "La Liga", "Serie A", "Bundesliga", "UEFA Champions League"]
    names = [c["name"] for c in competitions]
    ordered = [x for x in preferred if x in names] + [x for x in names if x not in preferred]
    selected_name = st.selectbox("Lig", ordered)
    comp = next(c for c in competitions if c["name"] == selected_name)

    teams = get_teams(token, comp["code"])
    team_names = sorted([t["name"] for t in teams])

    c1, c2 = st.columns(2)
    home_name = c1.selectbox("1. Takım", team_names, index=0)
    away_name = c2.selectbox("2. Takım", team_names, index=min(1, len(team_names)-1))

    if home_name == away_name:
        st.warning("İki farklı takım seç.")
        st.stop()

    home_team = next(t for t in teams if t["name"] == home_name)
    away_team = next(t for t in teams if t["name"] == away_name)

    if st.button("🔎 MAÇI ANALİZ ET", use_container_width=True):
        with st.spinner("Maç verileri analiz ediliyor..."):
            h_matches = get_matches(token, home_team["id"])
            a_matches = get_matches(token, away_team["id"])
            hdf = team_stats(h_matches, home_team["id"])
            adf = team_stats(a_matches, away_team["id"])
            hs = analyze(home_name, hdf)
            a_s = analyze(away_name, adf)

        st.subheader(f"{home_name}  vs  {away_name}")

        cols = st.columns(2)
        for col, s in zip(cols, [hs, a_s]):
            with col:
                st.markdown(f"### {s['name']}")
                st.metric("Son 5 form", s["form"])
                st.metric("Toplam puan", s["puan"])
                st.metric("Gol", f"{s['gf']} - {s['ga']}")

        st.divider()

        h_score = hs["puan"] + (hs["gf"] - hs["ga"])
        a_score = a_s["puan"] + (a_s["gf"] - a_s["ga"])

        if h_score > a_score:
            verdict = f"{home_name} son maç verilerinde daha güçlü görünüyor."
        elif a_score > h_score:
            verdict = f"{away_name} son maç verilerinde daha güçlü görünüyor."
        else:
            verdict = "İki takımın son maç verileri birbirine yakın."

        st.success("📊 Analiz sonucu")
        st.write(verdict)
        st.caption("Bu sonuç geçmiş istatistiklere dayalı basit bir karşılaştırmadır; maç sonucunu garanti etmez.")

        t1, t2 = st.columns(2)
        with t1:
            st.write(f"**{home_name} son maçları**")
            st.dataframe(hdf, use_container_width=True, hide_index=True)
        with t2:
            st.write(f"**{away_name} son maçları**")
            st.dataframe(adf, use_container_width=True)

except requests.HTTPError as e:
    st.error("API isteği başarısız oldu. API anahtarını ve günlük istek limitini kontrol et.")
except Exception as e:
    st.error(f"Bir hata oluştu: {e}")
