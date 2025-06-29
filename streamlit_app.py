import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

DATA_FILE = "data.json"
ADMIN_PASSWORD = "capibara"
POINTS = [25, 20, 15]

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
    sheet_themes = client.open("ClassificaAbbigliamento").worksheet("themes")

    top3_data = sheet_top3.get_all_records()
    extra_data = sheet_extra.get_all_records()
    themes_data = sheet_themes.get_all_records()

    daily_top3 = {row["Date"]: [row["Name1"], row["Name2"], row["Name3"]] for row in top3_data}
    return {
        "daily_top3": daily_top3,
        "extra_points": extra_data,
        "themes": {row["Date"]: row["Theme"] for row in themes_data}
    }

def add_daily_top3(date_str, top3_names):
    client = get_gsheet_client()
    sheet_top3 = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    sheet_top3.append_row([date_str] + top3_names)

def delete_top3(date_str):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    rows = sheet.get_all_values()
    for i, row in enumerate(rows):
        if row and row[0] == date_str:
            sheet.delete_rows(i + 1)
            return True
    return False

def add_extra_points(name, points, reason):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    sheet.append_row([datetime.today().strftime("%Y-%m-%d"), name, points, reason])

def delete_extra_point(index):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    sheet.delete_rows(index + 2)  # Skip header

def set_theme(date_str, theme):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("themes")
    sheet.append_row([date_str, theme])

def calculate_global_ranking(data):
    scores = defaultdict(int)
    for date, top3 in data.get("daily_top3", {}).items():
        for i, name in enumerate(top3):
            scores[name] += POINTS[i]
    for entry in data.get("extra_points", []):
        name = entry.get("name") or entry.get("Name")
        points = entry.get("points") or entry.get("Points")
        if name and points:
            scores[name] += int(points)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

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
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    if yesterday in data["daily_top3"]:
        show_top3(yesterday, data)
    else:
        st.info("Nessuna top 3 registrata per ieri.")

    st.subheader("📊 Classifica globale")
    ranking = calculate_global_ranking(data)
    for i, (name, score) in enumerate(ranking, 1):
        st.write(f"{i}. {name}: {score} punti")
        st.progress(min(score / 500, 1.0))

    st.divider()
    st.subheader("📅 Storico top 3")
    available_dates = sorted(data["daily_top3"].keys(), reverse=True)
    if available_dates:
        selected_date = st.selectbox("Seleziona una data:", available_dates)
        show_top3(selected_date, data)
        if theme := data["themes"].get(selected_date):
            st.info(f"🧵 Tema del giorno: *{theme}*")
    else:
        st.info("Nessuna classifica passata.")

    if st.toggle("📈 Mostra statistiche avanzate"):
        df = pd.DataFrame(ranking, columns=["Nome", "Punti"])
        st.bar_chart(df.set_index("Nome"))

    st.divider()
    st.subheader("🔐 Area riservata (admin)")
    with st.expander("Login Admin"):
        password = st.text_input("Password admin:", type="password")
        if password == ADMIN_PASSWORD:
            st.success("Accesso admin riuscito.")

            selected_top3_date = st.date_input("Data Top 3:", value=datetime.today(), max_value=datetime.today())
            date_str = selected_top3_date.strftime("%Y-%m-%d")

            st.write(f"Top 3 per {date_str}:")
            name1 = st.text_input("1° posto", key="pos1")
            name2 = st.text_input("2° posto", key="pos2")
            name3 = st.text_input("3° posto", key="pos3")
            if st.button("Salva top 3"):
                if all([name1, name2, name3]):
                    add_daily_top3(date_str, [name1, name2, name3])
                    st.success("Top 3 salvata.")
                    st.rerun()
            if st.button("❌ Elimina top 3 per questa data"):
                if delete_top3(date_str):
                    st.success("Top 3 eliminata.")
                    st.rerun()

            st.write("Assegna punti extra:")
            extra_name = st.text_input("Nome", key="extra_name")
            extra_points = st.number_input("Punti", min_value=1, step=1, key="extra_pts")
            reason = st.text_input("Motivazione", key="extra_reason")
            if st.button("Assegna"):
                if extra_name and reason:
                    add_extra_points(extra_name, int(extra_points), reason)
                    st.success("Punti extra assegnati.")
                    st.rerun()

            st.write("🧾 Elenco punti extra registrati:")
            for i, entry in enumerate(data["extra_points"]):
                st.write(f"{i+1}. {entry}")
                if st.button(f"Elimina", key=f"delete_extra_{i}"):
                    delete_extra_point(i)
                    st.success("Voce eliminata.")
                    st.rerun()

            st.divider()
            st.write("🎨 Imposta tema del giorno:")
            theme_date = st.date_input("Data tema", key="theme_date")
            theme_text = st.text_input("Tema (es. 'Total Black')")
            if st.button("Salva tema"):
                if theme_text:
                    set_theme(theme_date.strftime("%Y-%m-%d"), theme_text)
                    st.success("Tema salvato.")
                    st.rerun()
        elif password:
            st.error("Password errata.")

if __name__ == "__main__":
    main()
