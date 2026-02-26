import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import sys

FEED_URL = 'https://feeds.bbci.co.uk/news/rss.xml'
OUTPUT_PATH = Path('agent/data/raw_data.json')
HEADERS = {'User-Agent': 'OSINT-crawler/1.0 (+https://example.local)'}


def parse_pubdate(text):
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def normalize_description(desc_html):
    if not desc_html:
        return ''
    # Unescape HTML entities and strip HTML tags
    unescaped = html.unescape(desc_html)
    return BeautifulSoup(unescaped, 'html.parser').get_text(separator=' ', strip=True)


def fetch_feed(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.content


def extract_items(xml_content):
    soup = BeautifulSoup(xml_content, 'xml')
    items = soup.find_all('item')
    results = []
    fetched_at = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    for item in items:
        title_tag = item.find('title')
        desc_tag = item.find('description')
        link_tag = item.find('link')
        guid_tag = item.find('guid')
        pub_tag = item.find('pubDate')

        title = title_tag.text.strip() if title_tag and title_tag.text else ''
        description = normalize_description(desc_tag.text if desc_tag and desc_tag.text else '')
        link = link_tag.text.strip() if link_tag and link_tag.text else ''
        guid = guid_tag.text.strip() if guid_tag and guid_tag.text else ''
        published_at = parse_pubdate(pub_tag.text if pub_tag and pub_tag.text else None)

        record = {
            'source': 'BBC',
            'title': title,
            'description': description,
            'link': link,
            'guid': guid,
            'published_at': published_at,
            'fetched_at': fetched_at
        }
        results.append(record)
    return results


def append_ndjson(records, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Append one JSON object per line (NDJSON) to keep file valid when appending
    with path.open('a', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def main():
    try:
        xml = fetch_feed(FEED_URL)
        items = extract_items(xml)
        if not items:
            print('No items found in feed.', file=sys.stderr)
            return
        append_ndjson(items, OUTPUT_PATH)
        print(f'Appended {len(items)} items to {OUTPUT_PATH}')
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}', file=sys.stderr)
    except requests.exceptions.RequestException as req_err:
        print(f'Request error occurred: {req_err}', file=sys.stderr)
    except Exception as e:
        print(f'An error occurred: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()