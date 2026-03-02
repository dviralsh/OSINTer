import requests
from bs4 import BeautifulSoup
import json
import os

def main():
    try:
        rss_url = 'https://threatpost.com/feed/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; OSINTAgent/1.0; +https://example.com)'
        }

        resp = requests.get(rss_url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, 'xml')
        items = soup.find_all('item')[:5]  # fetch up to 5 most recent items

        os.makedirs('agent/data', exist_ok=True)
        out_path = os.path.join('agent', 'data', 'raw_data.json')

        entries = []

        for item in items:
            title = item.title.text.strip() if item.title else ''
            # RSS <link> tag can be a child element or text
            link = ''
            if item.find('link'):
                link = item.find('link').text.strip()
            elif item.link:
                link = item.link.strip()
            description = item.description.text.strip() if item.description else ''

            article_body = ''
            if link:
                try:
                    aresp = requests.get(link, headers=headers, timeout=15)
                    aresp.raise_for_status()
                    a_soup = BeautifulSoup(aresp.content, 'html.parser')

                    # Try several common containers for article text
                    paragraphs = []
                    article_tag = a_soup.find('article')
                    if article_tag:
                        paragraphs = article_tag.find_all('p')
                    else:
                        # threatpost and many sites use classes like 'entry-content', 'td-post-content', etc.
                        container = (a_soup.find('div', class_='td-post-content') or
                                     a_soup.find('div', class_='entry-content') or
                                     a_soup.find('div', id='article-body') or
                                     a_soup.find('div', class_='article-body') or
                                     a_soup.find('div', class_='post-content'))
                        if container:
                            paragraphs = container.find_all('p')
                        else:
                            # fallback: first several <p> tags on the page
                            paragraphs = a_soup.find_all('p')[:15]

                    texts = [p.get_text(strip=True) for p in paragraphs]
                    # filter out very short paragraphs
                    texts = [t for t in texts if len(t) > 20]
                    article_body = '\n\n'.join(texts).strip()

                    if not article_body:
                        article_body = 'Article fetched but no substantial paragraph content was found.'

                except Exception as e:
                    article_body = f'Failed to fetch article body: {e}'
            else:
                article_body = 'No link available in RSS item.'

            content = (
                f"Title: {title}\n"
                f"Link: {link}\n"
                f"Description: {description}\n\n"
                f"Article:\n{article_body}"
            )

            entry = {'source': 'Threatpost RSS', 'content': content}
            entries.append(entry)

        # Append each entry as a JSON string (one per line) to the raw_data.json file
        with open(out_path, 'a', encoding='utf-8') as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')

    except Exception as main_e:
        # On any unexpected error, append an error entry so the system has feedback
        os.makedirs('agent/data', exist_ok=True)
        err = {'source': 'crawler_threatpost_rss.py', 'content': f'Error: {repr(main_e)}'}
        with open(os.path.join('agent', 'data', 'raw_data.json'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(err, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main()
