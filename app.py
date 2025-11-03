from datetime import datetime
import streamlit as st
import pandas as pd


@st.cache_data
def load_data(uploaded_file):
    """Function to read the CSV and cache the resulting DataFrame."""
    df = pd.read_csv(uploaded_file)
    return df


st.title("Hoogtetoets")

uploaded_file = st.file_uploader("Kies een CSV bestand", type="csv")

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.write("De data uit het geuploadede CSV bestand:")
    st.dataframe(df)

    # Hoogteligging plot
    st.write("### Hoogteligging volgens AHN")

    # Check if all required columns are in the DataFrame
    if all(col in df.columns for col in ["l", "z3", "z4", "z5"]):
        st.line_chart(df, x="l", y=["z3", "z4", "z5"])
    else:
        st.warning(
            f"To display the plot, the CSV must contain the following columns: {', '.join(["l","z3", "z4", "z5"])}"
        )

    st.write("### Achtergrondzetting volgens AHN")
    st.markdown(
        """
In eerste instantie zie je in de onderstaande grafiek de ongefilterde data, dat wil zeggen dat extremen niet gefilterd worden. Je kunt
nu de grafiek bekijken en bepalen welke van de gevonden achtergrondzettingen je wilt gebruiken. Je kunt in de volgende stap maar **één** 
achtergrondzetting selecteren.

Na deze keuze kun je extremen weg filteren. Zet bijvoorbeeld de minimale waarde op 0.0 om te voorkomen dat negatieve zettingen (zwel)
meegerekend worden. Op dezelfde manier kunnen extreme zettingen beperkt worden tot een waarde tussen de 0.0 en 0.05m. 

Gebruik de **refresh** knop om deze waarden toe te passen. Op dat moment staan de waardes voor de volgende berekeningen vast tenzij je besluit \
nog een keer **refresh** te gebruiken met andere waarden voor de minimale en maximale waarde.
                """
    )

    selected_agz = st.multiselect(
        "Gebruik periode(s)",
        ["agz34", "agz45", "agz35"],
        default=["agz34", "agz45", "agz35"],
    )

    # Achtergrondzettingen plot
    col1, col2, col3 = st.columns(3)

    # Initialize session state for the filter values if they don't exist
    if "min_dz" not in st.session_state:
        st.session_state.min_dz = -0.05
    if "max_dz" not in st.session_state:
        st.session_state.max_dz = 0.05

    with col1:
        # These sliders will just capture user input, not directly filter
        min_val = st.slider(
            "minimaal (zwel)",
            -0.05,
            0.0,
            st.session_state.min_dz,
            step=0.005,
            format="%.3f",
        )
    with col2:
        max_val = st.slider(
            "maximaal (zetting)",
            0.0,
            0.05,
            st.session_state.max_dz,
            step=0.005,
            format="%.3f",
        )
    with col3:
        # When this button is clicked, update the session state with the slider values
        if st.button("refresh"):
            st.session_state.min_dz = min_val
            st.session_state.max_dz = max_val

    df_filtered = df.copy()
    if all(col in df.columns for col in ["l", "agz34", "agz45", "agz35"]):
        # Create a copy of the dataframe to filter

        # Filter the data based on the values stored in session_state
        for col in [selected_agz]:
            df_filtered[col] = df_filtered[col].clip(
                st.session_state.min_dz, st.session_state.max_dz
            )

        st.line_chart(df_filtered, x="l", y=selected_agz)
    else:
        st.warning(
            f"To display the plot, the CSV must contain the following columns: {', '.join(["l", "agz34", "agz45", "agz35"])}"
        )

    st.write("### Hoogteligging na verstrijken van de planperiode(s).")
    st.markdown(
        """
Selecteer de planperiodes die je wilt onderzoeken. Hoe meer planperiodes hoe voller de grafiek dus hou daar rekening mee.
                """
    )

    selected_pps = st.multiselect(
        "Gebruik planperiode(s)",
        [5, 10, 15, 20, 25, 30],
        default=[5, 10, 15, 30],
    )

    if st.button("Berekenen"):
        if len(selected_agz) != 1:
            st.warning(
                "Je dient een keuze te maken voor de te gebruiken achtergrondzetting. Het is niet mogelijk om simultaan meerdere achtergrondzettingen te gebruiken."
            )
        else:
            st.write("### Hoogteligging na planperiode(s) volgens AHN")
            now_year = datetime.now().year
            num_jaren = datetime.now().year - 2023

            df_result = df_filtered.copy()
            df_result[f"z_{now_year}"] = (
                df["z5"] - df_filtered[selected_agz[0]] * num_jaren
            )

            plot_names = []
            for pp in selected_pps:
                name = f"z_planperiode_{pp}"
                plot_names.append(name)
                df_result[name] = (
                    df_result[f"z_{now_year}"] - df_filtered[selected_agz[0]] * pp
                )

            st.line_chart(df_result, x="l", y=plot_names)
            st.dataframe(df_result)
