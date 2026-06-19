from app.db.connection import run_query
from app.ui.filters_module import FilterConfig, FilterManager
from app.ui.dashboard_output import DashboardOutput, setup_page

# ---------------------------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------------------------

setup_page("Pokémon Leaderboard", "🃏", layout="centered")


# ---------------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------------

filter_config = FilterConfig(
    category_options=[
        "Pokemon",
        "Baby",
        "Legendary",
        "Mythical",
        "Legendary + Mythical",
    ],
)

filter_manager = FilterManager(filter_config)
series, generation, mode = filter_manager.render_filters()

filter_sql, params = filter_manager.get_filter_sql(series, generation, mode)


# ---------------------------------------------------------------------------
# QUERY
# ---------------------------------------------------------------------------

QUERY = f"""
SELECT
    pokemon,
    number_of_cards,
    DENSE_RANK() OVER (ORDER BY number_of_cards DESC) AS rank
FROM (
    SELECT
        p.name AS pokemon,
        COUNT(*) AS number_of_cards
    FROM cards c
    INNER JOIN pokemons p ON c.dex_id_1 = p.dex_id
    INNER JOIN sets st ON c.set_id = st.id
    INNER JOIN series s ON st.series_id = s.id
    WHERE c.category IN ('Pokemon', 'Pokémon')
      AND c.dex_id_2 IS NULL
      {filter_sql}
    GROUP BY p.dex_id
)
ORDER BY number_of_cards DESC
"""

df = run_query(QUERY, params)


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

output = DashboardOutput(
    df, rank_column="rank", columns_to_display=["pokemon", "number_of_cards", "rank"]
)

output.format_and_display()
