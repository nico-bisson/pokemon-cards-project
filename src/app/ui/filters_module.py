"""
Shared filters module for TCG analytics dashboards.
Handles all filter UI and data fetching logic.
"""

import streamlit as st
from app.db.connection import run_query
from app.analytics.filters import build_filters
from app.analytics.romans import format_generation
from app.ui.language import get_selected_language


# Module-level cached data functions (avoids Streamlit hashing issues)
@st.cache_data
def _fetch_generations(language):
    """Fetch and cache generation data."""
    return run_query("SELECT id FROM generations ORDER BY id")


@st.cache_data
def _fetch_series(language):
    """Fetch and cache series data."""
    return run_query("""
        SELECT
            standard_name,
            MIN((
                SELECT MIN(release_date)
                FROM sets
                WHERE sets.series_id = series.id
            )) AS first_release_date
        FROM series 
        WHERE standard_name IS NOT NULL
          AND id != 'misc'
        GROUP BY standard_name
        ORDER BY first_release_date
    """)


class FilterConfig:
    """Configuration for a dashboard's filters."""

    def __init__(self, category_options):
        """
        Args:
            category_options: List of category options to display
        """
        self.category_options = category_options


class FilterManager:
    """Manages filter UI and data fetching for TCG dashboards."""

    def __init__(self, config: FilterConfig = None):
        """
        Initialize the filter manager.

        Args:
            config: FilterConfig instance with category options
        """
        self.config = config or FilterConfig()
        language = get_selected_language()
        # Load data from module-level cached functions
        self._gen_df = _fetch_generations(language)
        self._series_df = _fetch_series(language)

    @property
    def gen_df(self):
        """Get generations dataframe."""
        return self._gen_df

    @property
    def series_df(self):
        """Get series dataframe."""
        return self._series_df

    def render_filters(self):
        """
        Render filter UI and return selected values.

        Returns:
            tuple: (series, generation, mode) - the selected filter values
        """
        st.subheader("Filters")

        col1, col2 = st.columns(2)

        with col1:
            series = st.selectbox(
                "Series",
                ["All"] + self.series_df["standard_name"].tolist(),
                format_func=self._format_series,
            )

        with col2:
            generation = st.selectbox(
                "Generation",
                ["All"] + self.gen_df["id"].tolist(),
                format_func=self._format_generation,
            )

        mode = st.segmented_control(
            "Category",
            self.config.category_options,
        )

        return series, generation, mode

    def _format_series(self, series_id):
        """Format series dropdown label."""
        if series_id == "All":
            return "All"

        return series_id

    def _format_generation(self, gen_id):
        """Format generation dropdown label."""
        if gen_id == "All":
            return "All"
        return format_generation(gen_id)

    def get_filter_sql(self, series, generation, mode):
        """
        Build SQL filter clause.

        Args:
            series: Selected series
            generation: Selected generation
            mode: Selected category/mode

        Returns:
            tuple: (filter_sql, params) - SQL filter and parameters
        """
        return build_filters(series, generation, mode)
