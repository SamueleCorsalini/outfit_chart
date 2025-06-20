import streamlit as st
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

DATA_FILE = "data.json"
ADMIN_PASSWORD = "capibara"

POINTS = [25, 20, 15]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"daily_top3": {}, "extra_points": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_daily_top3(date_str, top3_names):
    data = load_data()
    data["daily_top3"][date_str] = top3_names
    save_data(data)

def add_extra_points(name, points, reason):
    data = load_data()
    data["extra_points"].append({
        "name": name,
        "points": points,
        "reason": reason,
        "date": datetime.today().strftime("%Y-%m-%d")
    })
    save_data(data)

def calculate_global_ranking(data):
    scores = defaultdict(int)

    for date, top3 in data["daily_top3"].items():
        for i, name in enumerate(top3):
            scores[name] += POINTS[i]

    for entry in data["extra_points"]:
        scores[entry["name"]] += entry["points"]

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

    # Calcola data di ieri
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Top 3 di ieri
    if yesterday in data["daily_top3"]:
        show_top3(yesterday, data)
    else:
        st.info("Nessuna top 3 registrata per ieri.")

    # Classifica globale
    st.subheader("📊 Classifica globale")
    ranking = calculate_global_ranking(data)
    for i, (name, score) in enumerate(ranking, 1):
        st.write(f"{i}. {name}: {score} punti")

    # Divider
    st.divider()

    # Calendario semplificato (simulato con dropdown)
    st.subheader("📅 Storico top 3")
    available_dates = sorted(data["daily_top3"].keys(), reverse=True)
    if available_dates:
        selected_date = st.selectbox("Seleziona una data con classifica registrata:", available_dates)
        show_top3(selected_date, data)
    else:
        st.info("Ancora nessuna classifica registrata nei giorni passati.")

    # Area Admin
    st.divider()
    st.subheader("🔐 Area riservata (admin)")

    with st.expander("Login Admin"):
        password = st.text_input("Inserisci password admin:", type="password")
        if password == ADMIN_PASSWORD:
            # Area Admin con inserimento top 3 per qualsiasi giorno
            st.success("Accesso admin riuscito.")

            # Seleziona la data per cui inserire la top 3
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

            # Assegna punti extra
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


        elif password:
            st.error("Password errata.")

if __name__ == "__main__":
    main()
