import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

# ==== Google Sheets Setup ====
creds_dict = st.secrets["GOOGLE_SHEET_CREDS"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_NAME = "ClassificaAbbigliamento"

# Sheet references
sheet_main = client.open(SPREADSHEET_NAME).worksheet("daily_top3")
sheet_extra = client.open(SPREADSHEET_NAME).worksheet("extra_points")
sheet_themes = client.open(SPREADSHEET_NAME).worksheet("themes")

# Load data
def load_data():
    df_main = pd.DataFrame(sheet_main.get_all_records())
    df_extra = pd.DataFrame(sheet_extra.get_all_records())
    df_themes = pd.DataFrame(sheet_themes.get_all_records())
    return df_main, df_extra, df_themes

# Save top 3 assignments
def assign_top3(date, first, second, third):
    points = {first: 25, second: 20, third: 15}
    for name, pts in points.items():
        sheet_main.append_row([str(date), name, pts])

# Save extra points
def assign_extra(date, name, points, reason):
    sheet_extra.append_row([str(date), name, points, reason])

# Add theme for a date
def set_theme(date, theme):
    sheet_themes.append_row([str(date), theme])

# Check admin access
def check_admin():
    password = st.text_input("Inserisci la password admin", type="password")
    return password == "admin123"  # Cambia con la tua password reale

# MAIN
st.title("Classifica Abbigliamento")

df_main, df_extra, df_themes = load_data()

# Mostra tema del giorno corrente
oggi = datetime.today().date()
tema_oggi = df_themes[df_themes["Date"] == str(oggi)]
if not tema_oggi.empty:
    st.markdown(f"### 🌟 Tema del giorno: **{tema_oggi.iloc[0]['Theme']}**")

# ADMIN SECTION
st.markdown("---")
st.markdown("## Sezione Admin")
if check_admin():
    st.success("Accesso admin confermato")

    # Assegna Top 3
    st.subheader("Assegna la Top 3")
    date_top3 = st.date_input("Seleziona la data")
    partecipanti = sorted(set(df_main["Name"]).union(df_extra["Name"]))
    p1 = st.selectbox("1º posto", partecipanti)
    p2 = st.selectbox("2º posto", [x for x in partecipanti if x != p1])
    p3 = st.selectbox("3º posto", [x for x in partecipanti if x not in [p1, p2]])
    if st.button("Assegna Top 3"):
        assign_top3(date_top3, p1, p2, p3)
        st.success("Top 3 assegnata correttamente!")

    # Assegna punti extra
    st.subheader("Assegna punti extra")
    date_extra = st.date_input("Data (extra)", key="extra")
    name_extra = st.selectbox("Nome", partecipanti, key="extra_name")
    pts_extra = st.number_input("Punti", min_value=1, max_value=10, value=1)
    reason = st.text_input("Motivazione")
    if st.button("Assegna punti extra"):
        assign_extra(date_extra, name_extra, pts_extra, reason)
        st.success("Punti extra assegnati")

    # Imposta tema del giorno
    st.subheader("Imposta un tema")
    theme_date = st.date_input("Data (tema)", key="theme")
    theme_text = st.text_input("Descrizione tema")
    if st.button("Salva tema"):
        set_theme(theme_date, theme_text)
        st.success("Tema salvato")
else:
    st.warning("Accesso admin richiesto per visualizzare questa sezione")

