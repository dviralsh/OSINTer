#!/usr/bin/env python3
import os
import json
import logging
import requests
from bs4 import BeautifulSoup

# CNN RSS feed
RSS_URL = 'http://rss.cnn.com/rss/edition.rss'
OUTPUT_PATH = os.path.join('agent', 'data', 'raw_data.json')
SOURCE_NAME = 'cnn_rss'
MAX_ITEMS = 30


def fetch_rss(url, timeout=15):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; OSINT-Crawler/1.0)'}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def parse_rss(xml_bytes, max_items=MAX_ITEMS):
    soup = BeautifulSoup(xml_bytes, 'xml')
    items = soup.find_all('item')
    results = []
    for item in items[:max_items]:
        title = item.title.get_text(strip=True) if item.title else ''
        description = item.description.get_text(strip=True) if item.description else ''
        link = item.link.get_text(strip=True) if item.link else ''
        pubDate = item.pubDate.get_text(strip=True) if item.pubDate else ''
        parts = []
        if title:
            parts.append(title)
        if description:
            parts.append(description)
        if link:
            parts.append(link)
        if pubDate:
            parts.append(pubDate)
        content = "\n\n".join(parts).strip()
        if content:
            results.append(content)
    return results


def ensure_output_dir(path):
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def append_json_line(path, obj):
    # Each line must be a strictly valid JSON object
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        logging.info('Starting CNN RSS crawler for %s', RSS_URL)
        xml = fetch_rss(RSS_URL)
        logging.info('Fetched feed, parsing...')
        entries = parse_rss(xml)
        if not entries:
            logging.warning('No entries parsed from RSS feed: %s', RSS_URL)
        ensure_output_dir(OUTPUT_PATH)
        written = 0
        for content in entries:
            record = {'source': SOURCE_NAME, 'content': content}
            append_json_line(OUTPUT_PATH, record)
            written += 1
        logging.info('Appended %d entries to %s', written, OUTPUT_PATH)
    except Exception as e:
        logging.exception('Crawler encountered an error: %s', e)


if __name__ == '__main__':
    main()
