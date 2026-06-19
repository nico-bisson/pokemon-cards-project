"""
Dashboard output formatter for TCG analytics.
Handles result formatting and display.
"""

import streamlit as st
from app.analytics.badges import rank_badge
from app.ui.language import render_database_language_selector
from app.utils import st_dataframe_pretty


class DashboardOutput:
    """Handles formatting and display of dashboard results."""

    def __init__(self, df, rank_column="rank", columns_to_display=None):
        """
        Initialize dashboard output.

        Args:
            df: DataFrame with results
            rank_column: Name of the rank column
            columns_to_display: List of columns to show (in order)
        """
        self.df = df
        self.rank_column = rank_column
        self.columns_to_display = columns_to_display

    def format_and_display(self, metric_labels=None):
        """
        Format dataframe with rank badges and display results.

        Args:
            metric_labels: Dict mapping column names to display labels
                          e.g., {"pokemon": "Pokémon", "number_of_cards": "Cards"}

        Returns:
            None (displays in Streamlit)
        """
        if self.df.empty:
            st.info("No results found for these filters.")
            return

        # Apply rank badge formatting
        self.df[self.rank_column] = self.df[self.rank_column].apply(rank_badge)

        # Select columns to display
        display_df = (
            self.df[self.columns_to_display] if self.columns_to_display else self.df
        )

        # Display metrics
        self._display_metrics(metric_labels)

        # Display table
        st_dataframe_pretty(display_df, hide_index=True)

    def _display_metrics(self, metric_labels=None):
        """Display summary metrics as caption."""
        if self.df.empty:
            return

        # Count unique items in first column
        first_col = (
            self.columns_to_display[0]
            if self.columns_to_display
            else self.df.columns[0]
        )
        count = len(self.df)

        # Sum cards from second column if it exists
        second_col = (
            self.columns_to_display[1]
            if self.columns_to_display and len(self.columns_to_display) > 1
            else None
        )
        total_cards = self.df[second_col].sum() if second_col else 0

        # Build caption
        first_label = (
            metric_labels.get(first_col, first_col) if metric_labels else first_col
        )

        if count > 1:
            caption = f"{count} {first_label}s"
        else:
            caption = f"{count} {first_label}"

        if total_cards == 1:
            caption += f" · {total_cards} Card total"

        if total_cards > 1:
            caption += f" · {total_cards} Cards total"

        st.caption(caption)


def setup_page(title, page_icon, layout="wide"):
    """
    Configure Streamlit page settings.

    Args:
        title: Page title
        page_icon: Emoji or icon for the page
        layout: Layout mode (centered, wide, etc.)
    """
    st.set_page_config(page_title=title, page_icon=page_icon, layout=layout)
    render_database_language_selector()
    st.title(f"{page_icon} Pokémon TCG — {title}")
