import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import logging
import sys
from email.utils import parsedate_to_datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def fetch_rss(url: str, timeout: int = 10) -> bytes:
    headers = {
        "User-Agent": "osint-crawler/1.0 (+https://example.local/)"
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def parse_items(xml_content: bytes):
    # Use the XML parser
    soup = BeautifulSoup(xml_content, "xml")
    items = soup.find_all("item")
    results = []

    for item in items:
        # Use get_text to handle CDATA and nested tags; strip whitespace
        def txt(tag_name):
            t = item.find(tag_name)
            return t.get_text(strip=True) if t and t.get_text(strip=True) != "" else None

        title = txt("title")
        link = txt("link")
        description = txt("description")
        guid = txt("guid")
        pub_date_raw = txt("pubDate")

        # Try to normalize pubDate to ISO 8601 if possible, otherwise keep raw string
        pub_date = None
        if pub_date_raw:
            try:
                dt = parsedate_to_datetime(pub_date_raw)
                # parsedate_to_datetime may return naive datetime in some cases; use isoformat()
                pub_date = dt.isoformat()
            except Exception:
                pub_date = pub_date_raw

        news_item = {
            "title": title,
            "link": link,
            "description": description,
            "pubDate": pub_date,
            "pubDateRaw": pub_date_raw,
            "guid": guid,
            "source": "aljazeera",
        }

        results.append(news_item)

    return results


def append_json_lines(path: Path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Append newline-delimited JSON (NDJSON), UTF-8, preserve unicode characters
    with path.open("a", encoding="utf-8") as fh:
        for it in items:
            json_line = json.dumps(it, ensure_ascii=False)
            fh.write(json_line + "\n")


def main():
    url = "https://www.aljazeera.com/xml/rss/all.xml"
    out_path = Path("agent/data/raw_data.json")

    try:
        logging.info("Fetching RSS feed from %s", url)
        content = fetch_rss(url)
        logging.info("Parsing feed")
        items = parse_items(content)

        if not items:
            logging.warning("No items found in feed.")
        else:
            logging.info("Appending %d items to %s", len(items), out_path)
            append_json_lines(out_path, items)

        logging.info("Finished successfully.")
    except requests.RequestException as re:
        logging.exception("Network or HTTP error while fetching the RSS feed: %s", re)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()