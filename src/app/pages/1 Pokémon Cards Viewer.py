import streamlit as st
import pandas as pd

from app.db.connection import run_query
from app.ui.dashboard_output import DashboardOutput, setup_page
from app.ui.language import get_selected_language

# ---------------------------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------------------------

setup_page("Pokémon Cards Viewer", "🔍")


# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------


@st.cache_data
def load_all_pokemon(language):
    """Load all pokémon with card counts for the selectbox"""
    query = """
    SELECT 
        p.dex_id,
        p.name,
        COUNT(DISTINCT c.id) AS card_count,
        se.series_type
    FROM pokemons p
    LEFT JOIN cards c 
        ON c.dex_id_1 = p.dex_id 
        OR c.dex_id_2 = p.dex_id 
        OR c.dex_id_3 = p.dex_id 
        OR c.dex_id_4 = p.dex_id 
        OR c.dex_id_5 = p.dex_id
    INNER JOIN sets s ON c.set_id = s.id
    INNER JOIN series se ON s.series_id = se.id
    WHERE p.name IS NOT NULL
    GROUP BY p.dex_id, p.name
    ORDER BY p.dex_id
    """
    df = run_query(query)
    return df if df is not None else pd.DataFrame()


# ---------------------------------------------------------------------------
# UI / FILTERS
# ---------------------------------------------------------------------------

st.subheader("Select a Pokémon")

language = get_selected_language()
pokemon_df = load_all_pokemon(language)

if pokemon_df.empty:
    st.error("No pokémon found in database")
    st.stop()

pokemon_list = [
    f"#{row['dex_id']:03d} - {row['name']} ({row['card_count']} cards)"
    for _, row in pokemon_df.iterrows()
]


# ---------------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------------

col0, col1, col2, col3 = st.columns([4, 2.5, 2, 2.5])

with col0:
    selected_pokemon = st.selectbox(
        "Choose a Pokémon:",
        options=range(len(pokemon_df)),
        format_func=lambda i: pokemon_list[i],
    )


with col1:
    filter_mode = st.radio(
        "Filter mode:",
        ["All Cards", "Only this Pokémon", "Multiple species"],
        horizontal=True,
        help="Multiple species: your selected Pokémon species with other species.",
    )

with col2:
    card_type_filter = st.radio("Card Type:", ["Physical", "Digital"], horizontal=True)

with col3:
    reverse_sort = st.checkbox("Reverse sort", value=False)


# ---------------------------------------------------------------------------
# TITLE (FIXED SAFE BUILD)
# ---------------------------------------------------------------------------


selected_dex_id = pokemon_df.iloc[selected_pokemon]["dex_id"]
selected_name = pokemon_df.iloc[selected_pokemon]["name"]

page_title = f"Cards featuring {selected_name}"

if filter_mode == "Only this Pokémon":
    page_title += " (single Pokémon only)"
elif filter_mode == "Multiple species":
    page_title += " (Multiple species)"
elif filter_mode == "All Cards":
    page_title += " (All Cards)"

if card_type_filter == "Digital":
    page_title += " [Digital]"
elif card_type_filter == "Physical":
    page_title += " [Physical]"


# ---------------------------------------------------------------------------
# QUERY BUILD
# ---------------------------------------------------------------------------

if filter_mode == "Only this Pokémon":
    where_clause = f"""
    WHERE c.dex_id_1 = {selected_dex_id} 
    AND c.dex_id_2 IS NULL
    """
elif filter_mode == "Multiple species":
    where_clause = f"""
    WHERE {selected_dex_id} IN (
        c.dex_id_1,
        c.dex_id_2,
        c.dex_id_3,
        c.dex_id_4,
        c.dex_id_5
    ) AND c.dex_id_2 NOT NULL
    """
elif filter_mode == "All Cards":
    where_clause = f"""
    WHERE {selected_dex_id} IN (
        c.dex_id_1,
        c.dex_id_2,
        c.dex_id_3,
        c.dex_id_4,
        c.dex_id_5
    )
    """

if card_type_filter == "Digital":
    where_clause += " AND se.series_type = 'Digital'"
elif card_type_filter == "Physical":
    where_clause += " AND se.series_type != 'Digital'"


# ---------------------------------------------------------------------------
# SORTING
# ---------------------------------------------------------------------------


order_direction = "DESC" if reverse_sort else "ASC"
order_clause = f"ORDER BY s.release_date {order_direction}, c.id"


# ---------------------------------------------------------------------------
# FINAL QUERY
# ---------------------------------------------------------------------------

QUERY = f"""
SELECT
    c.id AS card_id,
    c.name AS card_name,
    c.set_id,
    s.name AS set_name,
    s.release_date,
    se.standard_name AS series_name,
    c.dex_id_1,
    c.dex_id_2,
    c.image
FROM cards c
JOIN sets s ON c.set_id = s.id
JOIN series se ON s.series_id = se.id
{where_clause}
{order_clause}
"""

df = run_query(QUERY)


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

st.subheader(page_title)

if df is None or df.empty:
    st.info(f"No cards found for {selected_name} with the selected filter.")
    st.stop()

# Stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Cards", len(df))

with col2:
    st.metric("Sets Featured In", df["set_name"].nunique())

with col3:
    st.metric("Series", df["series_name"].nunique())

with col4:
    primary_only = len(df[df["dex_id_1"] == selected_dex_id])
    st.metric("Primary Pokémon", primary_only)


st.divider()

# ---------------------------------------------------------------------------
# GALLERY
# ---------------------------------------------------------------------------

st.subheader("📸 Card Gallery")

cards_per_row = st.slider("Cards per row:", 2, 8, 4)
image_quality = st.radio("Image Quality:", ["Low", "High"], horizontal=True)

missing_cards = []

# ---------------------------------------------------------------------------
# STEP 1: FILTER VALID ROWS FIRST
# ---------------------------------------------------------------------------

valid_rows = []

for _, row in df.iterrows():
    base_url = row.get("image")

    if pd.notna(base_url) and str(base_url).strip():
        image_url = f"{base_url}/{image_quality.lower()}.webp"

        valid_rows.append((row, image_url))
    else:
        missing_cards.append(row["card_id"])

# ---------------------------------------------------------------------------
# STEP 2: RENDER ONLY VALID IMAGES
# ---------------------------------------------------------------------------

cols = st.columns(cards_per_row)

for idx, (row, image_url) in enumerate(valid_rows):
    col = cols[idx % cards_per_row]

    with col:
        st.image(image_url, width="stretch")

# ---------------------------------------------------------------------------
# STEP 3: MISSING REPORT
# ---------------------------------------------------------------------------

if missing_cards:
    st.divider()
    st.subheader("❌ Missing Images")

    st.write(f"{len(missing_cards)} cards have missing images:")

    st.code(", ".join(map(str, missing_cards)))


st.divider()

# ---------------------------------------------------------------------------
# TABLE
# ---------------------------------------------------------------------------

st.subheader("📋 Card List")

display_df = df[
    ["card_id", "card_name", "set_name", "series_name", "release_date"]
].copy()
display_df.columns = ["Card ID", "Card Name", "Set", "Series", "Release Date"]

st.dataframe(display_df, width="stretch", hide_index=True)

csv = display_df.to_csv(index=False)

st.download_button(
    "Download as CSV", data=csv, file_name=f"{selected_name}_cards.csv", mime="text/csv"
)
