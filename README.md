# Pokemon TCG Dashboard

An interactive Streamlit dashboard for exploring Pokemon Trading Card Game
cards, Pokemon appearances, and illustrator contributions.

The dashboard uses local SQLite databases built from data retrieved through
the [TCGdex API](https://tcgdex.dev/) and
[PokeAPI](https://pokeapi.co/). Card images are dynamically loaded from the
TCGdex API.

## Features

- Browse cards by Pokemon, illustrator, or set from one unified explorer.
- Filter physical and digital cards.
- Rank Pokemon by their number of card appearances.
- Rank illustrators and compare their contributions across series and sets.
- Switch between English, French, and Japanese databases.
- Export filtered card lists as CSV files.

## Data coverage

TCGdex is a community-maintained database, so coverage varies by language.
Japanese data currently has significantly lower coverage than English and
French data. Check the
[official TCGdex status page](https://api.tcgdex.net/status) for current
figures.

The generated SQLite databases are included in this repository so the
deployed dashboard can use them without rebuilding the data at startup.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)

## Installation

Install the project and its dependencies:

```bash
uv sync
```

## Build the databases

Run the ETL once for each language you want to use:

```bash
uv run python -m tcdex_etl.main --lang en
uv run python -m tcdex_etl.main --lang fr
uv run python -m tcdex_etl.main --lang ja
```

Generated databases are stored in the `data/` directory:

```text
data/
|-- pokemon&cards_en.db
|-- pokemon&cards_fr.db
`-- pokemon&cards_ja.db
```

Running the ETL for an existing language replaces that language's database
with a newly generated one.

## Run the dashboard locally

```bash
uv run streamlit run src/app/Home.py
```

Then open something like [http://localhost:8501](http://localhost:8501).

## Project structure

```text
.
|-- data/                  # SQLite databases used by the dashboard
|-- src/
|   |-- app/               # Streamlit application
|   |-- tcdex_etl/         # TCGdex and PokeAPI data pipeline
|   `-- config.py          # Shared paths and database configuration
|-- pyproject.toml
`-- uv.lock
```

## Data sources

- [TCGdex](https://www.tcgdex.net/)
- [PokeAPI](https://pokeapi.co/)

This project is not affiliated with or endorsed by Nintendo, The Pokemon
Company, Creatures Inc., or GAME FREAK.
