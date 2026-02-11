import requests
from bs4 import BeautifulSoup

# Function to scrape Oricon Book Rankings by Genre

def scrape_oricon_rankings(genre):
    url = f'https://www.oricon.co.jp/rank/book/{genre}/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    rankings = []
    for item in soup.select('.item'):  # Update the selector based on actual structure
        title = item.select_one('.title').text.strip()  # Adjust as needed
        author = item.select_one('.author').text.strip()  # Adjust as needed
        rank = item.select_one('.rank').text.strip()  # Adjust as needed
        rankings.append({'rank': rank, 'title': title, 'author': author})
    
    return rankings

# Sample usage
if __name__ == '__main__':
    genre = 'your_genre_here'  # Replace with desired genre
    rankings = scrape_oricon_rankings(genre)
    for ranking in rankings:
        print(ranking)