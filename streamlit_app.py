import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
import matplotlib.pyplot as plt

DATA_FILE = "data.json"
ADMIN_PASSWORD = "capibara"
POINTS = [25, 20, 15]
TARGET_SCORE = 500

# Autenticazione Google Sheets
def get_gsheet_client():
    creds_dict = st.secrets["GOOGLE_SHEET_CREDS"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def load_data():
    client = get_gsheet_client()
    sheet_top3 = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    sheet_extra = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    try:
        sheet_themes = client.open("ClassificaAbbigliamento").worksheet("themes")
        themes_data = sheet_themes.get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        themes_data = []

    top3_data = sheet_top3.get_all_records()
    extra_data = sheet_extra.get_all_records()

    daily_top3 = {}
    for row in top3_data:
        daily_top3[row["Date"]] = [row["Name1"], row["Name2"], row["Name3"]]

    return {
        "daily_top3": daily_top3,
        "extra_points": extra_data,
        "themes": {row["Date"]: row["Theme"] for row in themes_data}
    }

def add_daily_top3(date_str, top3_names):
    client = get_gsheet_client()
    sheet_top3 = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    sheet_top3.append_row([date_str] + top3_names)

def add_extra_points(name, points, reason):
    client = get_gsheet_client()
    sheet_extra = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    sheet_extra.append_row([
        datetime.today().strftime("%Y-%m-%d"),
        name,
        points,
        reason
    ])

def add_theme(date_str, theme):
    client = get_gsheet_client()
    sheet_themes = client.open("ClassificaAbbigliamento").worksheet("themes")
    sheet_themes.append_row([date_str, theme])

def calculate_global_ranking(data):
    scores = defaultdict(int)
    history = defaultdict(list)

    for date, top3 in data.get("daily_top3", {}).items():
        for i, name in enumerate(top3):
            scores[name] += POINTS[i]
            history[name].append((date, POINTS[i]))

    for entry in data.get("extra_points", []):
        name = entry.get("name") or entry.get("Name")
        points = entry.get("points") or entry.get("Points")
        date = entry.get("date") or entry.get("Date")
        if name and points:
            scores[name] += int(points)
            history[name].append((date, int(points)))

    return sorted(scores.items(), key=lambda x: x[1], reverse=True), history

def show_top3(date_str, data):
    st.subheader(f"👔 Top 3 - {date_str}")
    top3 = data["daily_top3"].get(date_str)
    if not top3:
        st.info("Nessuna classifica registrata per questa data.")
        return
    for i, name in enumerate(top3):
        st.write(f"{i+1}. {name} (+{POINTS[i]} punti)")

def main():
    st.set_page_config("Classifica Abbigliamento", layout="centered")
    st.title("🏆 Classifica Abbigliamento in Ufficio")

    data = load_data()

    today_str = datetime.today().strftime("%Y-%m-%d")
    if today_str in data.get("themes", {}):
        st.markdown(f"### 👗 Tema del giorno: **{data['themes'][today_str]}**")

    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in data["daily_top3"]:
        show_top3(yesterday, data)
    else:
        st.info("Nessuna top 3 registrata per ieri.")

    st.subheader("📊 Classifica globale")
    ranking, history = calculate_global_ranking(data)
    for i, (name, score) in enumerate(ranking, 1):
        progress = min(score / TARGET_SCORE, 1.0)
        st.write(f"{i}. {name}: {score} punti")
        st.progress(progress, text=f"{score}/{TARGET_SCORE} punti")

    st.divider()

    st.subheader("📅 Storico top 3")
    available_dates = sorted(data["daily_top3"].keys(), reverse=True)
    if available_dates:
        selected_date = st.selectbox("Seleziona una data con classifica registrata:", available_dates)
        show_top3(selected_date, data)
    else:
        st.info("Ancora nessuna classifica registrata nei giorni passati.")

    st.divider()

    with st.expander("📈 Statistiche avanzate"):
        selected_users = st.multiselect("Seleziona partecipanti da analizzare:", list(history.keys()))
        if selected_users:
            fig, ax = plt.subplots()
            for name in selected_users:
                entries = sorted(history[name], key=lambda x: x[0])
                dates = [x[0] for x in entries]
                cumulative = []
                total = 0
                for _, pts in entries:
                    total += pts
                    cumulative.append(total)
                ax.plot(dates, cumulative, label=name)
            ax.legend()
            ax.set_title("Andamento punti nel tempo")
            ax.set_xlabel("Data")
            ax.set_ylabel("Punti cumulativi")
            st.pyplot(fig)

    st.divider()

    st.subheader("🔐 Area riservata (admin)")
    with st.expander("Login Admin"):
        password = st.text_input("Inserisci password admin:", type="password")
        if password == ADMIN_PASSWORD:
            st.success("Accesso admin riuscito.")
            selected_top3_date = st.date_input(
                "Seleziona una data per cui inserire/modificare la Top 3:",
                value=datetime.today(),
                max_value=datetime.today()
            )
            date_str = selected_top3_date.strftime("%Y-%m-%d")

            st.write(f"Inserisci la top 3 per il giorno selezionato ({date_str}):")
            name1 = st.text_input("1° posto", key="pos1")
            name2 = st.text_input("2° posto", key="pos2")
            name3 = st.text_input("3° posto", key="pos3")
            if st.button("Salva top 3"):
                if name1 and name2 and name3:
                    add_daily_top3(date_str, [name1, name2, name3])
                    st.success(f"Top 3 per {date_str} salvata con successo.")
                else:
                    st.warning("Inserisci tutti e tre i nomi.")

            st.write("Assegna punti extra:")
            extra_name = st.text_input("Nome destinatario", key="extra_name")
            extra_points = st.number_input("Punti extra", min_value=1, step=1, key="extra_pts")
            reason = st.text_input("Motivazione", key="extra_reason")
            if st.button("Assegna punti extra"):
                if extra_name and reason:
                    add_extra_points(extra_name, int(extra_points), reason)
                    st.success("Punti extra assegnati.")
                    st.rerun()
                else:
                    st.warning("Inserisci nome e motivazione.")

            st.write("\n---\n**📅 Imposta un tema per un giorno specifico**")
            theme_date = st.date_input("Data tema", key="theme_date")
            theme_text = st.text_input("Descrizione tema", key="theme_text")
            if st.button("Salva tema"):
                if theme_text:
                    add_theme(theme_date.strftime("%Y-%m-%d"), theme_text)
                    st.success("Tema salvato correttamente.")
                else:
                    st.warning("Inserisci una descrizione per il tema.")

        elif password:
            st.error("Password errata.")

if __name__ == "__main__":
    main()
