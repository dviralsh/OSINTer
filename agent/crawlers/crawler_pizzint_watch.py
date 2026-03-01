import requests
from bs4 import BeautifulSoup
import time
import random
import os
import json
import traceback
from datetime import datetime


def fetch_url_with_retries(url, max_attempts=5, init_delay=2, factor=2, timeout=10):
    attempt = 0
    delay = init_delay
    last_exception = None
    while attempt < max_attempts:
        try:
            headers = {
                "User-Agent": "crawler_pizzint_watch/1.0 (+https://pizzint.watch)"
            }
            start = time.time()
            resp = requests.get(url, headers=headers, timeout=timeout)
            latency_ms = int((time.time() - start) * 1000)

            # Treat non-200 and empty bodies as errors to trigger retry
            if resp is None:
                raise ValueError("Null response")
            if resp.status_code != 200:
                raise ValueError(f"Unexpected status: {resp.status_code}")
            if resp.content is None or len(resp.content) == 0:
                raise ValueError("Empty response body")

            return resp
        except Exception as e:
            last_exception = e
            attempt += 1
            # exponential backoff with jitter
            jitter = random.uniform(0, 1)
            sleep_time = min(delay, 32) + jitter
            time.sleep(sleep_time)
            delay *= factor
    # after retries
    raise last_exception


def extract_text_from_html(html, url):
    soup = BeautifulSoup(html, "html.parser")

    # Prefer article tags
    parts = []
    # Try to get page title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        parts.append(title_tag.string.strip())

    # Collect text from <article> tags
    for article in soup.find_all("article"):
        for p in article.find_all(["p", "h1", "h2", "h3"]):
            t = p.get_text(separator=" ", strip=True)
            if t:
                parts.append(t)

    # Fallback: collect main content paragraphs
    if not parts:
        for p in soup.find_all("p"):
            t = p.get_text(separator=" ", strip=True)
            if t:
                parts.append(t)

    # As a last resort, extract all visible text
    if not parts:
        body = soup.get_text(separator=" ", strip=True)
        if body:
            parts.append(body)

    # Join and trim
    content = "\n\n".join(parts).strip()
    return content


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def append_record_to_file(record, filepath):
    ensure_directory(os.path.dirname(filepath) or ".")
    # atomic-ish write: write to temp file then append
    # but since multiple processes might append, keep it simple: append newline-delimited JSON
    with open(filepath, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    target = "https://pizzint.watch"
    out_path = os.path.join("agent", "data", "raw_data.json")
    timestamp = datetime.utcnow().isoformat() + "Z"

    record = {
        "source": target,
        "content": "",
        "fetched_at": timestamp
    }

    try:
        resp = fetch_url_with_retries(target)
        html = resp.text
        extracted = extract_text_from_html(html, target)

        if not extracted:
            # explicit empty-body handling
            record["content"] = ""
            record["error"] = "EMPTY_BODY"
            record["http_status"] = resp.status_code
        else:
            record["content"] = extracted
            record["http_status"] = resp.status_code

    except Exception as e:
        # On any error, write a structured record (still contains 'source' and 'content')
        record["content"] = ""
        record["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "trace": traceback.format_exc().splitlines()[-1]
        }

    try:
        append_record_to_file(record, out_path)
    except Exception:
        # If writing the file fails, print the error to stdout/stderr but do not raise
        print("Failed to write output file:", traceback.format_exc())


if __name__ == "__main__":
    main()
