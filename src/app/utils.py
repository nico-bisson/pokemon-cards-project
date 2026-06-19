import streamlit as st
import pandas as pd
import re


def _prettify_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def pretty(col: str) -> str:
        # snake_case → "Title Case"
        col = col.replace("_", " ")
        col = col.replace("pokemon", "Pokémon")
        return re.sub(r"\b\w", lambda m: m.group().upper(), col)

    df.columns = [pretty(c) for c in df.columns]
    return df


def st_dataframe_pretty(df: pd.DataFrame, **kwargs):
    """
    Streamlit dataframe with automatic pretty column names.

    - snake_case → Title Case
    - keeps original df intact
    """

    pretty_df = _prettify_columns(df)
    return st.dataframe(pretty_df, **kwargs)
