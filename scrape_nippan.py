import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re

def get_book_info_from_rakuten(title):
    """Scrape book info directly from Rakuten Books"""
    try:
        # Search on Rakuten Books
        search_url = f"https://books.rakuten.co.jp/search/products?keyword={title}&sort=-releaseDate"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first book result
        book_item = soup.find('div', class_='searchResultItem')
        
        if not book_item:
            book_item = soup.find('li', class_='item')
        
        if book_item:
            # Extract author
            author_elem = book_item.find('span', class_='author')
            if not author_elem:
                author_elem = book_item.find('div', class_='author')
            if not author_elem:
                # Try to find author in text
                author_text = book_item.find_all(string=re.compile('著'))
                author_elem = author_text[0] if author_text else None
            
            author = author_elem.get_text(strip=True) if author_elem else "-"
            
            # Extract publisher
            publisher_elem = book_item.find('span', class_='publisher')
            if not publisher_elem:
                publisher_elem = book_item.find('div', class_='publisher')
            if not publisher_elem:
                # Try to find publisher in text
                publisher_text = book_item.find_all(string=re.compile('出版社|出版'))
                publisher_elem = publisher_text[0] if publisher_text else None
            
            publisher = publisher_elem.get_text(strip=True) if publisher_elem else "-"
            
            # Clean up text
            author = author.replace('著', '').replace('作', '').replace('編', '').strip()
            publisher = publisher.replace('出版社:', '').replace('出版:', '').strip()
            
            return {
                'author': author if author else "-",
                'publisher': publisher if publisher else "-"
            }
        
        return None
        
    except Exception as e:
        print(f"    ⚠️  Error scraping Rakuten: {e}")
        return None

def scrape_nippan_books():
    """Scrape titles from Nippan, fetch details from Rakuten Books"""
    
    try:
        url = "https://www.nippan.co.jp/rank/books/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print("🔄 Fetching titles from Nippan...\n")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch Nippan")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = {
            "updated": datetime.now().isoformat() + "Z",
            "genres": {
                "General": [],
                "Paperback": [],
                "Comics": []
            }
        }
        
        rows = soup.find_all('tr')
        
        general_count = 0
        paperback_count = 0
        comics_count = 0
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                rank_text = cells[0].get_text(strip=True)
                if not rank_text.isdigit():
                    continue
                rank = int(rank_text)
                
                title_elem = cells[1].find('a') or cells[1]
                title = title_elem.get_text(strip=True)
                
                last_week = cells[4].get_text(strip=True) if len(cells) > 4 else "-"
                
                print(f"📖 {rank}. {title}")
                print(f"   🔍 Searching Rakuten Books...")
                
                # Get info from Rakuten Books
                book_info = get_book_info_from_rakuten(title)
                
                if book_info:
                    author = book_info['author']
                    publisher = book_info['publisher']
                    print(f"   ✅ Author: {author}")
                    print(f"   ✅ Publisher: {publisher}")
                else:
                    author = "-"
                    publisher = "-"
                    print(f"   ⚠️  Not found on Rakuten")
                
                book_data = {
                    "rank": rank,
                    "last_week": last_week,
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "image": ""
                }
                
                if general_count < 10:
                    data["genres"]["General"].append(book_data)
                    general_count += 1
                elif paperback_count < 10:
                    data["genres"]["Paperback"].append(book_data)
                    paperback_count += 1
                elif comics_count < 10:
                    data["genres"]["Comics"].append(book_data)
                    comics_count += 1
                
                print()
                time.sleep(2)  # Be respectful to Rakuten servers
                
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
                continue
        
        with open('nippan_books.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Scraping completed!")
        print(f"📚 General: {len(data['genres']['General'])} books")
        print(f"📚 Paperback: {len(data['genres']['Paperback'])} books")
        print(f"📚 Comics: {len(data['genres']['Comics'])} books")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    scrape_nippan_books()
