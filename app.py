from datetime import datetime
import streamlit as st
import pandas as pd
from pyproj import Transformer


@st.cache_data
def load_data(uploaded_file):
    """Function to read the CSV and cache the resulting DataFrame."""
    df = pd.read_csv(uploaded_file)
    return df


st.title("Hoogtetoets")

uploaded_file = st.file_uploader("Kies een CSV bestand", type="csv")

if uploaded_file is not None:
    st.write("### Uitgangspunten")
    dth = st.number_input("Wat is de afkeurhoogte / dijktafelhoogte?", value=-0.4)

    df = load_data(uploaded_file)

    # Check if x and y columns exist before trying to convert
    if "x" in df.columns and "y" in df.columns:
        # Create a transformer for coordinate conversion from RD New to WGS84
        transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
        # Perform the transformation
        lons, lats = transformer.transform(df["x"].values, df["y"].values)
        # Add the new lat/lon columns to the DataFrame
        df["lat"] = lats
        df["lon"] = lons
    st.write("De data uit het geuploadede CSV bestand:")
    st.dataframe(df)

    # Hoogteligging plot
    st.write("### Hoogteligging volgens AHN")

    # Check if all required columns are in the DataFrame
    df["dth"] = dth
    st.line_chart(df, x="l", y=["z3", "z4", "z5", "dth"])

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
        st.session_state.min_dz = 0.0
    if "max_dz" not in st.session_state:
        st.session_state.max_dz = 0.03

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
            oph_plot_names = []
            for pp in selected_pps:
                name = f"z_planperiode_{pp}"
                plot_names.append(name)
                df_result[name] = (
                    df_result[f"z_{now_year}"] - df_filtered[selected_agz[0]] * pp
                )
                oph_name = f"oph_{pp}"
                oph_plot_names.append(oph_name)
                df_result[oph_name] = df_result["dth"] - df_result[name]
                df_result[oph_name] = df_result[oph_name].clip(lower=0)

            st.line_chart(df_result, x="l", y=plot_names + ["dth"])
            st.dataframe(df_result)

            st.write("### Benodigde ophoging (excl zetting)")
            st.line_chart(df_result, x="l", y=oph_plot_names)
            st.dataframe(df_result)

            # --- Color mapping for st.map ---
            map_df = df_result.copy()

            st.write("### Kaarten met de benodigde ophoging")
            st.markdown(
                """
Let op dat in de onderstaande kaarten enkel gerekend is met de achtergrondzetting en **niet** met de zetting
die optreedt door het aanbrengen van de ophoging (zettingscompensatie). Dit dient berekend te worden.

De benodigde ophoging is uitgedrukt ik een kleurovergang van groen naar rood. Fel groen is geen ophoging,
fel rood is een ophoging van een meter of meer. Zie het dataframe hierboven voor de berekende waarden genaamd 
oph gevolgd door de planperiode, bv ```oph_5``` voor de benodigde ophoging voor een planperiode van 5 jaar etc.
                """
            )

            for pp in selected_pps:
                color_col_name = f"oph_{pp}"

                # Check if the column for coloring exists (user must have selected '5' years)
                if color_col_name in map_df.columns:
                    st.write(
                        f"#### Kaart met benodigde ophoging voor een planperiode van {pp} jaar"
                    )

                    maximized_values = map_df[color_col_name].clip(upper=1)

                    # Create a 'color' column with RGB tuples [R, G, B]
                    # It transitions from Green (low values) to Red (high values)
                    # If a value is NaN, color it grey.
                    map_df["color"] = maximized_values.apply(
                        lambda x: (
                            [0.5, 0.5, 0.5]
                            if pd.isna(x)
                            else [1.0 * x, 1.0 * (1 - x), 0.0]
                        )
                    )
                    st.map(
                        map_df, latitude="lat", longitude="lon", size=1, color="color"
                    )
