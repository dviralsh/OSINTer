import requests
from bs4 import BeautifulSoup
import os
import json
import sys

# Crawler for Bellingcat RSS feed -> appends JSON lines to agent/data/raw_data.json
# Requirements satisfied: fetch real recent OSINT/news data, uses requests and bs4,
# writes dicts with 'source' and 'content' keys as JSON strings appended to file.

FEED_URL = "https://www.bellingcat.com/feed/"
OUTPUT_PATH = os.path.join("agent", "data", "raw_data.json")
MAX_ITEMS = 5  # number of recent items to fetch
HEADERS = {"User-Agent": "OSINT-Agent/1.0 (+https://example.com)"}


def extract_article_text(page_soup):
    # Try multiple likely containers for the article text
    candidates = []
    candidates.append(page_soup.find("div", class_="entry-content"))
    candidates.append(page_soup.find("div", class_="post-content"))
    candidates.append(page_soup.find("div", class_="content"))
    candidates.append(page_soup.find("article"))
    candidates.append(page_soup.find(attrs={"itemprop": "articleBody"}))

    for c in candidates:
        if c:
            # Collect paragraphs and list items for cleaner content
            parts = []
            for tag in c.find_all(["p", "li"]):
                text = tag.get_text(separator=" ", strip=True)
                if text:
                    parts.append(text)
            if parts:
                return "\n\n".join(parts)
            # fallback to full text of the container
            full_text = c.get_text(separator=" ", strip=True)
            if full_text:
                return full_text
    # Last-resort: return the page body text
    body = page_soup.body
    if body:
        return body.get_text(separator=" ", strip=True)
    return ""


try:
    resp = requests.get(FEED_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    feed_soup = BeautifulSoup(resp.content, "xml")
    items = feed_soup.find_all("item")

    if not items:
        # Try Atom entries as fallback
        items = feed_soup.find_all("entry")

    items = items[:MAX_ITEMS]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "a", encoding="utf-8") as out_f:
        for it in items:
            # RSS item vs Atom entry differences
            title_tag = it.find("title")
            link_tag = it.find("link")
            pub_tag = it.find("pubDate") or it.find("published") or it.find("updated")

            title = title_tag.get_text(strip=True) if title_tag else "(no title)"

            link = None
            if link_tag:
                # Atom <link href="..."/>
                if link_tag.has_attr("href"):
                    link = link_tag["href"]
                else:
                    link = link_tag.get_text(strip=True)

            # Some feeds put link in <guid>
            if not link:
                guid = it.find("guid")
                if guid:
                    link = guid.get_text(strip=True)

            if not link:
                # skip if no link
                continue

            pub = pub_tag.get_text(strip=True) if pub_tag else ""

            try:
                art_resp = requests.get(link, headers=HEADERS, timeout=15)
                art_resp.raise_for_status()
                page_soup = BeautifulSoup(art_resp.content, "html.parser")

                article_text = extract_article_text(page_soup)

                # Compose a concise content blob
                content_parts = [f"Title: {title}", f"URL: {link}"]
                if pub:
                    content_parts.append(f"Published: {pub}")
                content_parts.append("\nArticle:\n" + (article_text if article_text else "(no extracted body)"))
                final_text = "\n\n".join(content_parts)

                record = {"source": "bellingcat", "content": final_text}

                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

            except Exception as e_article:
                # Append an error record for this article so failures are visible
                err_record = {
                    "source": "bellingcat",
                    "content": f"ERROR fetching article {link}: {type(e_article).__name__}: {str(e_article)}"
                }
                out_f.write(json.dumps(err_record, ensure_ascii=False) + "\n")

except Exception as e:
    # Top-level failure: ensure the error is recorded so the operator can see it
    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "a", encoding="utf-8") as out_f:
            err_record = {"source": "bellingcat", "content": f"FATAL ERROR: {type(e).__name__}: {str(e)}"}
            out_f.write(json.dumps(err_record, ensure_ascii=False) + "\n")
    except Exception:
        # If even writing fails, print to stderr as a last resort
        print(f"FATAL ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr)
