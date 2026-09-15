import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Maç Analizi AI",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Maç Analizi AI")
st.caption(
    "Takımların geçmiş performanslarını karşılaştıran "
    "istatistiksel analiz uygulaması."
)

API_URL = "https://api.football-data.org/v4"


# =========================================================
# API FONKSİYONLARI
# =========================================================

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


# Tek maçın ayrıntılı istatistiklerini alır
@st.cache_data(ttl=900)
def get_match_details(token, match_id):
    r = requests.get(
        f"{API_URL}/matches/{match_id}",
        headers={"X-Auth-Token": token},
        timeout=15
    )
    r.raise_for_status()
    return r.json()


# =========================================================
# TAKIM GOL İSTATİSTİKLERİ
# =========================================================

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


# =========================================================
# TAKIM GENEL ANALİZİ
# =========================================================

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
        3 if x == "G"
        else 1 if x == "B"
        else 0
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


# =========================================================
# ŞUT İSTATİSTİKLERİ
# =========================================================

def get_shot_stats(token, matches, team_id, limit=5):

    rows = []

    # API limitini zorlamamak için son 5 maç
    for m in matches[:limit]:

        try:

            detail = get_match_details(
                token,
                m["id"]
            )

            home_team = detail["homeTeam"]
            away_team = detail["awayTeam"]

            if home_team["id"] == team_id:

                team = home_team
                opponent = away_team
                venue = "Ev"

            elif away_team["id"] == team_id:

                team = away_team
                opponent = home_team
                venue = "Deplasman"

            else:
                continue

            team_statistics = team.get(
                "statistics",
                {}
            )

            opponent_statistics = opponent.get(
                "statistics",
                {}
            )

            shots = team_statistics.get(
                "shots"
            )

            shots_on_target = team_statistics.get(
                "shots_on_goal"
            )

            shots_off_target = team_statistics.get(
                "shots_off_goal"
            )

            opponent_shots = opponent_statistics.get(
                "shots"
            )

            # Şut verisi yoksa bu maçı atla
            if shots is None:
                continue

            rows.append({
                "Tarih": detail["utcDate"][:10],
                "Rakip": opponent["name"],
                "Saha": venue,
                "Şut": shots,
                "İsabetli Şut": shots_on_target or 0,
                "İsabetsiz Şut": shots_off_target or 0,
                "Rakip Şut": opponent_shots or 0
            })

        except Exception:
            continue

    return pd.DataFrame(rows)


def calculate_shot_summary(df):

    if df.empty:

        return {
            "mac": 0,
            "sut_ort": 0,
            "isabetli_ort": 0,
            "isabetsiz_ort": 0,
            "rakip_sut_ort": 0,
            "isabet_orani": 0
        }

    total_shots = df["Şut"].sum()
    total_on_target = df["İsabetli Şut"].sum()

    return {
        "mac": len(df),

        "sut_ort": round(
            df["Şut"].mean(),
            2
        ),

        "isabetli_ort": round(
            df["İsabetli Şut"].mean(),
            2
        ),

        "isabetsiz_ort": round(
            df["İsabetsiz Şut"].mean(),
            2
        ),

        "rakip_sut_ort": round(
            df["Rakip Şut"].mean(),
            2
        ),

        "isabet_orani": round(
            (total_on_target / total_shots) * 100,
            1
        ) if total_shots > 0 else 0
    }


# =========================================================
# API ANAHTARI
# =========================================================

st.sidebar.header("⚙️ Ayarlar")

token = st.sidebar.text_input(
    "Football-Data API anahtarı",
    type="password",
    help="Football-Data.org API anahtarını buraya gir."
)

if not token:

    st.info(
        "Başlamak için sol taraftaki API anahtarını gir."
    )

    st.stop()


# =========================================================
# LİGLER
# =========================================================

try:

    competitions = get_competitions(token)

except Exception:

    st.error(
        "API anahtarı geçersiz olabilir veya API'ye ulaşılamadı."
    )

    st.stop()


competition_names = {
    c["name"]: c["code"]
    for c in competitions
}


selected_competition_name = st.selectbox(
    "Lig",
    list(competition_names.keys())
)

competition_code = competition_names[
    selected_competition_name
]


# =========================================================
# TAKIMLAR
# =========================================================

try:

    teams = get_teams(
        token,
        competition_code
    )

except Exception:

    st.error(
        "Bu ligdeki takımlar alınamadı."
    )

    st.stop()


team_names = {
    t["name"]: t["id"]
    for t in teams
}


if len(team_names) < 2:

    st.warning(
        "Bu ligde yeterli takım bulunamadı."
    )

    st.stop()


# =========================================================
# TAKIM SEÇİMİ
# =========================================================

col1, col2 = st.columns(2)


with col1:

    team1_name = st.selectbox(
        "1. Takım",
        list(team_names.keys()),
        index=0
    )


with col2:

    team2_options = [
        x
        for x in team_names.keys()
        if x != team1_name
    ]

    team2_name = st.selectbox(
        "2. Takım",
        team2_options,
        index=0
    )


team1_id = team_names[team1_name]
team2_id = team_names[team2_name]


# =========================================================
# MAÇLARI GETİR
# =========================================================

try:

    matches1 = get_matches(
        token,
        team1_id,
        20
    )

    matches2 = get_matches(
        token,
        team2_id,
        20
    )

except Exception:

    st.error(
        "Maç verileri alınamadı."
    )

    st.stop()


df1 = team_stats(
    matches1,
    team1_id
)

df2 = team_stats(
    matches2,
    team2_id
)


stats1 = analyze_team(
    team1_name,
    df1
)

stats2 = analyze_team(
    team2_name,
    df2
)


# =========================================================
# ŞUT VERİLERİNİ GETİR
# =========================================================

shot_df1 = get_shot_stats(
    token,
    matches1,
    team1_id,
    5
)

shot_df2 = get_shot_stats(
    token,
    matches2,
    team2_id,
    5
)


shot1 = calculate_shot_summary(
    shot_df1
)

shot2 = calculate_shot_summary(
    shot_df2
)


# =========================================================
# BAŞLIK
# =========================================================

st.divider()

st.header(
    f"⚽ {team1_name} vs {team2_name}"
)


# =========================================================
# GENEL FORM
# =========================================================

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


# =========================================================
# GOL KARŞILAŞTIRMASI
# =========================================================

st.divider()

st.subheader(
    "📊 Gol Karşılaştırması"
)


chart_data = pd.DataFrame({

    "Takım": [
        team1_name,
        team2_name
    ],

    "Atılan Gol": [
        stats1["gf"],
        stats2["gf"]
    ],

    "Yenilen Gol": [
        stats1["ga"],
        stats2["ga"]
    ]
})


st.bar_chart(
    chart_data.set_index("Takım")
)


# =========================================================
# DETAYLI İSTATİSTİKLER
# =========================================================

st.divider()

st.subheader(
    "📈 Detaylı İstatistikler"
)


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


# =========================================================
# ŞUT İSTATİSTİKLERİ
# =========================================================

st.divider()

st.subheader(
    "🎯 Şut İstatistikleri"
)


col1, col2 = st.columns(2)


with col1:

    st.subheader(team1_name)

    st.metric(
        "Maç Başına Şut",
        shot1["sut_ort"]
    )

    st.metric(
        "Maç Başına İsabetli Şut",
        shot1["isabetli_ort"]
    )

    st.metric(
        "Maç Başına İsabetsiz Şut",
        shot1["isabetsiz_ort"]
    )

    st.metric(
        "Şut İsabet Oranı",
        f'%{shot1["isabet_orani"]}'
    )

    st.metric(
        "Rakibe Verilen Şut",
        shot1["rakip_sut_ort"]
    )


with col2:

    st.subheader(team2_name)

    st.metric(
        "Maç Başına Şut",
        shot2["sut_ort"]
    )

    st.metric(
        "Maç Başına İsabetli Şut",
        shot2["isabetli_ort"]
    )

    st.metric(
        "Maç Başına İsabetsiz Şut",
        shot2["isabetsiz_ort"]
    )

    st.metric(
        "Şut İsabet Oranı",
        f'%{shot2["isabet_orani"]}'
    )

    st.metric(
        "Rakibe Verilen Şut",
        shot2["rakip_sut_ort"]
    )


# =========================================================
# ŞUT KARŞILAŞTIRMASI
# =========================================================

if not shot_df1.empty or not shot_df2.empty:

    st.subheader(
        "📊 Şut Karşılaştırması"
    )

    shot_comparison = pd.DataFrame({

        "İstatistik": [

            "Maç Başına Şut",
            "Maç Başına İsabetli Şut",
            "Maç Başına İsabetsiz Şut",
            "Rakibe Verilen Şut",
            "Şut İsabet Oranı"

        ],

        team1_name: [

            shot1["sut_ort"],
            shot1["isabetli_ort"],
            shot1["isabetsiz_ort"],
            shot1["rakip_sut_ort"],
            f'%{shot1["isabet_orani"]}'

        ],

        team2_name: [

            shot2["sut_ort"],
            shot2["isabetli_ort"],
            shot2["isabetsiz_ort"],
            shot2["rakip_sut_ort"],
            f'%{shot2["isabet_orani"]}'

        ]
    })


    st.dataframe(
        shot_comparison,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # SON 5 MAÇ ŞUT GRAFİĞİ
    # =====================================================

    st.subheader(
        "📈 Son 5 Maç Şut Grafiği"
    )


    graph_rows = []


    for _, row in shot_df1.iterrows():

        graph_rows.append({

            "Tarih": row["Tarih"],
            "Takım": team1_name,
            "Şut": row["Şut"]

        })


    for _, row in shot_df2.iterrows():

        graph_rows.append({

            "Tarih": row["Tarih"],
            "Takım": team2_name,
            "Şut": row["Şut"]

        })


    if graph_rows:

        shot_graph = pd.DataFrame(
            graph_rows
        )

        st.line_chart(
            shot_graph,
            x="Tarih",
            y="Şut",
            color="Takım"
        )


else:

    st.info(
        "Bu maçlar için şut istatistikleri "
        "API tarafından sağlanamadı."
    )


# =========================================================
# ŞUT VERİLERİNİN MAÇ MAÇ GÖSTERİLMESİ
# =========================================================

if not shot_df1.empty or not shot_df2.empty:

    st.subheader(
        "📋 Son 5 Maç Şut Detayları"
    )

    col1, col2 = st.columns(2)


    with col1:

        st.write(
            f"**{team1_name}**"
        )

        if not shot_df1.empty:

            st.dataframe(
                shot_df1,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Şut verisi bulunamadı."
            )


    with col2:

        st.write(
            f"**{team2_name}**"
        )

        if not shot_df2.empty:

            st.dataframe(
                shot_df2,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Şut verisi bulunamadı."
            )


# =========================================================
# ŞUT İSTATİSTİKLERİNE DAYALI AÇIKLAMA
# =========================================================

st.divider()

st.subheader(
    "🧠 Şut Analizi"
)


if not shot_df1.empty and not shot_df2.empty:

    if shot1["sut_ort"] > shot2["sut_ort"]:

        st.write(
            f"• Son 5 maçta **{team1_name}**, "
            f"maç başına ortalama "
            f"**{shot1['sut_ort']} şut** ile "
            f"{team2_name}'den daha fazla şut üretmiş."
        )

    elif shot2["sut_ort"] > shot1["sut_ort"]:

        st.write(
            f"• Son 5 maçta **{team2_name}**, "
            f"maç başına ortalama "
            f"**{shot2['sut_ort']} şut** ile "
            f"{team1_name}'den daha fazla şut üretmiş."
        )

    else:

        st.write(
            "• İki takımın maç başına şut ortalamaları eşit."
        )


    if shot1["isabetli_ort"] > shot2["isabetli_ort"]:

        st.write(
            f"• **{team1_name}** isabetli şut "
            f"ortalamasında daha yüksek."
        )

    elif shot2["isabetli_ort"] > shot1["isabetli_ort"]:

        st.write(
            f"• **{team2_name}** isabetli şut "
            f"ortalamasında daha yüksek."
        )

    else:

        st.write(
            "• İki takımın isabetli şut ortalamaları birbirine eşit."
        )


    if shot1["isabet_orani"] > shot2["isabet_orani"]:

        st.write(
            f"• Şut isabet oranı **{team1_name}** lehine daha yüksek."
        )

    elif shot2["isabet_orani"] > shot1["isabet_orani"]:

        st.write(
            f"• Şut isabet oranı **{team2_name}** lehine daha yüksek."
        )

    else:

        st.write(
            "• İki takımın şut isabet oranları eşit."
        )


    if shot1["rakip_sut_ort"] < shot2["rakip_sut_ort"]:

        st.write(
            f"• Rakibe daha az şut verme açısından "
            f"**{team1_name}** daha iyi görünüyor."
        )

    elif shot2["rakip_sut_ort"] < shot1["rakip_sut_ort"]:

        st.write(
            f"• Rakibe daha az şut verme açısından "
            f"**{team2_name}** daha iyi görünüyor."
        )

    else:

        st.write(
            "• İki takımın rakibe verdiği şut ortalamaları eşit."
        )

else:

    st.info(
        "Şut analizi için yeterli maç verisi bulunamadı."
    )


# =========================================================
# BASİT GENEL ANALİZ
# =========================================================

st.divider()

st.subheader(
    "🧠 Genel Analiz Sonucu"
)


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


if shot1["sut_ort"] > shot2["sut_ort"]:

    score1 += 1

elif shot2["sut_ort"] > shot1["sut_ort"]:

    score2 += 1


if shot1["isabetli_ort"] > shot2["isabetli_ort"]:

    score1 += 1

elif shot2["isabetli_ort"] > shot1["isabetli_ort"]:

    score2 += 1


if score1 > score2:

    st.success(
        f"{team1_name} son maç verilerinde "
        f"daha güçlü görünüyor."
    )

elif score2 > score1:

    st.success(
        f"{team2_name} son maç verilerinde "
        f"daha güçlü görünüyor."
    )

else:

    st.info(
        "İki takımın geçmiş istatistikleri "
        "birbirine oldukça yakın görünüyor."
    )


st.caption(
    "Bu sonuç yalnızca geçmiş istatistiklere dayalı "
    "basit bir karşılaştırmadır; maç sonucunu garanti etmez."
)


# =========================================================
# SON MAÇLAR
# =========================================================

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

        st.info(
            "Maç verisi bulunamadı."
        )


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

        st.info(
            "Maç verisi bulunamadı."
        )


# =========================================================
# EV / DEPLASMAN
# =========================================================

st.divider()

st.subheader(
    "🏠 İç Saha / Deplasman Performansı"
)


def venue_stats(df):

    if df.empty:

        return pd.DataFrame()

    result = []


    for venue in ["Ev", "Deplasman"]:

        part = df[
            df["Saha"] == venue
        ]

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

    st.write(
        f"**{team1_name}**"
    )

    if not venue1.empty:

        st.dataframe(
            venue1,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Yeterli veri bulunamadı."
        )


with col2:

    st.write(
        f"**{team2_name}**"
    )

    if not venue2.empty:

        st.dataframe(
            venue2,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Yeterli veri bulunamadı."
        )


# =========================================================
# H2H
# =========================================================

st.divider()

st.subheader(
    "🆚 Birbirleriyle Oynadıkları Maçlar"
)


try:

    h2h_response = requests.get(

        f"{API_URL}/teams/{team1_id}/matches",

        headers={
            "X-Auth-Token": token
        },

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

                "Ev Sahibi":
                    m["homeTeam"]["name"],

                "Deplasman":
                    m["awayTeam"]["name"],

                "Skor": (
                    f'{m["score"]["fullTime"]["home"]}'
                    f' - '
                    f'{m["score"]["fullTime"]["away"]}'
                )
            })


    if h2h_rows:

        h2h_df = pd.DataFrame(
            h2h_rows
        )


        st.dataframe(

            h2h_df,

            use_container_width=True,

            hide_index=True

        )

    else:

        st.info(
            "Mevcut API verileri içerisinde "
            "bu iki takımın yakın dönem karşılaşması "
            "bulunamadı."
        )


except Exception:

    st.info(
        "İki takımın geçmiş karşılaşmaları "
        "şu anda alınamadı."
    )


# =========================================================
# ALT BİLGİ
# =========================================================

st.divider()

st.caption(
    "⚽ Futbol verileri Football-Data.org API üzerinden alınmaktadır."
)

st.caption(
    "Bu uygulama istatistiksel maç analizi içindir; "
    "bahis veya garanti edilmiş maç tahmini sunmaz."
)
