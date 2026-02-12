import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

def get_week_date():
    """Get the date for the current week (Monday of current week)"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime('%Y-%m-%d')

def scrape_oricon_category(category_url):
    """Scrape Oricon data for a specific category"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(category_url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Error fetching {category_url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        books = []
        
        # Find all rank item rows
        rank_items = soup.select('tr.rank_item')
        print(f"Found {len(rank_items)} items")
        
        for idx, item in enumerate(rank_items[:10], 1):
            try:
                # Rank (from the row number or explicit rank cell)
                rank_elem = item.select_one('td.rank_num')
                rank = rank_elem.text.strip() if rank_elem else str(idx)
                rank = rank.replace('位', '').strip()
                
                # Book cover image
                img_elem = item.select_one('td img')
                image = img_elem.get('src', '') if img_elem else ""
                # Convert to full URL if relative
                if image and not image.startswith('http'):
                    image = 'https://www.oricon.co.jp' + image
                
                # Book Title
                title_elem = item.select_one('td.title a')
                title = title_elem.text.strip() if title_elem else "Unknown"
                
                # Publisher
                publisher_elem = item.select_one('td.publisher')
                publisher = publisher_elem.text.strip() if publisher_elem else "Unknown"
                
                # Release Date
                release_date_elem = item.select_one('td.release_date')
                release_date = release_date_elem.text.strip() if release_date_elem else "Unknown"
                
                # Estimated Sales
                sales_elem = item.select_one('td.sales')
                sales = sales_elem.text.strip() if sales_elem else "0"
                # Remove commas and extract just the number
                sales = sales.replace(',', '').replace('万', '0000').split()[0] if sales else "0"
                
                book = {
                    "rank": rank,
                    "title": title,
                    "publisher": publisher,
                    "release_date": release_date,
                    "sales": sales,
                    "image": image
                }
                books.append(book)
                print(f"  #{rank}: {title} - {publisher}")
                
            except Exception as e:
                print(f"Error parsing book entry {idx}: {e}")
                continue
        
        return books
    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return []

def main():
    week_date = get_week_date()
    print(f"Scraping Oricon data for week of {week_date}...\n")
    
    categories = {
        "Comics": f
