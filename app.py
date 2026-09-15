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
        "Atılan - Yenilen Gol",
        f'{stats1["gf"]} - {stats1["ga"]}'
    )

with col2:
    st.subheader(team2_name)

    st.metric(
        "Son 5 Form",
        stats2["form"]
    )

    st.metric(
        "Toplam Puan",
        stats2["puan"]
    )

    st.metric(
        "Atılan - Yenilen Gol",
        f'{stats2["gf"]} - {stats2["ga"]}'
    )


# Gol karşılaştırması
st.divider()

st.subheader("📊 Gol Karşılaştırması")

chart_data = pd.DataFrame({
    "Takım": [team1_name, team2_name],
    "Atılan Gol": [stats1["gf"], stats2["gf"]],
    "Yenilen Gol": [stats1["ga"], stats2["ga"]]
})

st.bar_chart(
    chart_data.set_index("Takım")
)


# Detaylı istatistikler
st.divider()

st.subheader("📈 Detaylı İstatistikler")

comparison = pd.DataFrame({
    "İstatistik": [
        "Maç",
        "Galibiyet",
        "Beraberlik",
        "Mağlubiyet",
        "Atılan Gol",
        "Yenilen Gol",
        "Maç Başına Atılan Gol",
        "Maç Başına Yenilen Gol"
    ],

    team1_name: [
        stats1["mac"],
        stats1["galibiyet"],
        stats1["beraberlik"],
        stats1["maglubiyet"],
        stats1["gf"],
        stats1["ga"],
        stats1["gol_ort"],
        stats1["yenen_ort"]
    ],

    team2_name: [
        stats2["mac"],
        stats2["galibiyet"],
        stats2["beraberlik"],
        stats2["maglubiyet"],
        stats2["gf"],
        stats2["ga"],
        stats2["gol_ort"],
        stats2["yenen_ort"]
    ]
})

st.dataframe(
    comparison,
    use_container_width=True,
    hide_index=True
)


# Basit analiz
st.divider()

st.subheader("🧠 Analiz Sonucu")

score1 = 0
score2 = 0

if stats1["puan"] > stats2["puan"]:
    score1 += 1
elif stats2["puan"] > stats1["puan"]:
    score2 += 1

if stats1["gf"] > stats2["gf"]:
    score1 += 1
elif stats2["gf"] > stats1["gf"]:
    score2 += 1

if stats1["ga"] < stats2["ga"]:
    score1 += 1
elif stats2["ga"] < stats1["ga"]:
    score2 += 1

if stats1["gol_ort"] > stats2["gol_ort"]:
    score1 += 1
elif stats2["gol_ort"] > stats1["gol_ort"]:
    score2 += 1


if score1 > score2:
    st.success(
        f"{team1_name} son maç verilerinde daha güçlü görünüyor."
    )

elif score2 > score1:
    st.success(
        f"{team2_name} son maç verilerinde daha güçlü görünüyor."
    )

else:
    st.info(
        "İki takımın geçmiş istatistikleri birbirine oldukça yakın görünüyor."
    )


st.caption(
    "Bu sonuç yalnızca geçmiş istatistiklere dayalı basit bir karşılaştırmadır; maç sonucunu garanti etmez."
)


# Son maçlar
st.divider()

col1, col2 = st.columns(2)

with col1:

    st.subheader(
        f"📋 {team1_name} Son Maçları"
    )

    if not df1.empty:
        st.dataframe(
            df1.head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Maç verisi bulunamadı.")


with col2:

    st.subheader(
        f"📋 {team2_name} Son Maçları"
    )

    if not df2.empty:
        st.dataframe(
            df2.head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Maç verisi bulunamadı.")


# Ev / Deplasman
st.divider()

st.subheader("🏠 İç Saha / Deplasman Performansı")


def venue_stats(df):

    if df.empty:
        return pd.DataFrame()

    result = []

    for venue in ["Ev", "Deplasman"]:

        part = df[df["Saha"] == venue]

        if len(part) == 0:
            continue

        result.append({
            "Saha": venue,
            "Maç": len(part),
            "Galibiyet": int(
                (part["Sonuç"] == "G").sum()
            ),
            "Beraberlik": int(
                (part["Sonuç"] == "B").sum()
            ),
            "Mağlubiyet": int(
                (part["Sonuç"] == "M").sum()
            ),
            "Atılan Gol": int(
                part["GF"].sum()
            ),
            "Yenilen Gol": int(
                part["GA"].sum()
            )
        })

    return pd.DataFrame(result)


venue1 = venue_stats(df1)
venue2 = venue_stats(df2)


col1, col2 = st.columns(2)

with col1:

    st.write(f"**{team1_name}**")

    if not venue1.empty:
        st.dataframe(
            venue1,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Yeterli veri bulunamadı.")


with col2:

    st.write(f"**{team2_name}**")

    if not venue2.empty:
        st.dataframe(
            venue2,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Yeterli veri bulunamadı.")


# H2H
st.divider()

st.subheader("🆚 Birbirleriyle Oynadıkları Maçlar")

try:

    h2h_response = requests.get(
        f"{API_URL}/teams/{team1_id}/matches",
        headers={"X-Auth-Token": token},
        params={
            "status": "FINISHED",
            "limit": 100
        },
        timeout=15
    )

    h2h_response.raise_for_status()

    h2h_matches = h2h_response.json()["matches"]

    h2h_rows = []

    for m in h2h_matches:

        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]

        if {home_id, away_id} == {
            team1_id,
            team2_id
        }:

            h2h_rows.append({
                "Tarih": m["utcDate"][:10],
                "Ev Sahibi": m["homeTeam"]["name"],
                "Deplasman": m["awayTeam"]["name"],
                "Skor": (
                    f'{m["score"]["fullTime"]["home"]}'
                    f' - '
                    f'{m["score"]["fullTime"]["away"]}'
                )
            })

    if h2h_rows:

        h2h_df = pd.DataFrame(h2h_rows)

        st.dataframe(
            h2h_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Mevcut API verileri içerisinde "
            "bu iki takımın yakın dönem karşılaşması bulunamadı."
        )

except Exception:

    st.info(
        "İki takımın geçmiş karşılaşmaları şu anda alınamadı."
    )


# Alt bilgi
st.divider()

st.caption(
    "⚽ Futbol verileri Football-Data.org API üzerinden alınmaktadır."
)

st.caption(
    "Bu uygulama istatistiksel maç analizi içindir; "
    "bahis veya garanti edilmiş maç tahmini sunmaz."
)
