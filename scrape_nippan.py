import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

def load_corrections():
    """Load corrections from books_corrections.json"""
    try:
        with open('books_corrections.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('corrections', {})
    except Exception as e:
        print(f"⚠️  Could not load corrections: {e}")
        return {}

def find_correction(title, corrections_by_genre):
    """Find correction for a title"""
    for genre, books in corrections_by_genre.items():
        for book in books:
            if book['title'].lower() == title.lower():
                return book
    return None

def scrape_nippan_books():
    """Scrape from Nippan, use corrections from books_corrections.json"""
    
    try:
        # Load corrections first
        corrections = load_corrections()
        print(f"📋 Loaded corrections: {len(corrections)} genres\n")
        
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
                
                # Get title
                title_link = cells[1].find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                
                last_week = cells[4].get_text(strip=True) if len(cells) > 4 else "-"
                
                print(f"📖 {rank}. {title}")
                
                # Try to find correction for this title
                correction = find_correction(title, corrections)
                
                if correction:
                    author = correction.get('author', '-')
                    publisher = correction.get('publisher', '-')
                    print(f"   ✅ Found in corrections!")
                    print(f"   Author: {author}")
                    print(f"   Publisher: {publisher}")
                else:
                    author = "-"
                    publisher = "-"
                    print(f"   ⚠️  No correction found")
                
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
