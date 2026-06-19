"""
fetcher.py - All TCGdex API fetching logic, decoupled from the CLI.
"""

import asyncio
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Callable

from tqdm import tqdm

from .db import (
    init_series_classification,
    insert_cards,
    insert_generations,
    insert_pokemons,
    insert_series,
    insert_sets,
)
from .maps import map_series_obj, map_set_obj, map_card_obj

log = logging.getLogger(__name__)

# PokeAPI language code mapping (TCGdex lang -> PokeAPI lang)
_POKEAPI_LANG = {
    "en": "en",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "ja": "ja",
    "ko": "ko",
    "zh-tw": "zh-Hant",
}

_HEADERS = {"User-Agent": "tcgdex-pipeline/1.0 (personal project)"}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _urlopen(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(req, timeout=timeout)


def _fetch_json(url: str):
    with _urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


class SafeNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return None


def _to_namespace(value):
    if isinstance(value, dict):
        return SafeNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


def _clean_tcgdex_data(data: dict) -> dict:
    """
    Remove fields that are not used by this project and can break SDK-style parsing.
    """
    data.pop("boosters", None)

    if isinstance(data.get("set"), dict):
        data["set"].pop("boosters", None)

    return data


# ---------------------------------------------------------------------------
# TCGdex REST fetchers
# ---------------------------------------------------------------------------


async def _fetch_all_rest(
    lang: str, resource: str, mapper: Callable, label: str
) -> list[tuple]:
    """Fetch and map every item from a TCGdex REST list endpoint."""
    list_url = f"https://api.tcgdex.net/v2/{lang}/{resource}"
    items = await asyncio.to_thread(_fetch_json, list_url)

    rows = []

    for item in tqdm(items, desc=label, unit=label.lower()):
        item_id = item.get("id")

        try:
            full_url = f"https://api.tcgdex.net/v2/{lang}/{resource}/{item_id}"
            full = await asyncio.to_thread(_fetch_json, full_url)
            full = _clean_tcgdex_data(full)

            rows.append(mapper(_to_namespace(full)))

        except Exception as exc:
            log.warning("Skipping %s %s - %s", label, item_id, exc)

    log.info("Got %d %s.", len(rows), label.lower())
    return rows


async def _fetch_one_card_rest(
    lang: str,
    card_id: str,
    semaphore: asyncio.Semaphore,
) -> tuple | None:
    async with semaphore:
        try:
            url = f"https://api.tcgdex.net/v2/{lang}/cards/{card_id}"
            full = await asyncio.to_thread(_fetch_json, url)
            full = _clean_tcgdex_data(full)

            return map_card_obj(_to_namespace(full))

        except Exception as exc:
            if "404" in str(exc):
                return None

            log.warning("Skipping card %s - %s", card_id, exc)
            return None


async def _fetch_cards_rest(lang: str, workers: int, batch_size: int, conn) -> None:
    items = await asyncio.to_thread(
        _fetch_json,
        f"https://api.tcgdex.net/v2/{lang}/cards",
    )

    log.info("Found %d cards to process.", len(items))

    semaphore = asyncio.Semaphore(workers)
    valid_set_ids = (
        {row[0].casefold(): row[0] for row in conn.execute("SELECT id FROM sets")}
        if conn
        else {}
    )
    tasks = [
        _fetch_one_card_rest(lang, card["id"], semaphore)
        for card in items
        if card.get("id")
    ]

    batch = []
    missing_set_ids = set()
    skipped_missing_sets = 0

    with tqdm(total=len(tasks), desc="Cards", unit="card") as bar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            bar.update(1)

            if result is None:
                continue

            set_id = result[3]
            if conn and set_id is not None:
                canonical_set_id = valid_set_ids.get(set_id.casefold())
                if canonical_set_id is None:
                    missing_set_ids.add(set_id)
                    skipped_missing_sets += 1
                    continue

                if canonical_set_id != set_id:
                    result = (*result[:3], canonical_set_id, *result[4:])

            batch.append(result)

            if conn and len(batch) >= batch_size:
                insert_cards(conn, batch)
                conn.commit()
                batch.clear()

    if conn and batch:
        insert_cards(conn, batch)
        conn.commit()

    if skipped_missing_sets:
        log.warning(
            "Skipped %d cards linked to missing sets: %s",
            skipped_missing_sets,
            ", ".join(sorted(missing_set_ids)),
        )


# ---------------------------------------------------------------------------
# PokeAPI fetchers
# ---------------------------------------------------------------------------


def _pokeapi_species(dex_id: int, lang: str) -> tuple | None:
    """
    Fetch stable species data for a given dex_id and language from PokeAPI.

    Returns a tuple of:
        (name, generation_id, is_legendary, is_mythical, is_baby,
         evolves_from, egg_groups, shape)
    or None on failure.
    """
    pokeapi_lang = _POKEAPI_LANG.get(lang, "en")
    url = f"https://pokeapi.co/api/v2/pokemon-species/{dex_id}/"

    try:
        with _urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())

        name = next(
            (e["name"] for e in data["names"] if e["language"]["name"] == pokeapi_lang),
            next(
                (e["name"] for e in data["names"] if e["language"]["name"] == "en"),
                None,
            ),
        )

        if not name:
            return None

        gen_id = int(data["generation"]["url"].rstrip("/").split("/")[-1])
        is_legendary = int(data["is_legendary"])
        is_mythical = int(data["is_mythical"])
        is_baby = int(data["is_baby"])

        evolves_from = (
            data["evolves_from_species"]["name"]
            if data.get("evolves_from_species")
            else None
        )

        egg_groups = ",".join(e["name"] for e in data.get("egg_groups", []))
        shape = data["shape"]["name"] if data.get("shape") else None

        return (
            name,
            gen_id,
            is_legendary,
            is_mythical,
            is_baby,
            evolves_from,
            egg_groups,
            shape,
        )

    except Exception:
        return None


async def _fetch_one_pokemon(
    dex_id: int,
    lang: str,
    now: str,
    semaphore: asyncio.Semaphore,
    retries: int = 3,
) -> tuple | None:
    async with semaphore:
        for attempt in range(retries):
            await asyncio.sleep(0.1)
            result = await asyncio.to_thread(_pokeapi_species, dex_id, lang)

            if result:
                (
                    name,
                    gen_id,
                    is_legendary,
                    is_mythical,
                    is_baby,
                    evolves_from,
                    egg_groups,
                    shape,
                ) = result

                return (
                    dex_id,
                    name,
                    gen_id,
                    is_legendary,
                    is_mythical,
                    is_baby,
                    evolves_from,
                    egg_groups,
                    shape,
                    now,
                )

            if attempt < retries - 1:
                await asyncio.sleep(1 * (attempt + 1))

        log.warning("Failed to fetch dex_id %d after %d attempts.", dex_id, retries)
        return None


async def _fetch_generations(conn) -> None:
    """Fetch generation dex ranges from PokeAPI."""
    with _urlopen("https://pokeapi.co/api/v2/generation?limit=100") as resp:
        index = json.loads(resp.read())

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for item in tqdm(index["results"], desc="Generations", unit="gen"):
        with _urlopen(item["url"]) as resp:
            data = json.loads(resp.read())

        dex_ids = sorted(
            int(s["url"].rstrip("/").split("/")[-1]) for s in data["pokemon_species"]
        )

        rows.append(
            (
                data["id"],
                data["name"],
                dex_ids[0],
                dex_ids[-1],
                now,
            )
        )

    insert_generations(conn, rows)
    conn.commit()
    log.info("Inserted %d generations.", len(rows))


async def _fetch_pokemons(lang: str, conn) -> None:
    """Fetch all Pokemon stable species data from PokeAPI for the given language."""
    with _urlopen("https://pokeapi.co/api/v2/pokemon-species?limit=2000") as resp:
        data = json.loads(resp.read())
        dex_ids = list(range(1, data["count"] + 1))

    log.info("Fetching %d Pokemon from PokeAPI (lang=%s)...", len(dex_ids), lang)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    semaphore = asyncio.Semaphore(5)
    tasks = [_fetch_one_pokemon(dex_id, lang, now, semaphore) for dex_id in dex_ids]

    with tqdm(total=len(tasks), desc="Pokemons", unit="pokemon") as bar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            bar.update(1)

            if result:
                rows.append(result)

    insert_pokemons(conn, rows)
    conn.commit()
    log.info("Inserted %d Pokemon.", len(rows))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def sync(lang: str, workers: int, batch_size: int, conn) -> None:
    """
    Main pipeline: fetch generations -> pokemons -> series -> sets -> cards.
    """
    log.info("Starting sync (lang=%s)...", lang)

    if conn:
        await _fetch_generations(conn)
        await _fetch_pokemons(lang, conn)

    rows = await _fetch_all_rest(lang, "series", map_series_obj, "Series")
    if conn:
        insert_series(conn, rows)
        init_series_classification(conn, lang)
        conn.commit()

    rows = await _fetch_all_rest(lang, "sets", map_set_obj, "Sets")
    if conn:
        insert_sets(conn, rows)
        conn.commit()

    await _fetch_cards_rest(lang, workers, batch_size, conn)

    log.info("Sync complete.")
