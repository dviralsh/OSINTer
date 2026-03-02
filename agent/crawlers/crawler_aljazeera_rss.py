#!/usr/bin/env python3
import os
import sys
import json
import re
import html
from datetime import datetime, timezone

try:
    import requests
except Exception:
    print("Missing dependency: requests. Install with `pip install requests`.", file=sys.stderr)
    sys.exit(1)

import xml.etree.ElementTree as ET

FEED_URL = "https://www.aljazeera.com/xml/rss/all.xml"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
REQUEST_TIMEOUT = 15  # seconds
USER_AGENT = "aljazeera-rss-crawler/1.0 (+https://example.com)"

TAG_RE = re.compile(r"<[^>]+>")

def fetch_feed(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise RuntimeError(f"Network error when fetching feed: {e}") from e
    if resp.status_code != 200:
        raise RuntimeError(f"Unexpected HTTP status {resp.status_code} when fetching feed.")
    content = resp.content
    if not content:
        raise RuntimeError("Received empty content from feed.")
    return content

def text_of(element):
    if element is None:
        return ""
    # element.text might be None
    return element.text or ""

def clean_html_text(s):
    if not s:
        return ""
    # Unescape HTML entities, remove tags, collapse whitespace
    s = html.unescape(s)
    s = TAG_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_rss(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse XML: {e}") from e

    items = []
    # Find all item elements regardless of top-level structure
    for item_el in root.findall(".//item"):
        title = clean_html_text(text_of(item_el.find("title")))
        link = text_of(item_el.find("link"))
        # Some feeds put link in <guid isPermaLink="true"> or just guid
        guid = text_of(item_el.find("guid")) or link
        pubDate = text_of(item_el.find("pubDate"))
        description = clean_html_text(text_of(item_el.find("description")))

        # Attempt to extract an image URL if present in media:content or enclosure
        image = ""
        # look for enclosure tag with type image/*
        enclosure = item_el.find("enclosure")
        if enclosure is not None and "type" in enclosure.attrib and enclosure.attrib.get("type", "").startswith("image"):
            image = enclosure.attrib.get("url", "") or ""
        # check for media:content (namespace aware)
        if not image:
            for child in item_el:
                tag = child.tag
                if tag.lower().endswith("content") and "url" in child.attrib:
                    # media:content
                    image = child.attrib.get("url", "")
                    break

        items.append({
            "source": "aljazeera",
            "title": title,
            "link": link,
            "guid": guid,
            "published": pubDate,
            "summary": description,
            "image": image,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return items

def ensure_output_dir(path):
    d = os.path.dirname(path)
    if not d:
        return
    os.makedirs(d, exist_ok=True)

def append_ndjson(path, items):
    ensure_output_dir(path)
    # Append newline-delimited JSON objects
    written = 0
    try:
        with open(path, "a", encoding="utf-8") as fh:
            for item in items:
                # Ensure it's JSON serializable (datetimes already converted to isoformat)
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
                written += 1
    except Exception as e:
        raise RuntimeError(f"Failed writing to {path}: {e}") from e
    return written

def main():
    try:
        content = fetch_feed(FEED_URL)
        items = parse_rss(content)
        if not items:
            print("No items found in feed.")
            sys.exit(0)
        count = append_ndjson(OUTPUT_PATH, items)
        print(f"Appended {count} items to {OUTPUT_PATH}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()