import requests
from bs4 import BeautifulSoup

class OriconScraper:
    def __init__(self, url):
        self.url = url
        self.data = []

    def scrape(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            self.parse_data(soup)
        else:
            print('Failed to retrieve data from Oricon')

    def parse_data(self, soup):
        # Example: parsing a list of items
        items = soup.find_all('div', class_='item_class')  # Replace with actual class
        for item in items:
            title = item.find('h2').text
            self.data.append(title)

    def get_data(self):
        return self.data


if __name__ == '__main__':
    scraper = OriconScraper('http://www.oricon.co.jp/')  # Replace with actual URL
    scraper.scrape()
    print(scraper.get_data())