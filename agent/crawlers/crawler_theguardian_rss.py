import requests
from bs4 import BeautifulSoup
import json
import os

# This crawler fetches recent items from The Guardian World RSS feed,
# extracts article text when possible, and appends a JSON string
# containing {'source': ..., 'content': ...} to agent/data/raw_data.json

try:
    FEED_URL = "https://www.theguardian.com/world/rss"
    resp = requests.get(FEED_URL, timeout=15)
    resp.raise_for_status()

    feed_soup = BeautifulSoup(resp.content, "xml")
    items = feed_soup.find_all("item")[:6]  # take up to 6 recent items

    entries = []

    for item in items:
        title = item.title.text.strip() if item.title else ""
        link = item.link.text.strip() if item.link else ""
        description = item.description.text.strip() if item.description else ""

        article_text = ""
        if link:
            try:
                art_r = requests.get(link, timeout=15)
                art_r.raise_for_status()
                art_soup = BeautifulSoup(art_r.content, "html.parser")

                # The Guardian uses a few possible container class names for article body
                body = None
                for cls in ("article-body-commercial-selector", "content__article-body", "article-body-viewer-selector"):
                    body = art_soup.find("div", {"class": cls})
                    if body:
                        break

                if not body:
                    # fallback: try to locate by role or main article tag
                    body = art_soup.find("main") or art_soup.find("article")

                if body:
                    paragraphs = body.find_all("p")
                    article_text = "\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs if p.get_text(strip=True))

            except Exception:
                # On any article fetch/parsing error, fall back to the RSS description
                article_text = ""

        if not article_text:
            article_text = description or f"(No article text available for {title})"

        entries.append({
            "title": title,
            "url": link,
            "content": article_text,
        })

    # Combine entries into a single content blob for storage
    combined_parts = []
    for e in entries:
        header = f"{e['title']}\n{e['url']}" if e.get('url') else e['title']
        combined_parts.append(header + "\n\n" + e.get('content', ''))

    combined_text = "\n\n---\n\n".join(combined_parts)

    out = {
        "source": "The Guardian - World RSS",
        "content": combined_text,
    }

    os.makedirs("agent/data", exist_ok=True)
    out_path = os.path.join("agent", "data", "raw_data.json")

    # Append a JSON string (one per line) as required
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False) + "\n")

except Exception as exc:
    # On error, still append an error record so the system knows the crawler ran
    try:
        os.makedirs("agent/data", exist_ok=True)
        err = {"source": "crawler_theguardian_rss_error", "content": f"{type(exc).__name__}: {str(exc)}"}
        with open(os.path.join("agent", "data", "raw_data.json"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(err, ensure_ascii=False) + "\n")
    except Exception:
        # If even logging fails, raise the original exception
        pass
    raise