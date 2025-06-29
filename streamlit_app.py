import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

DATA_FILE = "data.json"
ADMIN_PASSWORD = "capibara"
POINTS = [25, 20, 15]
GOAL_POINTS = 500

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
        theme_data = sheet_themes.get_all_records()
    except:
        theme_data = []

    top3_data = sheet_top3.get_all_records()
    extra_data = sheet_extra.get_all_records()

    daily_top3 = {}
    for row in top3_data:
        daily_top3[row["Date"]] = [row["Name1"], row["Name2"], row["Name3"]]

    themes = {row["Date"]: row["Theme"] for row in theme_data if "Date" in row and "Theme" in row}

    return {
        "daily_top3": daily_top3,
        "extra_points": extra_data,
        "themes": themes
    }

def add_daily_top3(date_str, top3_names):
    client = get_gsheet_client()
    sheet_top3 = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    sheet_top3.append_row([date_str] + top3_names)

def remove_daily_top3(date_str):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("daily_top3")
    all_data = sheet.get_all_values()
    for idx, row in enumerate(all_data):
        if row[0] == date_str:
            sheet.delete_rows(idx+1)
            break

def add_extra_points(name, points, reason):
    client = get_gsheet_client()
    sheet_extra = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    sheet_extra.append_row([
        datetime.today().strftime("%Y-%m-%d"),
        name,
        points,
        reason
    ])

def remove_extra_point(entry_to_remove):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("extra_points")
    all_data = sheet.get_all_values()
    headers = all_data[0]
    for idx, row in enumerate(all_data[1:], start=2):
        entry = dict(zip(headers, row))
        if all(str(entry.get(k, "")) == str(entry_to_remove.get(k, "")) for k in ["Date", "Name", "Points", "Reason"]):
            sheet.delete_rows(idx)
            return True
    return False

def set_theme(date_str, theme):
    client = get_gsheet_client()
    sheet = client.open("ClassificaAbbigliamento").worksheet("themes")
    all_data = sheet.get_all_values()
    for idx, row in enumerate(all_data):
        if row[0] == date_str:
            sheet.delete_rows(idx + 1)
            break
    sheet.append_row([date_str, theme])

def calculate_global_ranking(data):
    scores = defaultdict(int)
    for date, top3 in data.get("daily_top3", {}).items():
        for i, name in enumerate(top3):
            scores[name] += POINTS[i]
    for entry in data.get("extra_points", []):
        if isinstance(entry, dict):
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

def show_theme_of_today(data):
    today_str = datetime.today().strftime("%Y-%m-%d")
    theme = data.get("themes", {}).get(today_str)
    if theme:
        st.markdown(f"### 🎨 Tema del giorno: **{theme}**")

def main():
    st.set_page_config("Classifica Abbigliamento", layout="centered")
    st.title("🏆 Classifica Abbigliamento in Ufficio")

    data = load_data()

    show_theme_of_today(data)

    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in data["daily_top3"]:
        show_top3(yesterday, data)
    else:
        st.info("Nessuna top 3 registrata per ieri.")

    st.subheader("📊 Classifica globale")
    ranking = calculate_global_ranking(data)
    for i, (name, score) in enumerate(ranking, 1):
        progress = min(score / GOAL_POINTS, 1.0)
        st.write(f"{i}. {name}: {score} punti")
        st.progress(progress, text=f"Obiettivo: 500 punti")

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
        all_dates = sorted(list(set(data["daily_top3"].keys())))
        if not all_dates:
            st.info("Non ci sono abbastanza dati per generare statistiche.")
        else:
            df_scores = pd.DataFrame(columns=["Date"] + list({name for top3 in data["daily_top3"].values() for name in top3}))
            cumulative = defaultdict(int)
            for d in all_dates:
                row = {"Date": d}
                for i, name in enumerate(data["daily_top3"][d]):
                    cumulative[name] += POINTS[i]
                row.update(cumulative)
                df_scores = pd.concat([df_scores, pd.DataFrame([row])], ignore_index=True)
            df_scores = df_scores.fillna(method='ffill').fillna(0)
            df_scores["Date"] = pd.to_datetime(df_scores["Date"])
            df_scores.set_index("Date", inplace=True)
            st.line_chart(df_scores)

    st.divider()
    st.subheader("🔐 Area riservata (admin)")
    with st.expander("Login Admin"):
        password = st.text_input("Inserisci password admin:", type="password")
        if password == ADMIN_PASSWORD:
            st.success("Accesso admin riuscito.")
            selected_top3_date = st.date_input("Data per modificare/inserire Top 3:", value=datetime.today(), max_value=datetime.today())
            date_str = selected_top3_date.strftime("%Y-%m-%d")

            st.write(f"Inserisci la Top 3 per il {date_str}:")
            name1 = st.text_input("1° posto", key="pos1")
            name2 = st.text_input("2° posto", key="pos2")
            name3 = st.text_input("3° posto", key="pos3")

            if st.button("Salva top 3"):
                if name1 and name2 and name3:
                    add_daily_top3(date_str, [name1, name2, name3])
                    st.success(f"Top 3 per {date_str} salvata.")
                else:
                    st.warning("Inserisci tutti e tre i nomi.")

            if date_str in data["daily_top3"]:
                if st.button("🗑️ Elimina Top 3 di questo giorno"):
                    with st.expander("Conferma eliminazione Top 3"):
                        show_top3(date_str, data)
                        if st.button("Conferma eliminazione Top 3"):
                            remove_daily_top3(date_str)
                            st.success("Top 3 eliminata.")
                            st.rerun()

            st.divider()
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

            st.divider()
            st.write("📋 Punti extra assegnati:")
            for entry in data["extra_points"]:
                formatted = f"{entry['Date']} - {entry['Name']} (+{entry['Points']}): {entry['Reason']}"
                if st.button(f"🗑 Elimina", key=str(entry)):
                    with st.expander(f"Conferma eliminazione di:"):
                        st.write(formatted)
                        if st.button("Conferma eliminazione", key=str(entry)+"confirm"):
                            success = remove_extra_point(entry)
                            if success:
                                st.success("Voce eliminata.")
                                st.rerun()
                            else:
                                st.error("Errore durante l'eliminazione.")
                else:
                    st.write(formatted)

            st.divider()
            st.write("🎨 Imposta tema del giorno:")
            theme_date = st.date_input("Data tema:", value=datetime.today(), key="theme_date")
            theme_str = st.text_input("Tema:", key="theme_text")
            if st.button("Imposta tema"):
                if theme_str:
                    set_theme(theme_date.strftime("%Y-%m-%d"), theme_str)
                    st.success("Tema impostato.")
                    st.rerun()
                else:
                    st.warning("Inserisci un tema valido.")

        elif password:
            st.error("Password errata.")

if __name__ == "__main__":
    main()