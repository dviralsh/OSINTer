import requests
import bs4
import json

url = 'http://feeds.reuters.com/Reuters/worldNews'

try:
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.content, features='xml')
    items = soup.findAll('item')
    news_items = [{'source': 'Reuters', 'content': item.title.text} for item in items]

    with open('agent/data/raw_data.json', 'a') as f:
        for news_item in news_items:
            f.write(json.dumps(news_item))
            f.write('\n')
except Exception as e:
    print(f'Something went wrong while fetching the data: {e}')