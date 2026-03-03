import os
import json
import requests
from bs4 import BeautifulSoup
import traceback

# Crawler for OCCRP (Organized Crime and Corruption Reporting Project) RSS/Atom feed
# Fetches recent items from the feed and appends them as JSON lines to agent/data/raw_data.json
# The script runs once and exits.

FEED_URL = "https://www.occrp.org/en/feed"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
MAX_ITEMS = 8  # number of recent feed items to include
USER_AGENT = "osint-agent/1.0 (+https://example.org)"


def fetch_feed(url, timeout=15):
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    # Let requests determine encoding; return text
    return resp.text


def _get_tag_text(tag):
    if not tag:
        return ""
    # Tag may contain nested tags; use get_text to retrieve all text content
    try:
        return tag.get_text(separator=" ", strip=True)
    except Exception:
        # Fallback to string coercion
        return str(tag.string or "").strip()


def _extract_link(item_tag):
    # RSS: <link>http...</link>
    # Atom: <link href="..." rel="alternate" .../>
    link_tag = item_tag.find("link")
    if not link_tag:
        return ""
    # If link tag has href attribute (atom)
    href = link_tag.get("href")
    if href:
        return href.strip()
    # Otherwise, the link may be the text content (RSS)
    text = _get_tag_text(link_tag)
    return text.strip()


def parse_feed(xml_text, max_items=MAX_ITEMS):
    soup = BeautifulSoup(xml_text, "xml")
    # Support both RSS (<item>) and Atom (<entry>)
    items = soup.find_all(["item", "entry"])
    results = []
    for item in items[:max_items]:
        # Title: <title>
        title = _get_tag_text(item.find("title"))
        # Link: handle atom and rss
        link = _extract_link(item)
        # pubDate (RSS) or updated/published (Atom)
        pubdate = _get_tag_text(item.find("pubDate")) or _get_tag_text(item.find("updated")) or _get_tag_text(item.find("published"))
        # description (RSS) or summary/content (Atom). Keep plain text.
        description_tag = item.find("description") or item.find("summary") or item.find("content")
        description = ""
        if description_tag:
            # description_tag may contain HTML inside CDATA; parse with html parser and extract text
            inner = description_tag.string if description_tag.string is not None else description_tag.decode_contents()
            desc_soup = BeautifulSoup(inner or "", "html.parser")
            description = desc_soup.get_text(separator=" ").strip()
        entry = {
            "title": title,
            "link": link,
            "pubDate": pubdate,
            "description": description,
        }
        results.append(entry)
    return results


def build_content(source, entries):
    parts = [f"Source: {source}"]
    for e in entries:
        parts.append("---")
        parts.append(f"Title: {e.get('title', '')}")
        parts.append(f"Link: {e.get('link', '')}")
        if e.get("pubDate"):
            parts.append(f"Published: {e.get('pubDate')}")
        if e.get("description"):
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


def main():
    try:
        xml = fetch_feed(FEED_URL)
        entries = parse_feed(xml)
        content = build_content("occrp.org", entries)
        data = {"source": "occrp.org", "content": content, "count": len(entries)}
        append_json_record(OUTPUT_PATH, data)
        print(f"Appended {len(entries)} items from OCCRP to {OUTPUT_PATH}")
    except Exception as e:
        # Write an error record for later inspection (include traceback)
        try:
            tb = traceback.format_exc()
            error_record = {"source": "occrp.org", "content": f"ERROR: {str(e)}", "traceback": tb}
            append_json_record(OUTPUT_PATH, error_record)
        except Exception:
            # If write fails, print traceback to stderr (best-effort)
            print("Failed to write error record:", traceback.format_exc())
        print(f"Crawler failed: {e}")


if __name__ == "__main__":
    main()