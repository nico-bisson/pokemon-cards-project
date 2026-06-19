import streamlit as st

from config import DATA_DIR

LANGUAGE_LABELS = {"fr": "Français 🇫🇷", "en": "English 🇬🇧", "ja": "Japanese 🇯🇵"}

DEFAULT_LANGUAGE = "en"


def get_available_database_languages():
    return sorted(
        (
            path.stem.replace("pokemon&cards_", "", 1)
            for path in DATA_DIR.glob("pokemon&cards_*.db")
        ),
        key=lambda lang: (
            lang != DEFAULT_LANGUAGE,
            LANGUAGE_LABELS.get(lang, lang).lower(),
        ),
    )


def get_selected_language():
    if "db_language" not in st.session_state:
        st.session_state["db_language"] = DEFAULT_LANGUAGE

    return st.session_state["db_language"]


def set_selected_language(language):
    st.session_state["db_language"] = language


def render_database_language_selector():
    languages = get_available_database_languages()

    if not languages:
        st.sidebar.warning("No database found.")
        set_selected_language(DEFAULT_LANGUAGE)
        return DEFAULT_LANGUAGE

    current_language = get_selected_language()
    if current_language not in languages:
        current_language = (
            DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in languages else languages[0]
        )
        set_selected_language(current_language)

    selected_language = st.sidebar.selectbox(
        "Database language",
        languages,
        index=languages.index(current_language),
        format_func=lambda lang: LANGUAGE_LABELS.get(lang, lang),
    )

    set_selected_language(selected_language)

    return selected_language
