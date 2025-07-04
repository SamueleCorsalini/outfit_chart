import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict
from streamlit_modal import Modal

# ==== Google Sheets Setup ====
creds_dict = st.secrets["GOOGLE_SHEET_CREDS"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("ClassificaAbbigliamento")
top3_ws = sheet.worksheet("daily_top3")
extra_ws = sheet.worksheet("extra_points")
theme_ws = sheet.worksheet("themes")

POINTS = [25, 20, 15]

# ==== Load Data ====
def load_top3():
    return pd.DataFrame(top3_ws.get_all_records())

def load_extra():
    return pd.DataFrame(extra_ws.get_all_records())

def load_themes():
    return pd.DataFrame(theme_ws.get_all_records())

def show_top3(date_str, data):
    st.subheader(f"☀️ Top 3 - {date_str}")
    
    row = data[data["Date"] == date_str]
    if row.empty:
        st.info("Nessuna classifica registrata per questa data.")
        return

    top3 = row.iloc[0][["Name1", "Name2", "Name3"]].tolist()
    for i, name in enumerate(top3):
        st.write(f"{i+1}. {name} (+{POINTS[i]} punti)")

# ==== Save Data ====
def add_daily_top3(date_str, top3_names):
    top3_ws.append_row([date_str] + top3_names)


def remove_daily_top3(date_str):
    all_data = top3_ws.get_all_values()
    for idx, row in enumerate(all_data):
        if row[0] == date_str:
            sheet.delete_rows(idx+1)
            break

def add_extra_points(name, points, reason):
    extra_ws.append_row([
        datetime.today().strftime("%Y-%m-%d"),
        name,
        points,
        reason
    ])

def remove_extra_point(entry_to_remove):
    all_data = extra_ws.get_all_values()
    headers = all_data[0]
    for idx, row in enumerate(all_data[1:], start=2):
        entry = dict(zip(headers, row))
        if all(str(entry.get(k, "")) == str(entry_to_remove.get(k, "")) for k in ["Date", "Name", "Points", "Reason"]):
            sheet.delete_rows(idx)
            return True
    return False

def set_theme(date_str, theme):
    sheet = client.open("ClassificaAbbigliamento").worksheet("themes")
    all_data = sheet.get_all_values()
    for idx, row in enumerate(all_data):
        if row[0] == date_str:
            sheet.delete_rows(idx + 1)
            break
    sheet.append_row([date_str, theme])

# Check admin access
def check_admin():
    password = st.text_input("Inserisci la password admin", type="password")
    return password == "capibara"  # Cambia con la tua password reale

# Save top 3 assignments
def assign_top3(date, first, second, third):
    points = {first: 25, second: 20, third: 15}
    for name, pts in points.items():
        top3_ws.append_row([str(date), name, pts])

# ==== Main App ====
def main():
    st.title("👔 Classifica Outfit 👗")

    modal = Modal("📖 Regolamento del Concorso", key="regolamento")

    _,c1= st.columns([3,1])

    open_modal = c1.button("Regolamento", icon="📖", help= "Mostra regolamento del concorso")

    if open_modal:
        modal.open()

    if modal.is_open():
        with modal.container():
            st.markdown("""
            ## 1. Classifica Giornaliera
            Ogni giorno lavorativo viene stilata una classifica dei tre migliori outfit tra i colleghi presenti in ufficio.
            I punteggi assegnati sono i seguenti:

            🥇 1° posto: 25 punti

            🥈 2° posto: 20 punti

            🥉 3° posto: 15 punti

            La classifica viene definita a insindacabile giudizio di Francesca, che riveste il ruolo di giudice supremo unico e assoluto.

            In caso di assenza di Francesca, Samuele C. assume in via eccezionale il ruolo di giudice. Tuttavia, Samuele non può in alcun caso attribuire punti a sé stesso.

            Se entrambi i giudici sono assenti dall’ufficio, la classifica giornaliera non viene stilata.
            Anche in presenza dei giudici, la classifica può non essere assegnata, qualora si ritenga che nessun outfit sia meritevole di riconoscimento per quel giorno.

            ## 2. Punti Bonus
            Oltre ai punteggi della classifica giornaliera, il giudice può attribuire, a propria totale discrezione, dei punti bonus.
            Tali punti possono essere assegnati per qualsiasi motivazione ritenuta valida dal giudice, e l'entità del bonus è variabile.

            ## 3. Criteri di Valutazione
            I giudizi si basano su una pluralità di elementi stilistici e di presentazione, tra cui:

            Scelta dei capi

            Coordinazione dell’outfit

            Accostamento cromatico

            Originalità e stile personale

            Portamento e atteggiamento

            Cura del trucco (se presente)

            Acconciatura

            Manicure / Smalti

            Accessori (occhiali, gioielli, cinture, borse, ecc.)

            Coerenza generale dell’immagine

            Altri fattori non elencati possono essere considerati rilevanti, a piena discrezione del giudice.

            ## 4. Partecipazione
            Non è necessario alcun tipo di iscrizione formale per partecipare:
            chiunque si presenti in ufficio con un outfit curato partecipa automaticamente al contest.

            ## 5. Premio Finale
            Il primo concorrente che raggiungerà la soglia di 500 punti riceverà un premio esclusivo e molto bello, messo in palio personalmente da Francesca.


            """)

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

    # === Classifica Ultimo Giorno === 
    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    show_top3(yesterday, top3)

    # === Classifica ===
    st.header("🏆 Classifica Generale")
    score_dict = defaultdict(int)
    for _, row in top3.iterrows():
        score_dict[row["Name1"]] += 25
        score_dict[row["Name2"]] += 20
        score_dict[row["Name3"]] += 15
    for _, row in extra.iterrows():
        score_dict[row["Name"]] += int(row["Points"])

    score_df = pd.DataFrame(score_dict.items(), columns=["Nome", "Punteggio"])
    score_df = score_df.sort_values("Punteggio", ascending=False).reset_index(drop=True)

    for i, row in score_df.iterrows():
        position = i + 1
        st.markdown(f"**{position}. {row['Nome']}**: {row['Punteggio']} punti")
        st.progress(min(row['Punteggio'] / 500, 1.0), text=f"{row['Punteggio']} / 500 punti per il premio!")

    # === Storico top 3 ===
    st.header("🗓️ Storico Top 3")
    st.dataframe(top3.sort_values("Date", ascending=False), use_container_width=True)

    # === Statistiche Avanzate ===
    if st.toggle("Visualizza statistiche avanzate 📊", key="stats_toggle"):
        st.markdown("---")
        st.subheader("Andamento punteggi nel tempo")

        history = defaultdict(int)
        df_list = []
        all_dates = pd.to_datetime(top3["Date"]).sort_values().unique()

        for d in all_dates:
            day_df = top3[pd.to_datetime(top3["Date"]) == d]
            for n, p in zip(["Name1", "Name2", "Name3"], [25, 20, 15]):
                history[day_df.iloc[0][n]] += p
            for name in history:
                df_list.append({"Date": d, "Name": name, "Score": history[name]})

        df = pd.DataFrame(df_list)

        # Sort by final score (last date) to get top 10
        final_scores = df[df["Date"] == df["Date"].max()].sort_values("Score", ascending=False)
        all_names = df["Name"].unique()
        top_names = final_scores["Name"].head(10).tolist()

        selected_names = st.multiselect("Seleziona persone da mostrare", options=all_names, default=top_names)

        filtered_df = df[df["Name"].isin(selected_names)]

        fig = px.line(
            filtered_df,
            x="Date",
            y="Score",
            color="Name",
            labels={"Score": "Punteggio cumulativo", "Date": "Data"},
            title="Andamento punteggi nel tempo"
        )

        # Improve layout: light axis text, better spacing
        fig.update_layout(
            title="Andamento punteggi nel tempo",
            xaxis_title="Data",
            yaxis_title="Punteggio cumulativo",
            xaxis_tickfont_color='white',
            yaxis_tickfont_color='white',
            legend_title_text='Partecipanti',
            legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.02),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="white"
        )

        st.plotly_chart(fig, use_container_width=True)

    # === Admin Panel ===
    # st.sidebar.title("Admin")
    # with st.sidebar:
    #     if check_admin():
    #         st.success("Accesso admin confermato")

    #         # Assegna Top 3
    #         st.subheader("Assegna la Top 3")
    #         date_top3 = st.date_input("Seleziona la data")
    #         st.write(f"Inserisci la top 3 per il giorno selezionato ({date_top3}):")
    #         name1 = st.text_input("1° posto", key="pos1")
    #         name2 = st.text_input("2° posto", key="pos2")
    #         name3 = st.text_input("3° posto", key="pos3")

    #         if st.button("Salva top 3"):
    #             if name1 and name2 and name3:
    #                 add_daily_top3(date_top3, [name1, name2, name3])
    #                 st.success(f"Top 3 per {date_top3} salvata con successo.")
    #             else:
    #                 st.warning("Inserisci tutti e tre i nomi.")

    #         # Elimina Top 3
    #         st.subheader("Rimuovi Top 3")
    #         date_str = st.date_input("Seleziona la data")
    #         if date_str in top3_ws:
    #             if st.button("🗑️ Elimina Top 3 di questo giorno"):
    #                 with st.expander("Conferma eliminazione Top 3"):
    #                     show_top3(date_str, sheet)
    #                     if st.button("Conferma eliminazione Top 3"):
    #                         remove_daily_top3(date_str)
    #                         st.success("Top 3 eliminata.")
    #                         st.rerun()

    #         st.divider()
    #         st.write("Assegna punti extra:")
    #         extra_name = st.text_input("Nome destinatario", key="extra_name")
    #         extra_points = st.number_input("Punti extra", min_value=1, step=1, key="extra_pts")
    #         reason = st.text_input("Motivazione", key="extra_reason")
    #         if st.button("Assegna punti extra"):
    #             if extra_name and reason:
    #                 add_extra_points(extra_name, int(extra_points), reason)
    #                 st.success("Punti extra assegnati.")
    #                 st.rerun()
    #             else:
    #                 st.warning("Inserisci nome e motivazione.")

    #         st.divider()
    #         st.write("📋 Punti extra assegnati:")
    #         for entry in extra_ws:
    #             formatted = f"{entry['Date']} - {entry['Name']} (+{entry['Points']}): {entry['Reason']}"
    #             if st.button(f"🗑 Elimina", key=str(entry)):
    #                 with st.expander(f"Conferma eliminazione di:"):
    #                     st.write(formatted)
    #                     if st.button("Conferma eliminazione", key=str(entry)+"confirm"):
    #                         success = remove_extra_point(entry)
    #                         if success:
    #                             st.success("Voce eliminata.")
    #                             st.rerun()
    #                         else:
    #                             st.error("Errore durante l'eliminazione.")
    #             else:
    #                 st.write(formatted)

            
    #         st.divider()
    #         st.write("🎨 Imposta tema del giorno:")
    #         theme_date = st.date_input("Data tema:", value=datetime.today(), key="theme_date")
    #         theme_str = st.text_input("Tema:", key="theme_text")
    #         if st.button("Imposta tema"):
    #             if theme_str:
    #                 set_theme(theme_date.strftime("%Y-%m-%d"), theme_str)
    #                 st.success("Tema impostato.")
    #                 st.rerun()
    #             else:
    #                 st.warning("Inserisci un tema valido.")
    #     else:
    #         st.error("Password errata.")


if __name__ == "__main__":
    main()
