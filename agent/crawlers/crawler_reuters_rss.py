import requests
from bs4 import BeautifulSoup
import json

url = 'http://feeds.reuters.com/Reuters/worldNews'

try:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.findAll('item')
    news_items = [{'source': 'Reuters', 'title': item.title.text, 'link': item.link.text, 'pubDate': item.pubDate.text} for item in items]

    with open('agent/data/raw_data.json', 'a') as f:
        for news_item in news_items:
            f.write(json.dumps(news_item) + '\n')
except Exception as e:
    print(f'Something went wrong while fetching the data: {e}')