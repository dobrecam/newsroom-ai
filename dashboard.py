
import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(
    page_title="Newsroom AI",
    page_icon="📰",
    layout="wide"
)

st.title("📰 NEWSROOM AI")
st.caption("Platformă independentă de monitorizare a presei")

@st.cache_data(ttl=300)
def incarca_stiri():
    fisier = Path("stiri_detectate.json")

    if not fisier.exists():
        return pd.DataFrame(), None

    with open(fisier, "r", encoding="utf-8") as f:
        date = json.load(f)

    articole = date.get("articole", [])
    df = pd.DataFrame(articole)

    if df.empty:
        return df, date

    for coloana in ["titlu", "link", "sursa", "data"]:
        if coloana not in df.columns:
            df[coloana] = ""

    df["data_publicarii"] = pd.to_datetime(
        df["data"], errors="coerce", utc=True
    )

    df = df.drop_duplicates(subset=["link"])
    df = df.sort_values(
        "data_publicarii", ascending=False
    )

    return df, date


def categorie(titlu):
    text = str(titlu).lower()

    categorii = {
        "Politică": [
            "psd", "pnl", "usr", "aur", "udmr",
            "guvern", "ministru", "parlament",
            "alegeri", "partid", "senator",
            "deputat", "premier"
        ],
        "Administrație": [
            "primărie", "primar", "prefect",
            "consiliul județean", "consilier",
            "administrație", "taxe locale"
        ],
        "Economie": [
            "economie", "investiție", "investiții",
            "afaceri", "salarii", "companie",
            "buget", "inflație"
        ],
        "Port și transporturi": [
            "portul", "portuar", "navă",
            "transport", "autostradă",
            "drum", "feroviar"
        ],
        "Justiție": [
            "dosar penal", "procuror",
            "tribunal", "instanță", "dna",
            "anchetă", "judecător"
        ],
        "Sănătate": [
            "spital", "medic", "pacient",
            "sănătate", "ambulanță"
        ],
        "Educație": [
            "școală", "liceu", "elev",
            "profesor", "universitate",
            "educație"
        ],
        "Sport": [
            "fotbal", "meci", "campionat",
            "sportiv", "victorie"
        ]
    }

    for nume, cuvinte in categorii.items():
        if any(cuvant in text for cuvant in cuvinte):
            return nume

    return "Alte știri"


df, informatii = incarca_stiri()

if df.empty:
    st.warning(
        "Nu există încă date pentru afișare. "
        "Fișierul stiri_detectate.json trebuie "
        "adăugat lângă dashboard.py."
    )
    st.stop()

df["categorie"] = df["titlu"].apply(categorie)

st.sidebar.header("🔎 Filtre")

cautare = st.sidebar.text_input(
    "Caută știri, persoane sau instituții"
)

surse = sorted(df["sursa"].dropna().unique().tolist())
sursa = st.sidebar.multiselect(
    "Publicații", surse, default=surse
)

categorii = sorted(df["categorie"].unique().tolist())
categorii_selectate = st.sidebar.multiselect(
    "Categorii", categorii, default=categorii
)

perioada = st.sidebar.selectbox(
    "Perioada",
    ["Ultimele 24 de ore", "Ultimele 7 zile",
     "Ultimele 30 de zile", "Toate"]
)

filtrat = df[
    df["sursa"].isin(sursa)
    & df["categorie"].isin(categorii_selectate)
].copy()

if cautare:
    filtrat = filtrat[
        filtrat["titlu"].str.contains(
            cautare, case=False, na=False, regex=False
        )
        | filtrat["sursa"].str.contains(
            cautare, case=False, na=False, regex=False
        )
    ]

zile = {
    "Ultimele 24 de ore": 1,
    "Ultimele 7 zile": 7,
    "Ultimele 30 de zile": 30
}

if perioada in zile:
    reper = pd.Timestamp.now(tz="UTC") - pd.Timedelta(
        days=zile[perioada]
    )
    filtrat = filtrat[
        filtrat["data_publicarii"] >= reper
    ]

col1, col2, col3 = st.columns(3)

col1.metric("Articole afișate", len(filtrat))
col2.metric("Publicații", filtrat["sursa"].nunique())
col3.metric("Categorii", filtrat["categorie"].nunique())

st.divider()

tab1, tab2 = st.tabs(["📰 Flux de știri", "📊 Statistici"])

with tab1:
    st.subheader("Ultimele știri")

    if filtrat.empty:
        st.info("Nu există articole pentru filtrele selectate.")

    for _, articol in filtrat.head(150).iterrows():
        titlu = str(articol["titlu"])
        link = str(articol["link"])

        st.markdown(f"### {titlu}")

        data = articol["data_publicarii"]
        data_text = (
            data.strftime("%d.%m.%Y %H:%M UTC")
            if pd.notna(data) else "Dată necunoscută"
        )

        st.caption(
            f"{articol['sursa']} | "
            f"{articol['categorie']} | {data_text}"
        )

        if link.startswith(("https://", "http://")):
            st.link_button("Citește articolul", link)

        st.divider()

with tab2:
    st.subheader("Articole pe publicații")

    if not filtrat.empty:
        statistici = (
            filtrat["sursa"]
            .value_counts()
            .rename_axis("Publicație")
            .reset_index(name="Articole")
        )

        st.bar_chart(
            statistici.set_index("Publicație")
        )

        st.subheader("Distribuție pe categorii")

        st.bar_chart(
            filtrat["categorie"].value_counts()
        )

st.caption(
    "Newsroom AI • Monitorizare independentă. "
    "Clasificarea este automată, orientativă și "
    "bazată pe cuvintele din titluri."
)
