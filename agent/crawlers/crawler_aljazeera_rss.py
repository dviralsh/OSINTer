#!/usr/bin/env python3
import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# Configuration
FEED_URL = "https://www.aljazeera.com/xml/rss/all.xml"
OUTPUT_PATH = Path("agent/data/raw_data.json")
REQUEST_TIMEOUT = 15  # seconds
MAX_ITEMS = 200  # safety cap on items to process

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def fetch_feed(url: str, timeout: int = REQUEST_TIMEOUT) -> bytes:
    headers = {
        "User-Agent": "osint-crawler/1.0 (+https://example.com)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def local_name(tag: str) -> str:
    # Extract localname from a possibly namespaced tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def find_child_text(elem: ET.Element, name: str) -> Optional[str]:
    # Find child by local name (handles namespaces) and return its text stripped, or None
    for child in elem:
        if local_name(child.tag).lower() == name.lower():
            if child.text is None:
                return None
            return child.text.strip()
    return None


def parse_pubdate_to_iso(pubdate: Optional[str]) -> Optional[str]:
    if not pubdate:
        return None
    try:
        dt = parsedate_to_datetime(pubdate)
        # Ensure timezone-aware; parsedate_to_datetime may return naive in some environments
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            # fallback: try to parse some common formats
            parsed = datetime.fromisoformat(pubdate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except Exception:
            return None


def parse_feed(xml_bytes: bytes, max_items: int = MAX_ITEMS) -> List[Dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logging.error("Failed to parse XML feed: %s", e)
        return []

    items: List[Dict] = []
    # Find item elements anywhere under the root
    for item in root.findall(".//item"):
        if len(items) >= max_items:
            break

        title = find_child_text(item, "title")
        link = find_child_text(item, "link")
        description = find_child_text(item, "description")
        guid = find_child_text(item, "guid")
        pubdate_raw = find_child_text(item, "pubdate") or find_child_text(item, "pubDate")  # try both casings
        published_at = parse_pubdate_to_iso(pubdate_raw)
        # Some feeds include media:content or media:thumbnail with url attribute
        media_url = None
        for child in item:
            if local_name(child.tag).lower() in ("content", "thumbnail", "enclosure"):
                url = child.attrib.get("url")
                if url:
                    media_url = url
                    break

        # Basic validation: require at least title or link
        if not title and not link:
            logging.debug("Skipping item without title and link")
            continue

        record = {
            "source": "aljazeera_rss",
            "scraped_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "title": title,
            "link": link,
            "description": description,
            "guid": guid,
            "published_at": published_at,
            "media_url": media_url,
        }
        items.append(record)

    logging.info("Parsed %d items from feed", len(items))
    return items


def ensure_output_dir(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def append_json_lines(path: Path, records: List[Dict]) -> None:
    ensure_output_dir(path)
    # Append newline-delimited JSON objects
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            try:
                line = json.dumps(rec, ensure_ascii=False)
                f.write(line + "\n")
            except Exception as e:
                logging.warning("Failed to serialize record: %s. Error: %s", rec, e)


def main():
    try:
        logging.info("Fetching feed: %s", FEED_URL)
        xml = fetch_feed(FEED_URL)
        items = parse_feed(xml)
        if not items:
            logging.info("No items to write. Exiting.")
            return
        append_json_lines(OUTPUT_PATH, items)
        logging.info("Appended %d records to %s", len(items), OUTPUT_PATH)
    except requests.RequestException as e:
        logging.error("Network error while fetching feed: %s", e)
    except Exception as e:
        logging.exception("Unexpected error: %s", e)


if __name__ == "__main__":
    main()