import requests
from bs4 import BeautifulSoup
import json
import time

url = 'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml'

def parse_rss(url):
    articles = []
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'xml')
        items = soup.findAll('item')

        for item in items:
            news_item = {}
            news_item['title'] = item.title.text if item.title else None
            news_item['description'] = item.description.text if item.description else None
            news_item['pubDate'] = item.pubDate.text if item.pubDate else None
            news_item['link'] = item.link.text if item.link else None
            articles.append(news_item)
    except Exception as e:
        print('The scraping job failed. See exception: ', e)
    return articles

def append_json(filename, data):
    try:
        with open(filename, 'a') as f:
            json.dump(data, f)
            f.write('\n')
    except Exception as e:
        print('Failed to append data to json file. See exception: ', e)

def main():
    while True:
        print('Starting scraping cycle')
        try:
            articles = parse_rss(url)
            if articles:
                for article in articles:
                    append_json('agent/data/raw_data.json', {'source': 'NYTimes', 'content': article})
                print('Scraping cycle completed')
        except Exception as e:
            print('Error in main loop', e)
        time.sleep(60*60)

if __name__ == '__main__':
    main()