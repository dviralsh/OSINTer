import os
import json
import requests
import hashlib
import html
import re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# Configuration
RSS_URL = "http://feeds.reuters.com/reuters/topNews"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
HTTP_TIMEOUT = 10  # seconds
USER_AGENT = "Mozilla/5.0 (compatible; ReutersRSSCrawler/1.0; +https://example.com/bot)"


def ensure_output_dir(path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def sanitize_text(text: str | None) -> str:
    if not text:
        return ""
    # Unescape HTML entities
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_rss_items(xml_bytes: bytes) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse RSS XML: {e}")

    # Find all item elements regardless of namespace
    # ET supports .// for nested search
    for item in root.findall(".//item"):
        title = sanitize_text(item.findtext("title"))
        link = sanitize_text(item.findtext("link"))
        description = sanitize_text(item.findtext("description"))
        pub_date = sanitize_text(item.findtext("pubDate"))
        guid = sanitize_text(item.findtext("guid"))

        # If guid missing, fallback to link or hash of title+link
        unique_source = guid or link or (title[:200] if title else "")
        uid = hashlib.sha256(unique_source.encode("utf-8")).hexdigest()

        items.append(
            {
                "id": uid,
                "source": "reuters-rss",
                "source_url": RSS_URL,
                "title": title,
                "summary": description,
                "link": link,
                "published": pub_date,
                "guid": guid,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return items


def fetch_rss(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"}
    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.content


def append_json_lines(path: str, items: list[dict]):
    # Append newline-delimited JSON for each item (NDJSON)
    ensure_output_dir(path)
    with open(path, "a", encoding="utf-8") as fh:
        for item in items:
            json_line = json.dumps(item, ensure_ascii=False)
            fh.write(json_line + "\n")


def main():
    try:
        xml = fetch_rss(RSS_URL)
    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        return

    try:
        items = parse_rss_items(xml)
    except Exception as e:
        print(f"Error parsing RSS feed: {e}")
        return

    if not items:
        print("No items found in RSS feed.")
        return

    try:
        append_json_lines(OUTPUT_PATH, items)
    except Exception as e:
        print(f"Error writing output file: {e}")
        return

    print(f"Successfully appended {len(items)} items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()