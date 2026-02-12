import requests
import json

# Base URL for Nippan's book data API
base_url = 'https://api.nippan.com/books'

# Function to scrape book data

def scrape_nippan_books():
    response = requests.get(base_url)
    if response.status_code == 200:
        books = response.json()
        with open('nippan_books.json', 'w') as json_file:
            json.dump(books, json_file, indent=4)
        print('Data saved to nippan_books.json')
    else:
        print('Failed to retrieve data')

# Call the function
if __name__ == '__main__':
    scrape_nippan_books()