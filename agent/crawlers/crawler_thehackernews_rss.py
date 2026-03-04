import os
import json
import requests
from bs4 import BeautifulSoup

# Crawler for The Hacker News RSS feed
# Fetches recent items from the RSS feed, visits each article page,
# extracts readable text, and appends JSON entries to agent/data/raw_data.json

RSS_URL = "https://feeds.feedburner.com/TheHackersNews"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OSINT-Agent/1.0; +https://example.com)"
}


def ensure_output_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def fetch_rss(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_rss_items(rss_xml, limit=5):
    soup = BeautifulSoup(rss_xml, "xml")
    items = soup.find_all("item")
    parsed = []
    for item in items[:limit]:
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        title = title_tag.get_text(strip=True) if title_tag else None
        link = link_tag.get_text(strip=True) if link_tag else None
        description = desc_tag.get_text(strip=True) if desc_tag else None
        parsed.append({"title": title, "link": link, "description": description})
    return parsed


def fetch_article_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        page = resp.text
        soup = BeautifulSoup(page, "html.parser")

        # Heuristics: try common article containers
        selectors = [
            "article",
            "div[itemprop=articleBody]",
            "div.post-body",
            "div.entry-content",
            "div.content",
            "div.article-content",
            "div.post",
            "main",
        ]

        paragraphs = []
        for sel in selectors:
            container = soup.select_one(sel)
            if container:
                ps = container.find_all("p")
                for p in ps:
                    text = p.get_text(separator=" ", strip=True)
                    if text:
                        paragraphs.append(text)
                if paragraphs:
                    break

        # Fallback: collect all <p> from page but filter very short ones
        if not paragraphs:
            for p in soup.find_all("p"):
                text = p.get_text(separator=" ", strip=True)
                if text and len(text) > 40:
                    paragraphs.append(text)

        content = "\n\n".join(paragraphs).strip()
        return content if content else None
    except Exception:
        return None


if __name__ == "__main__":
    try:
        ensure_output_dir(OUTPUT_PATH)

        rss_xml = fetch_rss(RSS_URL)
        items = parse_rss_items(rss_xml, limit=6)

        if not items:
            entry = {"source": "thehackernews_rss", "content": "No items found in RSS feed."}
            with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        else:
            for it in items:
                title = it.get("title") or ""
                link = it.get("link")
                desc = it.get("description") or ""

                article_text = None
                if link:
                    article_text = fetch_article_text(link)

                combined = []
                if title:
                    combined.append(title)
                if desc:
                    combined.append(desc)
                if article_text:
                    combined.append(article_text)

                content = "\n\n".join(combined).strip()
                if not content:
                    content = f"Unable to extract content for link: {link}" if link else "No content extracted."

                entry = {"source": "thehackernews", "content": content}

                # Append one JSON object per line
                with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception as e:
        # On error, attempt to write an error entry so the system can track failures
        try:
            ensure_output_dir(OUTPUT_PATH)
            err_entry = {"source": "thehackernews", "content": f"ERROR: {str(e)}"}
            with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(err_entry, ensure_ascii=False) + "\n")
        except Exception:
            # If even writing fails, silently exit (no infinite loops)
            pass
