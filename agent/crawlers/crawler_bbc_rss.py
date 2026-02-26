import requests
from bs4 import BeautifulSoup
import json

url = 'http://feeds.bbci.co.uk/news/rss.xml#'

try:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.findAll('item')
    news_items = [{'source': 'BBC', 'content': item.find('description').text} for item in items]

    with open('agent/data/raw_data.json', 'a') as f:
        json.dump(news_items, f)
except requests.exceptions.HTTPError as http_err:
    print(f'HTTP error occurred: {http_err}')
except requests.exceptions.RequestException as req_err:
    print(f'Request error occurred: {req_err}')
except Exception as e:
    print(f'An error occurred: {e}')