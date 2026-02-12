import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

def get_book_info_from_openlibrary(title):
    """Get author and publisher from OpenLibrary"""
    try:
        url = f"https://openlibrary.org/search.json?title={title}&limit=5"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('docs') and len(data['docs']) > 0:
                book = data['docs'][0]
                authors = book.get('author_name', [])
                publishers = book.get('publisher', [])
                
                return {
                    'author': authors[0] if authors else "-",
                    'publisher': publishers[0] if publishers else "-"
                }
        return None
    except Exception as e:
        return None

def get_book_info_from_google_books(title):
    """Get author and publisher from Google Books API"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=5"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items') and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                
                authors = book.get('authors', [])
                publisher = book.get('publisher', '-')
                
                return {
                    'author': authors[0] if authors else "-",
                    'publisher': publisher
                }
        return None
    except Exception as e:
        return None

def get_book_info_from_rakuten(title):
    """Get author and publisher from Rakuten Books (Japanese source)"""
    try:
        # Using Rakuten Books search
        url = f"https://books.rakuten.co.jp/search/products?keyword={title}"
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find first result
            result = soup.find('div', class_='item')
            if result:
                author_elem = result.find('div', class_='author')
                publisher_elem = result.find('div', class_='publisher')
                
                author = author_elem.get_text(strip=True) if author_elem else "-"
                publisher = publisher_elem.get_text(strip=True) if publisher_elem else "-"
                
                if author != "-" and publisher != "-":
                    return {
                        'author': author,
                        'publisher': publisher
                    }
        return None
    except Exception as e:
        return None

def get_best_book_info(title):
    """Try multiple sources in order to get best data"""
    
    # Try Rakuten first (Japanese source, most accurate for Japanese books)
    print(f"  🔍 Checking Rakuten Books...")
    info = get_book_info_from_rakuten(title)
    if info and info['author'] != "-" and info['publisher'] != "-":
        print(f"  ✅ Found on Rakuten!")
        return info
    
    # Try Google Books
    print(f"  🔍 Checking Google Books...")
    info = get_book_info_from_google_books(title)
    if info and info['author'] != "-" and info['publisher'] != "-":
        print(f"  ✅ Found on Google Books!")
        return info
    
    # Try OpenLibrary
    print(f"  🔍 Checking OpenLibrary...")
    info = get_book_info_from_openlibrary(title)
    if info and info['author'] != "-" and info['publisher'] != "-":
        print(f"  ✅ Found on OpenLibrary!")
        return info
    
    # Return whatever we have
    return info or {'author': "-", 'publisher': "-"}

def scrape_nippan_books():
    """Scrape titles from Nippan, fetch details from multiple sources"""
    
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
                
                # Get best info from multiple sources
                book_info = get_best_book_info(title)
                
                book_data = {
                    "rank": rank,
                    "last_week": last_week,
                    "title": title,
                    "author": book_info['author'],
                    "publisher": book_info['publisher'],
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
                
                print(f"  Author: {book_info['author']}")
                print(f"  Publisher: {book_info['publisher']}\n")
                
                time.sleep(1)  # Be respectful to APIs
                
            except Exception as e:
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
