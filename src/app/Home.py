import streamlit as st
from app.ui.language import render_database_language_selector

DEFAULT_LANGUAGE = "fr"
st.session_state.setdefault("db_language", DEFAULT_LANGUAGE)


st.set_page_config(page_title="Pokémon TCG App", page_icon="🃏", layout="centered")

render_database_language_selector()

st.markdown(
    """
# 🃏 Pokémon TCG Dashboard

#### Welcome! 👋

Use the sidebar to explore this dashboard and switch the database language
between English, French, and Japanese.
This dashboard uses a database built with data retrieved from the TCGdex API
and PokéAPI. Card images are dynamically loaded from the TCGdex API.
The Japanese TCGdex database currently has limited coverage, with approximately
42.42% of cards available. See the [TCGdex status page][status] for the latest
information.

#### 🔍 Cards Viewer

Browse cards by Pokémon, illustrator, or set in a unified gallery. 
For example, select a Pokémon to view every available card featuring that species. 
Refine the results with additional filters, then export the matching cards to help track your collection.

#### 🃏🏆 Pokémon Leaderboard

Discover which Pokémon appear most frequently on cards. Use filters to analyze
appearances across series, generations, rarities, and other criteria.

#### 🎨🏆 Illustrators Leaderboard

Discover which illustrators have contributed the most artwork to the Pokémon
TCG. Explore their rankings by series, release period, card category, and other
criteria.
This dashboard offers a unique perspective on featured Pokémon and the artists
behind their cards.

#### 🎨 Illustrator Comparison — Series & Sets Contribution

Compare the contributions of two illustrators across Pokémon series and sets.
Interactive charts display their card totals or percentage contributions.
This view helps identify artist distribution, dominant illustrators, and
creative trends throughout the Pokémon TCG.

[status]: https://api.tcgdex.net/status
""",
    width="stretch",
    text_alignment="left",
)
