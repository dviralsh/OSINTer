import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.aljazeera.com/xml/rss/all.xml'

try:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.find_all('item')
    news_items = []

    for item in items:
        news_item = {}
        news_item['title'] = item.title.text
        news_item['link'] = item.link.text
        news_item['pubDate'] = item.pubDate.text
        news_item['description'] = item.description.text
        news_items.append(news_item)

    with open('agent/data/raw_data.json', 'a') as outfile:
        json.dump(news_items, outfile)

except Exception as e:
    print('The scraping job failed. See exception: ')
    print(e)