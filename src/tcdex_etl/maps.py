"""
maps.py — Transform raw TCGdex SDK objects into plain tuples ready for SQLite.

Date convention
---------------
- fetch_at   : TEXT, full datetime UTC "YYYY-MM-DD HH:MM:SS"
- release_date: TEXT, date only "YYYY-MM-DD"

SQLite recognises both formats natively for comparisons and strftime().
"""

from datetime import date, datetime, timezone
from typing import Any


def _pad(values: list, size: int) -> list:
    """Return a list of exactly `size` items, padding with None if needed."""
    return (list(values) + [None] * size)[:size]


def _now() -> str:
    """Current datetime as YYYY-MM-DD HH:MM:SS (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_date(value: str | None) -> str | None:
    """Normalise any date string to YYYY-MM-DD, or return None."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Pokemon  (sdk.pokemon.getSync)
# ---------------------------------------------------------------------------


def map_pokemon_obj(p: Any) -> tuple:
    return (
        p.id,  # dex_id (integer)
        p.name,
        _now(),  # fetch_at
    )


# ---------------------------------------------------------------------------
# Series  (sdk.serie.getSync)
# ---------------------------------------------------------------------------


def map_series_obj(s: Any) -> tuple:
    return (
        s.id,
        s.name,
        _now(),  # fetch_at  YYYY-MM-DD HH:MM:SS
    )


# ---------------------------------------------------------------------------
# Sets  (sdk.set.getSync)
# ---------------------------------------------------------------------------


def map_set_obj(s: Any) -> tuple:
    serie = getattr(s, "serie", None)
    count = getattr(s, "cardCount", None)
    return (
        s.id,
        s.name,
        serie.id if serie else None,  # series_id (FK)
        count.total if count else None,
        count.official if count else None,
        _parse_date(getattr(s, "releaseDate", None)),  # YYYY-MM-DD
        getattr(s, "logo", None),
        getattr(s, "symbol", None),
        _now(),  # fetch_at
    )


# ---------------------------------------------------------------------------
# Cards  (sdk.card.getSync)
# ---------------------------------------------------------------------------


def map_card_obj(c: Any) -> tuple:
    types = _pad(getattr(c, "types", None) or [], 2)
    dex_ids = _pad(getattr(c, "dexId", None) or [], 5)
    return (
        c.id,
        c.localId,
        c.name,
        c.category,
        c.set.id if c.set else None,  # set_id (FK)
        *types,  # type_1, type_2
        *dex_ids,  # dex_id_1 … dex_id_5
        c.hp,
        c.stage,
        c.evolveFrom,
        c.retreat,
        c.rarity,
        c.illustrator,
        c.image,
        _now(),  # fetch_at
    )
