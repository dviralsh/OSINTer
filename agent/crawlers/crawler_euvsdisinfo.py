#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import os
import sys

def main():
    try:
        base_url = 'https://euvsdisinfo.eu/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; OSINT-crawler/1.0)'
        }

        resp = requests.get(base_url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find recent article blocks. Be permissive about structure to handle minor layout changes.
        articles = soup.find_all('article')
        if not articles:
            # fallback: look for article links in h2 tags
            h2_links = soup.find_all('h2')
            articles = h2_links

        items = []
        max_items = 5
        count = 0

        for a in articles:
            if count >= max_items:
                break

            # Extract link and title robustly
            link_tag = None
            if a.name == 'article':
                h2 = a.find('h2')
                if h2 and h2.find('a'):
                    link_tag = h2.find('a')
                else:
                    link_tag = a.find('a')
            else:
                # fallback when soup returned h2 elements or other nodes
                link_tag = a.find('a') if hasattr(a, 'find') else None

            if not link_tag or not link_tag.get('href'):
                continue

            link = link_tag['href']
            title = link_tag.get_text(strip=True)

            # Date extraction if available
            date = ''
            if isinstance(a, (BeautifulSoup,)):
                # not expected; keep safe
                date = ''
            else:
                date_tag = a.find('time') if hasattr(a, 'find') else None
                if date_tag:
                    date = date_tag.get_text(strip=True)

            # Fetch article page and extract snippet paragraphs
            snippet = ''
            try:
                art_resp = requests.get(link, headers=headers, timeout=15)
                art_resp.raise_for_status()
                art_soup = BeautifulSoup(art_resp.text, 'html.parser')

                # Common containers for article text
                content_div = art_soup.find(class_='entry-content') or art_soup.find(class_='post-content') or art_soup.find('main') or art_soup.find('article')

                paragraphs = []
                if content_div:
                    for p in content_div.find_all('p'):
                        text = p.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
                        if len(paragraphs) >= 3:
                            break
                snippet = ' '.join(paragraphs)
            except Exception:
                # If fetching the article fails, continue with what we have
                snippet = ''

            items.append({
                'title': title,
                'date': date,
                'link': link,
                'snippet': snippet
            })
            count += 1

        if not items:
            raise RuntimeError('No articles/items could be parsed from EUvsDisinfo')

        # Construct a readable content string
        content_lines = []
        for it in items:
            line = f"Title: {it['title']}\nDate: {it['date']}\nLink: {it['link']}\nSnippet: {it['snippet']}\n"
            content_lines.append(line)
        content_text = '\n'.join(content_lines)

        out = {'source': 'EUvsDisinfo', 'content': content_text}

        os.makedirs('agent/data', exist_ok=True)
        with open('agent/data/raw_data.json', 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(out, ensure_ascii=False) + '\n')

    except Exception as e:
        # On error, append an error record to the same file and print to stderr
        err_record = {'source': 'crawler_euvsdisinfo.py', 'content': f'ERROR: {repr(e)}'}
        try:
            os.makedirs('agent/data', exist_ok=True)
            with open('agent/data/raw_data.json', 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(err_record, ensure_ascii=False) + '\n')
        except Exception:
            pass
        print('Error in crawler_euvsdisinfo.py:', e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
