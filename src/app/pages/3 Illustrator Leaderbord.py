from app.db.connection import run_query
from app.ui.filters_module import FilterConfig, FilterManager
from app.ui.dashboard_output import DashboardOutput, setup_page

# ---------------------------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------------------------

setup_page("Illustrator leaderboard", "🎨", layout="centered")


# ---------------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------------

filter_config = FilterConfig(
    category_options=[
        "All Cards",
        "Trainer",
        "Energy",
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
    illustrator,
    number_of_cards,
    DENSE_RANK() OVER (ORDER BY number_of_cards DESC) AS rank
FROM (
    SELECT
        c.illustrator AS illustrator,
        COUNT(*) AS number_of_cards
    FROM cards c
    LEFT JOIN pokemons p ON c.dex_id_1 = p.dex_id
    JOIN sets se ON c.set_id = se.id
    JOIN series s ON se.series_id = s.id
    WHERE c.illustrator IS NOT NULL
      AND c.illustrator != ''
      {filter_sql}
    GROUP BY c.illustrator
)
ORDER BY number_of_cards DESC
"""

df = run_query(QUERY, params)


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

output = DashboardOutput(
    df,
    rank_column="rank",
    columns_to_display=["illustrator", "number_of_cards", "rank"],
)

output.format_and_display()
