"""
db.py — SQLite persistence layer for the TCGdex card pipeline.

Date convention
---------------
All dates are stored as TEXT in ISO-8601 format (YYYY-MM-DD).
SQLite has no native DATE type but recognises this format natively
for comparisons, ordering, and date functions (date(), strftime()…).
"""

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id        INTEGER NOT NULL PRIMARY KEY,
    name      TEXT    NOT NULL,
    dex_start INTEGER NOT NULL,
    dex_end   INTEGER NOT NULL,
    fetch_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pokemons (
    dex_id        INTEGER NOT NULL PRIMARY KEY,
    name          TEXT    NOT NULL,
    generation_id INTEGER     NULL REFERENCES generations (id),
    is_legendary  INTEGER     NULL,
    is_mythical   INTEGER     NULL,
    is_baby       INTEGER     NULL,
    evolves_from  TEXT        NULL,
    egg_groups    TEXT        NULL,
    shape         TEXT        NULL,
    fetch_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS series (
    id       TEXT NOT NULL PRIMARY KEY,
    name     TEXT NOT NULL,
    fetch_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sets (
    id           TEXT    NOT NULL PRIMARY KEY,
    name         TEXT    NOT NULL,
    series_id    TEXT        NULL REFERENCES series (id),
    total_cards  INTEGER     NULL,
    official     INTEGER     NULL,
    release_date TEXT        NULL,
    logo         TEXT        NULL,
    symbol       TEXT        NULL,
    fetch_at     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id          TEXT    NOT NULL PRIMARY KEY,
    local_id    TEXT        NULL,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    set_id      TEXT        NULL REFERENCES sets (id),
    type_1      TEXT        NULL,
    type_2      TEXT        NULL,
    dex_id_1    INTEGER     NULL,
    dex_id_2    INTEGER     NULL,
    dex_id_3    INTEGER     NULL,
    dex_id_4    INTEGER     NULL,
    dex_id_5    INTEGER     NULL,
    hp          INTEGER     NULL,
    stage       TEXT        NULL,
    evolve_from TEXT        NULL,
    retreat     INTEGER     NULL,
    rarity      TEXT        NULL,
    illustrator TEXT        NULL,
    image       TEXT        NULL,
    fetch_at    TEXT    NOT NULL
);
"""

_WESTERN_WIZARD_SERIES = {
    "base": "Wizard",
    "gym": "Wizard",
    "neo": "Wizard",
    "ecard": "Wizard",
    "lc": "Wizard",
}

SERIES_STANDARD_NAMES = {
    "en": _WESTERN_WIZARD_SERIES,
    "fr": _WESTERN_WIZARD_SERIES,
    "ja": {
        "PMCG": "Wizard",
        "neo": "Wizard",
        "VS": "Wizard",
        "web": "Wizard",
        "e": "Wizard",
        "ADV": "EX",
        "PCG": "EX",
        "L": "HeartGold & SoulSilver",
        "XY": "XY",
        "XYb": "XY",
        "SM": "Sun & Moon",
        "S": "Sword & Shield",
        "M": "Mega Evolution",
        "SV": "Scarlet & Violet",
    },
}


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open the SQLite connection, enforce FK constraints, and ensure the schema exists."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)

    card_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(cards)")
    }
    if "local_id" not in card_columns:
        conn.execute("ALTER TABLE cards ADD COLUMN local_id TEXT")
        conn.execute(
            """
            UPDATE cards
            SET local_id = SUBSTR(id, LENGTH(set_id) + 2)
            WHERE local_id IS NULL
              AND set_id IS NOT NULL
            """
        )

    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------


def insert_generations(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO generations (id, name, dex_start, dex_end, fetch_at) VALUES (?,?,?,?,?)",
        rows,
    )


def insert_pokemons(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO pokemons
            (dex_id, name, generation_id, is_legendary, is_mythical, is_baby,
             evolves_from, egg_groups, shape, fetch_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )


def insert_series(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO series (id, name, fetch_at) VALUES (?,?,?)",
        rows,
    )


def init_series_classification(conn: sqlite3.Connection, lang: str) -> None:
    """Add and fill derived classification columns on the series table."""
    try:
        conn.execute("ALTER TABLE series ADD COLUMN standard_name TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE series ADD COLUMN series_type TEXT")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
        UPDATE series
        SET
            series_type =
                CASE
                    WHEN id = 'tcgp' THEN 'Digital'

                    WHEN id IN (
                        'pop',
                        'tk',
                        'mc',
                        'misc'
                    ) THEN 'Side'

                    ELSE 'Main'
                END,

            standard_name = name
        """)

    standard_names = SERIES_STANDARD_NAMES.get(lang.lower(), {})
    conn.executemany(
        "UPDATE series SET standard_name = ? WHERE id = ?",
        (
            (standard_name, series_id)
            for series_id, standard_name in standard_names.items()
        ),
    )


def insert_sets(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO sets
            (id, name, series_id, total_cards, official,
             release_date, logo, symbol, fetch_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )


def insert_cards(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO cards
            (id, local_id, name, category, set_id,
             type_1, type_2,
             dex_id_1, dex_id_2, dex_id_3, dex_id_4, dex_id_5,
             hp, stage, evolve_from, retreat,
             rarity, illustrator, image, fetch_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
