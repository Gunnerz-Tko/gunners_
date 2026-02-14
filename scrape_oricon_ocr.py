import os
import json
import time
import re
import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pytesseract import image_to_string
from PIL import Image

# Setup Chrome WebDriver with headless options
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# Initialize the Chrome WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def scrape_with_ocr(url):
    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    screenshot = driver.get_screenshot_as_png()
    with open('screenshot.png', 'wb') as f:
        f.write(screenshot)
    text = image_to_string(Image.open('screenshot.png'))
    return text


def parse_ocr_text(text):
    books = []
    # Assuming text parsing logic here
    lines = text.split('\n')
    for line in lines[1:11]:  # Get top 10 books
        parts = line.split(',')
        if len(parts) < 5:
            continue
        book = {
            'rank': parts[0],
            'title': parts[1],
            'author': parts[2],
            'publisher': parts[3],
            'sales': parts[4]
        }
        books.append(book)
    return books


def main():
    genres = ['Comics', 'Paperback', 'Light Novel', 'Light Literature', 'Literary']
    all_books = []
    for genre in genres:
        url = f'https://www.oricon.co.jp/rank/{genre}/'
        text = scrape_with_ocr(url)
        books = parse_ocr_text(text)
        all_books.extend(books)

    with open('oricon_books.json', 'w') as json_file:
        json.dump(all_books, json_file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()