import re

import pandas as pd
import streamlit as st

from app.db.connection import run_query
from app.ui.dashboard_output import setup_page
from app.ui.language import get_selected_language


setup_page("Cards Viewer", "🔍")


@st.cache_data
def load_pokemon(language):
    """Load Pokémon with their card counts."""
    query = """
        SELECT
            p.dex_id,
            p.name,
            COUNT(DISTINCT c.id) AS card_count
        FROM pokemons p
        LEFT JOIN cards c
            ON c.dex_id_1 = p.dex_id
            OR c.dex_id_2 = p.dex_id
            OR c.dex_id_3 = p.dex_id
            OR c.dex_id_4 = p.dex_id
            OR c.dex_id_5 = p.dex_id
        WHERE p.name IS NOT NULL
        GROUP BY p.dex_id, p.name
        HAVING card_count > 0
        ORDER BY p.dex_id
    """
    df = run_query(query)
    return df if df is not None else pd.DataFrame()


@st.cache_data
def load_illustrators(language):
    """Load illustrators with their card counts."""
    query = """
        SELECT
            illustrator,
            COUNT(*) AS card_count
        FROM cards
        WHERE illustrator IS NOT NULL
          AND TRIM(illustrator) != ''
        GROUP BY illustrator
        ORDER BY card_count DESC, illustrator
    """
    df = run_query(query)
    return df if df is not None else pd.DataFrame()


@st.cache_data
def load_series(language):
    """Load canonical series names in release order."""
    query = """
        SELECT
            se.standard_name,
            MIN(s.release_date) AS first_release_date
        FROM series se
        JOIN sets s ON s.series_id = se.id
        WHERE se.standard_name IS NOT NULL
          AND se.id != 'misc'
        GROUP BY se.standard_name
        ORDER BY first_release_date
    """
    df = run_query(query)
    return df if df is not None else pd.DataFrame()


@st.cache_data
def load_sets(series_name, language):
    """Load sets from one canonical series."""
    query = """
        SELECT
            s.id,
            s.name,
            s.release_date
        FROM sets s
        JOIN series se ON se.id = s.series_id
        WHERE se.standard_name = ?
        ORDER BY s.release_date, s.id
    """
    df = run_query(query, (series_name,))
    return df if df is not None else pd.DataFrame()


@st.cache_data
def load_cards(search_mode, selected_value, pokemon_match, language):
    """Load cards for the selected explorer mode."""
    params = ()

    if search_mode == "Pokémon":
        if pokemon_match == "Only this Pokémon":
            where_clause = """
                WHERE c.dex_id_1 = ?
                  AND c.dex_id_2 IS NULL
            """
            params = (selected_value,)
        elif pokemon_match == "Multiple species":
            where_clause = """
                WHERE ? IN (
                    c.dex_id_1,
                    c.dex_id_2,
                    c.dex_id_3,
                    c.dex_id_4,
                    c.dex_id_5
                )
                  AND c.dex_id_2 IS NOT NULL
            """
            params = (selected_value,)
        else:
            where_clause = """
                WHERE ? IN (
                    c.dex_id_1,
                    c.dex_id_2,
                    c.dex_id_3,
                    c.dex_id_4,
                    c.dex_id_5
                )
            """
            params = (selected_value,)
    elif search_mode == "Illustrator":
        where_clause = "WHERE c.illustrator = ?"
        params = (selected_value,)
    else:
        where_clause = "WHERE s.id = ?"
        params = (selected_value,)

    query = f"""
        SELECT
            c.id AS card_id,
            c.local_id,
            c.name AS card_name,
            c.category,
            c.rarity,
            c.illustrator,
            c.image,
            c.dex_id_1,
            c.dex_id_2,
            s.id AS set_id,
            s.name AS set_name,
            s.release_date,
            se.standard_name AS series_name,
            se.series_type
        FROM cards c
        JOIN sets s ON s.id = c.set_id
        JOIN series se ON se.id = s.series_id
        {where_clause}
        ORDER BY s.release_date, c.id
    """
    df = run_query(query, params)
    return df if df is not None else pd.DataFrame()


def safe_filename(value):
    """Return a filesystem-friendly name for CSV exports."""
    return "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in str(value)
    ).strip("_")


def natural_sort_key(value):
    """Build a sortable key for local IDs containing letters and numbers."""
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", str(value or ""))
    )


language = get_selected_language()
search_mode = st.segmented_control(
    "Browse cards by",
    ["Pokémon", "Illustrator", "Set"],
    default="Pokémon",
)

pokemon_match = "All appearances"
selected_label = ""

if search_mode == "Pokémon":
    pokemon_df = load_pokemon(language)

    if pokemon_df.empty:
        st.info("No Pokémon found in this database.")
        st.stop()

    pokemon_labels = {
        row["dex_id"]: (
            f"#{row['dex_id']:03d} - {row['name']} "
            f"({row['card_count']} cards)"
        )
        for _, row in pokemon_df.iterrows()
    }

    selector_col, match_col = st.columns([3, 2])

    with selector_col:
        selected_value = st.selectbox(
            "Pokémon",
            pokemon_df["dex_id"].tolist(),
            format_func=lambda dex_id: pokemon_labels[dex_id],
        )

    with match_col:
        pokemon_match = st.selectbox(
            "Appearance",
            [
                "All appearances",
                "Only this Pokémon",
                "Multiple species",
            ],
        )

    selected_label = pokemon_df.loc[
        pokemon_df["dex_id"] == selected_value,
        "name",
    ].iloc[0]

elif search_mode == "Illustrator":
    illustrators_df = load_illustrators(language)

    if illustrators_df.empty:
        st.info("No illustrators found in this database.")
        st.stop()

    illustrator_counts = dict(
        zip(
            illustrators_df["illustrator"],
            illustrators_df["card_count"],
            strict=False,
        )
    )

    selected_value = st.selectbox(
        "Illustrator",
        illustrators_df["illustrator"].tolist(),
        format_func=lambda name: (
            f"{name} ({illustrator_counts[name]} cards)"
        ),
    )
    selected_label = selected_value

else:
    series_df = load_series(language)

    if series_df.empty:
        st.info("No series found in this database.")
        st.stop()

    selector_col, set_col = st.columns(2)

    with selector_col:
        selected_series = st.selectbox(
            "Series",
            series_df["standard_name"].tolist(),
        )

    sets_df = load_sets(selected_series, language)

    if sets_df.empty:
        st.info("No sets found in this series.")
        st.stop()

    set_names = sets_df.set_index("id")["name"].to_dict()

    with set_col:
        selected_value = st.selectbox(
            "Set",
            sets_df["id"].tolist(),
            format_func=lambda set_id: set_names[set_id],
        )

    selected_label = set_names[selected_value]

cards_df = load_cards(
    search_mode,
    selected_value,
    pokemon_match,
    language,
)

if cards_df.empty:
    st.info("No cards found for this selection.")
    st.stop()

selected_series_filter = "All"
selected_set_filter = "All"

if search_mode != "Set":
    series_options = [
        "All",
        *cards_df["series_name"].dropna().drop_duplicates().tolist(),
    ]

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        selected_series_filter = st.selectbox(
            "Filter by series",
            series_options,
        )

    sets_source = cards_df
    if selected_series_filter != "All":
        sets_source = sets_source[
            sets_source["series_name"] == selected_series_filter
        ]

    filter_set_names = (
        sets_source[["set_id", "set_name"]]
        .drop_duplicates()
        .set_index("set_id")["set_name"]
        .to_dict()
    )

    with filter_col2:
        selected_set_filter = st.selectbox(
            "Filter by set",
            ["All", *filter_set_names],
            format_func=lambda set_id: (
                "All"
                if set_id == "All"
                else filter_set_names[set_id]
            ),
        )
else:
    _, _, filter_col3, filter_col4 = st.columns(4)

with filter_col3:
    card_type = st.selectbox(
        "Card type",
        ["All", "Physical", "Digital"],
    )

with filter_col4:
    reverse_sort = st.checkbox(
        (
            "Reverse card order"
            if search_mode == "Set"
            else "Newest first"
        )
    )

filtered_df = cards_df.copy()

if selected_series_filter != "All":
    filtered_df = filtered_df[
        filtered_df["series_name"] == selected_series_filter
    ]

if selected_set_filter != "All":
    filtered_df = filtered_df[
        filtered_df["set_id"] == selected_set_filter
    ]

if card_type == "Digital":
    filtered_df = filtered_df[
        filtered_df["series_type"] == "Digital"
    ]
elif card_type == "Physical":
    filtered_df = filtered_df[
        filtered_df["series_type"] != "Digital"
    ]

if search_mode == "Set":
    ordered_indices = sorted(
        filtered_df.index,
        key=lambda index: natural_sort_key(
            filtered_df.at[index, "local_id"]
        ),
        reverse=reverse_sort,
    )
    filtered_df = filtered_df.loc[ordered_indices]
else:
    filtered_df = filtered_df.sort_values(
        ["release_date", "card_id"],
        ascending=[not reverse_sort, not reverse_sort],
        na_position="last",
    )

st.subheader(f"{search_mode}: {selected_label}")

if filtered_df.empty:
    st.info("No cards match the selected filters.")
    st.stop()

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

metric_col1.metric("Cards", len(filtered_df))
metric_col2.metric("Sets", filtered_df["set_id"].nunique())
metric_col3.metric("Series", filtered_df["series_name"].nunique())
metric_col4.metric(
    "Pokémon cards",
    filtered_df["category"].isin(["Pokemon", "Pokémon"]).sum(),
)

st.divider()
st.subheader("Card Gallery")

gallery_col1, gallery_col2 = st.columns(2)

with gallery_col1:
    cards_per_row = st.slider("Cards per row", 2, 8, 4)

with gallery_col2:
    image_quality = st.radio(
        "Image quality",
        ["Low", "High"],
        horizontal=True,
    )

valid_images = []
missing_images = []

for _, card in filtered_df.iterrows():
    base_url = card.get("image")

    if pd.notna(base_url) and str(base_url).strip():
        image_url = (
            f"{str(base_url).rstrip('/')}/"
            f"{image_quality.lower()}.webp"
        )
        valid_images.append(image_url)
    else:
        missing_images.append(card["card_id"])

gallery_columns = st.columns(cards_per_row)

for index, image_url in enumerate(valid_images):
    with gallery_columns[index % cards_per_row]:
        st.image(image_url, width="stretch")

if missing_images:
    st.warning(
        f"{len(missing_images)} cards do not have an image available."
    )

st.divider()
st.subheader("Card List")

display_df = filtered_df[
    [
        "card_id",
        "local_id",
        "card_name",
        "category",
        "rarity",
        "illustrator",
        "set_name",
        "series_name",
        "release_date",
    ]
].copy()
display_df.columns = [
    "Card ID",
    "Local ID",
    "Card Name",
    "Category",
    "Rarity",
    "Illustrator",
    "Set",
    "Series",
    "Release Date",
]

st.dataframe(display_df, width="stretch", hide_index=True)

st.download_button(
    "Download as CSV",
    data=display_df.to_csv(index=False),
    file_name=(
        f"{search_mode.lower()}_{safe_filename(selected_label)}_cards.csv"
    ),
    mime="text/csv",
)
