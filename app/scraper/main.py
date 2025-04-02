"""Main entrypoint to the async scraper."""

import asyncio
import logging
import os
import shutil
import time

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from app.db.query import create_data
from app.db.setup import run_pg_session
from app.scraper.extracter import async_extract
from app.scraper.scraper import download, fetch_links
from app.utils.tools import scrap_event

lgr = logging.getLogger(__name__)


async def main() -> None:
    """
    Run web scrapper.

    Create an aiohttp session and parse links to downloading files.
    Download all needed files from the resourse.
    Extract data files using pandas in the process pull.
    Save all data to postgresql db.
    """
    start: float = time.perf_counter()

    headers: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36",
    }
    domain = "https://spimex.com"
    start_url = "/markets/oil_products/trades/results/"
    dest_dir = "downloads"
    links: list[tuple[str, str] | None] = []

    os.makedirs(dest_dir, exist_ok=True)

    timeout = ClientTimeout(total=600, connect=10)
    connector = TCPConnector(
        limit=100,
        ttl_dns_cache=300,
    )

    scrap_event.set()
    try:
        async with ClientSession(
            timeout=timeout,
            connector=connector,
            raise_for_status=True,
            headers=headers,
        ) as session:
            await fetch_links(session, domain, start_url, links)
            await download(session, links, dest_dir)

        data_to_db: list = await async_extract(dest_dir)
        await run_pg_session(create_data, data_to_db)
    finally:
        shutil.rmtree(dest_dir)
        scrap_event.clear()

    elapsed: float = time.perf_counter() - start
    lgr.info(f"The scraper worked in {elapsed:.4f} seconds.")
    # The scraper worked in 40.9596 seconds.


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(lineno)d | %(asctime)s | %(name)s | "
        "%(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(main())
