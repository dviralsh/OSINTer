import os
import json
import requests
from bs4 import BeautifulSoup

# Crawler for OCCRP (Organized Crime and Corruption Reporting Project) RSS feed
# Fetches recent items from the feed and appends them as JSON strings to agent/data/raw_data.json

FEED_URL = "https://www.occrp.org/en/feed"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
MAX_ITEMS = 8  # number of recent feed items to include


def fetch_feed(url):
    headers = {"User-Agent": "osint-agent/1.0 (+https://example.org)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_feed(xml_text, max_items=MAX_ITEMS):
    soup = BeautifulSoup(xml_text, "xml")
    items = soup.find_all("item")
    results = []
    for i, item in enumerate(items[:max_items]):
        title = item.title.string if item.title else ""
        link = item.link.string if item.link else ""
        pubdate = item.pubDate.string if item.pubDate else ""
        # description may contain HTML; keep plain text
        description = ""
        if item.description:
            desc_soup = BeautifulSoup(item.description.string or "", "html.parser")
            description = desc_soup.get_text(separator=" ").strip()
        entry = {
            "title": title.strip(),
            "link": link.strip(),
            "pubDate": pubdate.strip(),
            "description": description
        }
        results.append(entry)
    return results


def build_content(source, entries):
    parts = [f"Source: {source}"]
    for e in entries:
        parts.append("---")
        parts.append(f"Title: {e.get('title', '')}")
        parts.append(f"Link: {e.get('link', '')}")
        if e.get('pubDate'):
            parts.append(f"Published: {e.get('pubDate')}")
        if e.get('description'):
            parts.append(f"Description: {e.get('description')}")
    return "\n".join(parts)


def ensure_output_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def append_json_record(path, record):
    ensure_output_dir(path)
    # Append as a single JSON string per line
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        xml = fetch_feed(FEED_URL)
        entries = parse_feed(xml)
        content = build_content("occrp.org", entries)
        data = {"source": "occrp.org", "content": content}
        append_json_record(OUTPUT_PATH, data)
        # Optionally print a short success message
        print(f"Appended {len(entries)} items from OCCRP to {OUTPUT_PATH}")
    except Exception as e:
        # Catch all exceptions so the script exits gracefully
        # Write an error record to the same file for later inspection
        try:
            error_record = {"source": "occrp.org", "content": f"ERROR: {str(e)}"}
            append_json_record(OUTPUT_PATH, error_record)
        except Exception:
            pass
        print(f"Crawler failed: {e}")
