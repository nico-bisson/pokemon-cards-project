import streamlit as st

import plotly.graph_objects as go
from app.db.connection import run_query
from app.ui.dashboard_output import setup_page
from app.ui.language import get_selected_language

# -----------------------------
# Page config
# -----------------------------
setup_page(" Illustrator Comparison —  Series & Sets Contribution", "🎨")


# -----------------------------
# UI
# -----------------------------


@st.cache_data
def load_illustrators(series_type, language):
    """Load illustrators filtered by series type with card counts"""
    query = """
        SELECT 
            c.illustrator,
            COUNT(*) AS cnt
        FROM cards c
        JOIN sets se ON se.id = c.set_id
        JOIN series s ON s.id = se.series_id
        WHERE c.illustrator IS NOT NULL AND s.series_type = ?
        GROUP BY c.illustrator
        ORDER BY cnt DESC, c.illustrator
    """
    df = run_query(query, (series_type,))
    if df is None or df.empty:
        return []
    # Format with count for display
    return [f"{row['illustrator']} ({row['cnt']})" for _, row in df.iterrows()]


@st.cache_data
def load_series_types(language):
    """Load all available series types from database"""
    query = """
        SELECT DISTINCT series_type
        FROM series
        WHERE series_type IS NOT NULL
        ORDER BY series_type
    """
    df = run_query(query)
    if df is None or df.empty:
        return ["Main"]
    return df["series_type"].tolist()


language = get_selected_language()
series_types = load_series_types(language)

# Main row: 5 columns layout
col1, col2, col3, col4, col5 = st.columns(5)

with col5:
    main_index = series_types.index("Main") if "Main" in series_types else 0
    series_type = st.selectbox("Series Type", series_types, index=main_index)

# Load illustrators based on selected series type
illustrators_with_counts = load_illustrators(series_type, language)

if not illustrators_with_counts:
    st.warning(f"No illustrators found for {series_type} series")
    st.stop()

# Extract just the names (without counts) for the selectbox value
illustrators = [ill.split(" (")[0] for ill in illustrators_with_counts]

# Update col1, col2, col3, col4 with actual content
with col1:
    artist_a = st.selectbox(
        "Illustrator A",
        illustrators_with_counts,
        index=1 if len(illustrators_with_counts) > 1 else 0,
        format_func=lambda x: x,
    )
    artist_a = artist_a.split(" (")[0]

with col2:
    artist_b = st.selectbox(
        "Illustrator B", illustrators_with_counts, format_func=lambda x: x
    )
    artist_b = artist_b.split(" (")[0]

with col3:
    view_mode = st.radio(
        "Display mode", ["Number of cards", "Percentage"], horizontal=True
    )

with col4:
    grouping_mode = st.radio("Group by", ["Main Series", "Main Sets"], horizontal=True)

if artist_a == artist_b:
    st.warning("Please select two different illustrators")
    st.stop()

# -----------------------------
# SQL QUERY
# -----------------------------

if grouping_mode == "Main Series":
    query = """
    WITH base AS (
        SELECT
            s.id AS series_id,
            s.standard_name AS group_name,
            s.series_type as series_type,
            se.release_date,
            c.illustrator
        FROM series s
        JOIN sets se ON se.series_id = s.id
        LEFT JOIN cards c ON c.set_id = se.id
    )

    SELECT
        series_id,
        group_name,
        series_type,
        MIN(DATE(release_date)) AS first_release_date,

        COUNT(CASE WHEN illustrator = ? THEN 1 END) AS artist_a_count,
        COUNT(CASE WHEN illustrator = ? THEN 1 END) AS artist_b_count,

        COUNT(illustrator) AS total_cards,

        ROUND(
            100.0 * COUNT(CASE WHEN illustrator = ? THEN 1 END)
            / NULLIF(COUNT(illustrator), 0),
            2
        ) AS artist_a_pct,

        ROUND(
            100.0 * COUNT(CASE WHEN illustrator = ? THEN 1 END)
            / NULLIF(COUNT(illustrator), 0),
            2
        ) AS artist_b_pct

    FROM base
    WHERE series_type = ?
    GROUP BY group_name
    ORDER BY first_release_date;
    """
else:
    query = """
    WITH base AS (
        SELECT
            se.id AS set_id,
            se.name AS group_name,
            s.series_type as series_type,
            se.release_date,
            c.illustrator
        FROM sets se
        JOIN series s ON se.series_id = s.id
        LEFT JOIN cards c ON c.set_id = se.id
    )

    SELECT
        set_id,
        group_name,
        series_type,
        MIN(DATE(release_date)) AS first_release_date,

        COUNT(CASE WHEN illustrator = ? THEN 1 END) AS artist_a_count,
        COUNT(CASE WHEN illustrator = ? THEN 1 END) AS artist_b_count,

        COUNT(illustrator) AS total_cards,

        ROUND(
            100.0 * COUNT(CASE WHEN illustrator = ? THEN 1 END)
            / NULLIF(COUNT(illustrator), 0),
            2
        ) AS artist_a_pct,

        ROUND(
            100.0 * COUNT(CASE WHEN illustrator = ? THEN 1 END)
            / NULLIF(COUNT(illustrator), 0),
            2
        ) AS artist_b_pct

    FROM base
    WHERE series_type = ?
    GROUP BY set_id, group_name
    ORDER BY first_release_date;
    """


# -----------------------------
# DATA
# -----------------------------
df = run_query(query, (artist_a, artist_b, artist_a, artist_b, series_type))

if df is None or df.empty:
    st.info("No data found.")
    st.stop()

df = df.sort_values("first_release_date")


# -----------------------------
# CHART
# -----------------------------
st.subheader(
    f"📊 Comparison of contribution across {series_type} {grouping_mode.lower()}"
)

fig = go.Figure()

if view_mode == "Number of cards":

    fig.add_trace(
        go.Bar(
            x=df["group_name"],
            y=df["artist_a_count"],
            name=artist_a,
            marker_color="blue",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["group_name"],
            y=df["artist_b_count"],
            name=artist_b,
            marker_color="red",
        )
    )

    y_title = "Number of cards"

else:

    fig.add_trace(
        go.Bar(
            x=df["group_name"], y=df["artist_a_pct"], name=artist_a, marker_color="blue"
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["group_name"], y=df["artist_b_pct"], name=artist_b, marker_color="red"
        )
    )

    y_title = "Percentage (%)"


fig.update_layout(
    barmode="group",
    xaxis_title=grouping_mode,
    yaxis_title=y_title,
    template="plotly_white",
    height=500,
)

st.plotly_chart(fig, use_container_width=True)
