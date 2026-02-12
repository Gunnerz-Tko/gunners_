import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

def scrape_nippan_books():
    """Scrape book rankings directly from Nippan website"""
    
    try:
        url = "https://www.nippan.co.jp/rank/books/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("🔄 Fetching data from Nippan...")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch Nippan (Status: {response.status_code})")
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
        
        # Find all book rows
        rows = soup.find_all('tr', class_='book-item')
        
        if not rows:
            # Try alternative selectors
            rows = soup.find_all('tr')
        
        general_count = 0
        paperback_count = 0
        comics_count = 0
        
        for row in rows:
            try:
                # Extract data from row
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                # Parse rank
                rank_text = cells[0].get_text(strip=True)
                if not rank_text.isdigit():
                    continue
                rank = int(rank_text)
                
                # Parse title
                title_elem = cells[1].find('a') or cells[1]
                title = title_elem.get_text(strip=True)
                
                # Parse author
                author = cells[2].get_text(strip=True) if len(cells) > 2 else "-"
                
                # Parse publisher
                publisher = cells[3].get_text(strip=True) if len(cells) > 3 else "-"
                
                # Parse last week rank
                last_week = cells[4].get_text(strip=True) if len(cells) > 4 else "-"
                
                book_data = {
                    "rank": rank,
                    "last_week": last_week,
                    "title": title,
                    "author": author if author else "-",
                    "publisher": publisher if publisher else "-",
                    "image": ""
                }
                
                # Distribute to genres (heuristic: first 10 = General, next 10 = Paperback, rest = Comics)
                if general_count < 10:
                    data["genres"]["General"].append(book_data)
                    general_count += 1
                elif paperback_count < 10:
                    data["genres"]["Paperback"].append(book_data)
                    paperback_count += 1
                elif comics_count < 10:
                    data["genres"]["Comics"].append(book_data)
                    comics_count += 1
                
                print(f"✅ {rank}. {title} - {publisher}")
                
            except Exception as e:
                print(f"⚠️  Error parsing row: {e}")
                continue
        
        # Save to file
        with open('nippan_books.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Scraping completed!")
        print(f"📚 General: {len(data['genres']['General'])} books")
        print(f"📚 Paperback: {len(data['genres']['Paperback'])} books")
        print(f"📚 Comics: {len(data['genres']['Comics'])} books")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    scrape_nippan_books()
