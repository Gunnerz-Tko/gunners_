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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(category_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Error fetching {category_url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        books = []
        
        # Find all book entries
        rank = 1
        for item in soup.select('tr.rank_item')[:10]:  # Get top 10
            try:
                # Title
                title_elem = item.select_one('td:nth-child(3) a')
                title = title_elem.text.strip() if title_elem else "Unknown"
                
                # Author
                author_elem = item.select_one('td:nth-child(4) a')
                author = author_elem.text.strip() if author_elem else "Unknown"
                
                # Sales
                sales_elem = item.select_one('td:nth-child(5)')
                sales = sales_elem.text.strip().replace(',', '') if sales_elem else "0"
                
                # Image
                img_elem = item.select_one('img')
                image = img_elem.get('src', '') if img_elem else ""
                
                book = {
                    "rank": rank,
                    "title": title,
                    "author": author,
                    "sales": sales,
                    "image": image
                }
                books.append(book)
                rank += 1
                
            except Exception as e:
                print(f"Error parsing book entry: {e}")
                continue
        
        return books
    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return []

def main():
    week_date = get_week_date()
    print(f"Scraping Oricon data for week of {week_date}...")
    
    categories = {
        "Comics": f"https://www.oricon.co.jp/rank/obc/w/{week_date}/",
        "Light Novels": f"https://www.oricon.co.jp/rank/obl/w/{week_date}/",
        "Light Literature": f"https://www.oricon.co.jp/rank/obll/w/{week_date}/",
        "Literary Books": f"https://www.oricon.co.jp/rank/oba/w/{week_date}/"
    }
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "week": f"Week {datetime.now().isocalendar()[1]} {datetime.now().year}",
        "genres": {},
        "total_genres": len(categories)
    }
    
    for category_name, url in categories.items():
        print(f"Scraping {category_name}...")
        books = scrape_oricon_category(url)
        data["genres"][category_name] = books
        print(f"✓ Found {len(books)} books in {category_name}")
    
    # Save to JSON file
    with open('oricon_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Data saved to oricon_books.json")

if __name__ == "__main__":
    main()
