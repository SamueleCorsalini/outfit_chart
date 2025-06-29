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

sheet = client.open("ClassificaAbbigliamento")
top3_ws = sheet.worksheet("daily_top3")
extra_ws = sheet.worksheet("extra_points")
theme_ws = sheet.worksheet("themes")

# ==== Load Data ====
def load_top3():
    return pd.DataFrame(top3_ws.get_all_records())

def load_extra():
    return pd.DataFrame(extra_ws.get_all_records())

def load_themes():
    return pd.DataFrame(theme_ws.get_all_records())

# ==== Save Data ====
def save_top3(df):
    top3_ws.clear()
    top3_ws.update([df.columns.values.tolist()] + df.values.tolist())

def save_extra(df):
    extra_ws.clear()
    extra_ws.update([df.columns.values.tolist()] + df.values.tolist())

def save_themes(df):
    theme_ws.clear()
    theme_ws.update([df.columns.values.tolist()] + df.values.tolist())

# ==== Main App ====
def main():
    st.title("🌟 Classifica Abbigliamento 🌟")

    top3 = load_top3()
    extra = load_extra()
    themes = load_themes()

    # === Show today's and future themes ===
    today = datetime.date.today()
    upcoming_themes = themes.copy()
    upcoming_themes["Date"] = pd.to_datetime(upcoming_themes["Date"]).dt.date
    
    today_theme = upcoming_themes[upcoming_themes["Date"] == today]
    future_themes = upcoming_themes[upcoming_themes["Date"] > today]

    if not today_theme.empty:
        st.info(f"**Tema di oggi:** {today_theme.iloc[0]['Theme']}")

    if not future_themes.empty:
        st.markdown("### Temi dei prossimi giorni")
        st.dataframe(future_themes.sort_values("Date"), use_container_width=True)

    # === Classifica ===
    st.header("Classifica Generale")
    score_dict = defaultdict(int)
    for _, row in top3.iterrows():
        score_dict[row["Name1"]] += 3
        score_dict[row["Name2"]] += 2
        score_dict[row["Name3"]] += 1
    for _, row in extra.iterrows():
        score_dict[row["Name"]] += int(row["Points"])

    score_df = pd.DataFrame(score_dict.items(), columns=["Nome", "Punteggio"])
    score_df = score_df.sort_values("Punteggio", ascending=False).reset_index(drop=True)

    for _, row in score_df.iterrows():
        st.markdown(f"**{row['Nome']}**: {row['Punteggio']} punti")
        st.progress(min(row['Punteggio'] / 500, 1.0), text=f"{row['Punteggio']} / 500 punti per il premio!")

    # === Storico top 3 ===
    st.header("Storico Top 3")
    st.dataframe(top3.sort_values("Date", ascending=False), use_container_width=True)

    # === Statistiche Avanzate ===
    if st.toggle("Visualizza statistiche avanzate", key="stats_toggle"):
        st.markdown("---")
        st.subheader("Andamento punteggi nel tempo")
        history = defaultdict(int)
        df_list = []
        all_dates = pd.to_datetime(top3["Date"]).sort_values().unique()
        for d in all_dates:
            day_df = top3[pd.to_datetime(top3["Date"]) == d]
            for n, p in zip(["Name1", "Name2", "Name3"], [3,2,1]):
                history[day_df.iloc[0][n]] += p
            for name in history:
                df_list.append({"Date": d, "Name": name, "Score": history[name]})
        df = pd.DataFrame(df_list)

        fig, ax = plt.subplots()
        for name in df["Name"].unique():
            user_df = df[df["Name"] == name]
            ax.plot(user_df["Date"], user_df["Score"], label=name)
        ax.set_xlabel("Data")
        ax.set_ylabel("Punteggio cumulativo")
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)

    # === Admin Panel ===
    st.sidebar.title("Admin")
    with st.sidebar:
        st.subheader("Imposta tema giornaliero")
        date = st.date_input("Data tema")
        theme = st.text_input("Tema")
        if st.button("Aggiungi tema"):
            new_row = pd.DataFrame([[date.isoformat(), theme]], columns=["Date", "Theme"])
            themes = pd.concat([themes, new_row], ignore_index=True)
            save_themes(themes)
            st.success("Tema aggiunto!")

        st.subheader("Elimina Top 3")
        if not top3.empty:
            date_to_delete = st.date_input("Scegli data", key="delete_date")
            if date_to_delete.isoformat() in top3["Date"].values:
                row = top3[top3["Date"] == date_to_delete.isoformat()].iloc[0]
                st.warning(f"Confermi eliminazione della top 3 per il {date_to_delete}?\n\n1°: {row['Name1']}\n2°: {row['Name2']}\n3°: {row['Name3']}")
                if st.button("Conferma eliminazione"):
                    top3 = top3[top3["Date"] != date_to_delete.isoformat()]
                    save_top3(top3)
                    st.success("Top 3 eliminata")

        st.subheader("Elimina punti extra")
        if not extra.empty:
            selected = st.selectbox("Seleziona riga da eliminare:",
                                    [f"{row['Date']} | {row['Name']} ({row['Points']} pt): {row['Reason']}" for _, row in extra.iterrows()])
            if st.button("Elimina punto extra"):
                idx = [i for i, row in extra.iterrows() if f"{row['Date']} | {row['Name']}" in selected][0]
                extra = extra.drop(idx).reset_index(drop=True)
                save_extra(extra)
                st.success("Punto extra eliminato")

if __name__ == "__main__":
    main()
