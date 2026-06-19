"""
main.py — CLI entry point for the TCGdex card pipeline.

Usage
-----
    python main.py                      # sync in English
    python main.py --lang fr            # sync in French
    python main.py --workers 50         # raise concurrency ceiling
    python main.py --batch 200          # commit every 200 cards
    python main.py --dry-run            # fetch without writing to DB

Supported language codes
------------------------
    en, fr, de, es, it, pt, zh-tw, ja, ko, ...
    Full list: https://tcgdex.dev/docs
"""

import argparse
import asyncio
import logging
import sys

from config import DATA_DIR, get_db_path

from .db import get_connection
from .fetcher import sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


async def run(lang: str, workers: int, batch_size: int, dry_run: bool) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = get_db_path(lang)
    if not dry_run and db_path.exists():
        log.info("Removing existing database: %s", db_path)
        db_path.unlink()

    conn = None if dry_run else get_connection(str(db_path))

    await sync(lang=lang, workers=workers, batch_size=batch_size, conn=conn)

    if conn:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync TCGdex data to SQLite.")
    parser.add_argument(
        "--lang",
        default="en",
        metavar="LANG",
        help="Language code to sync, e.g. --lang fr (default: en)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="Max concurrent card fetches (default: 20)",
    )
    parser.add_argument(
        "--batch", type=int, default=500, help="DB commit every N cards (default: 500)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Fetch without writing to the database"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.dry_run:
        log.info("Dry-run mode — no data will be written.")

    try:
        asyncio.run(
            run(
                lang=args.lang,
                workers=args.workers,
                batch_size=args.batch,
                dry_run=args.dry_run,
            )
        )
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
