"""Asynchronous links parser."""

import asyncio
import logging
import os
import sys
from datetime import datetime

from aiofiles import open as aopen
from aiohttp import ClientError, ClientSession
from bs4 import BeautifulSoup, FeatureNotFound
from bs4.element import NavigableString, Tag

from app.db.query import get_last_date
from app.db.setup import run_pg_session

CHUNK_SIZE = 8192  # 8 Kb

lgr = logging.getLogger(__name__)


async def fetch_html(session: ClientSession, url: str) -> str:
    """
    Asynchronously fetch HTML content from a given URL.

    Args:
        session (ClientSession): The session for making HTTP requests.
        url (str): The URL to fetch.

    Returns:
        str: HTML content of the page.
    """
    try:
        async with session.get(url) as response:
            return await response.text()
    except ClientError as e:
        lgr.error(f"Error fetching URL: {url}", exc_info=e)
        raise e
    except asyncio.TimeoutError:
        lgr.error("Request timed out.")
        sys.exit(1)


async def parse_html(session: ClientSession, abs_url: str) -> BeautifulSoup:
    """Parse the HTML content and return a BeautifulSoup object.

    Args:
        session (ClientSession): The session for making HTTP requests.
        abs_url (str): Absolute URL of the page to fetch.

    Returns:
        BeautifulSoup: The requested page as a BeautifulSoup object.

    Raises:
        ValueError: If response of requested resourse is empty.
        FeatureNotFound: If it's not possible to create a BS object.
    """
    raw_html_content: str | None = await fetch_html(session, abs_url)
    if not raw_html_content:
        raise ValueError("The resourse sent an empty response.")

    try:
        return BeautifulSoup(raw_html_content, "lxml")
    except FeatureNotFound as e:
        raise FeatureNotFound(e)


async def fetch_links(
    session: ClientSession,
    base_url: str,
    start_url: str,
    links: list[tuple[str, str] | None],
) -> None:
    """
    Asynchronously parse HTML and extract download links from the web page.

    Args:
        session (ClientSession): Opened async session for HTTP requests.
        base_url (str): Domain of the parsing site.
        start_url (str): The starting relative URL for scraping.

    Returns:
        links: list[tuple[str, str] | None]: Extracted links.
            Each tuple contains an URL and a file name.
            None is passed as the last element
    """
    current_page: str = start_url
    page_count = 0
    links_count = 0

    while True:
        page_count += 1
        lgr.debug(f"Iterating #{page_count} with '{current_page}'")
        abs_url: str = base_url + current_page
        soup: BeautifulSoup = await parse_html(session, abs_url)

        # собрать все блоки со ссылками
        link_blocks = soup.select("div.accordeon-inner__wrap-item")

        stop_parsing = False
        for item in link_blocks:
            link_tag = item.find("a")
            if not isinstance(link_tag, Tag):
                raise ValueError(
                    f"'{link_tag}' element must be a Tag instance, "
                    f"not '{type(link_tag)}'"
                )

            # извлечь ссылки, сохранить в список
            if "Бюллетень" in (link_tag.string or ""):
                span_tag = item.find("span")
                if not isinstance(span_tag, Tag):
                    raise ValueError(
                        f"'{span_tag}' element must be a Tag instance, "
                        f"not '{type(span_tag)}'"
                    )

                date_str = span_tag.string
                if not isinstance(date_str, NavigableString):
                    raise ValueError(
                        f"'{date_str}' element must be a Tag instance, "
                        f"not '{type(date_str)}'"
                    )

                date = datetime.strptime(date_str, "%d.%m.%Y")
                last_dt: datetime | None = await run_pg_session(get_last_date)
                if (last_dt and date <= last_dt) or date.year == 2022:
                    lgr.warning("Stop links parsing.")
                    stop_parsing = True
                    # выход из for
                    break

                f_path = link_tag.get("href")
                if not isinstance(f_path, str):
                    raise ValueError(
                        f"'{f_path}' element must be a string, "
                        f"not '{type(f_path)}'"
                    )
                if not f_path.startswith("/"):
                    f_path = "/" + f_path

                link = base_url + f_path
                ext = f_path.split("?")[0].split("/")[-1].split(".")[-1]
                filename = f"{date_str}.{ext}"

                # сохранить очередную ссылку
                links.append((link, filename))
                links_count += 1
                lgr.debug(
                    f"Save link {links_count}: '{link}' for file '{filename}'"
                )
            else:
                break

        if stop_parsing:
            # выход из while
            break

        # поиск кнопки пагинации
        pag_btn = soup.select_one(".bx-pag-next")
        if pag_btn:
            link_next_tag = pag_btn.find("a")
            if not isinstance(link_next_tag, Tag):
                raise ValueError(
                    f"'{link_next_tag}' element must be a Tag instance, "
                    f"not '{type(link_next_tag)}'"
                )

            link_str = link_next_tag.get("href")
            if not isinstance(link_str, str):
                raise ValueError(
                    f"'{link_str}' element must be a string instance, "
                    f"not '{type(link_str)}'"
                )

            current_page = link_str
        else:
            break


async def get_file(
    session: ClientSession,
    url: str,
    dest_dir: str,
    filename: str,
) -> None:
    """
    Download the file and save it to file system.

    Args:
        url (str): Direct link to download file.
        filename (str): Specify a file name.
        dest_dir (str): Specify the location to save the file.
    """
    file_path: str = os.path.join(dest_dir, filename)
    try:
        async with session.get(url) as response:
            async with aopen(file_path, "wb") as f:
                while chunk := await response.content.read(CHUNK_SIZE):
                    await f.write(chunk)
        lgr.debug(f"Download successful to: {file_path}")
    except ClientError as e:
        lgr.error(f"Download failed: {filename}", exc_info=e)


async def download(
    session: ClientSession,
    links: list,
    dest_dir: str = "temp",
) -> None:
    """
    Save all files.

    Args:
        session (ClientSession): Opened async session for HTTP requests.
        links (list): Links to files for downloading.
        dest_dir (str): Specify the location to save the file.
    """
    lgr.info("Start download files.")
    download_tasks = [
        get_file(session, url, dest_dir, filename) for url, filename in links
    ]
    await asyncio.gather(*download_tasks)
    lgr.info(f"Downloaded {len(links)} files.")
