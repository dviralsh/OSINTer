import requests
from bs4 import BeautifulSoup
import json

url = 'http://feeds.bbci.co.uk/news/rss.xml#'

try:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, features='xml')
    items = soup.findAll('item')
    news_items = [{'source': 'BBC', 'content': item.find('description').text} for item in items]

    with open('agent/data/raw_data.json', 'a') as f:
        for news_item in news_items:
            f.write(json.dumps(news_item))
            f.write('\n')
except Exception as e:
    print(f'An error occurred: {e}')