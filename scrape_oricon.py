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
        
        # Try multiple selectors for rank items
        rank_items = soup.select('tr.rank_item')
        if not rank_items:
            rank_items = soup.select('table tr[class*="rank"]')
        if not rank_items:
            rank_items = soup.select('tbody tr')
            
        print(f"Found {len(rank_items)} potential rank items")
        
        # Debug: Print first item HTML
        if rank_items:
            print("\nFirst item HTML:")
            print(rank_items[0].prettify()[:500])
        
        for idx, item in enumerate(rank_items[:10], 1):
            try:
                # Try different selectors for rank
                rank = str(idx)
                for rank_selector in ['td:nth-child(1)', '.rank_num', 'td[class*="rank"]']:
                    rank_elem = item.select_one(rank_selector)
                    if rank_elem:
                        rank = rank_elem.text.strip().replace('位', '').strip()
                        break
                
                # Book cover image
                image = ""
                for img_selector in ['img', 'img[alt]', 'td:nth-child(2) img']:
                    img_elem = item.select_one(img_selector)
                    if img_elem:
                        image = img_elem.get('src', '')
                        if image and not image.startswith('http'):
                            image = 'https://www.oricon.co.jp' + image
                        break
                
                # Book Title - try multiple selectors
                title = "Unknown"
                for title_selector in ['.title a', 'td:nth-child(3) a', 'td:nth-child(4) a', 'a[href*="/product/"]']:
                    title_elem = item.select_one(title_selector)
                    if title_elem:
                        title = title_elem.text.strip()
                        break
                
                # Publisher
                publisher = "Unknown"
                for pub_selector in ['.publisher', 'td:nth-child(5)', 'td:nth-child(6)']:
                    pub_elem = item.select_one(pub_selector)
                    if pub_elem:
                        publisher = pub_elem.text.strip()
                        break
                
                # Release Date
                release_date = "Unknown"
                for date_selector in ['.release_date', 'td:nth-child(6)', 'td:nth-child(7)']:
                    date_elem = item.select_one(date_selector)
                    if date_elem:
                        release_date = date_elem.text.strip()
                        break
                
                # Estimated Sales
                sales = "0"
                for sales_selector in ['.sales', 'td:nth-child(7)', 'td:nth-child(8)']:
                    sales_elem = item.select_one(sales_selector)
                    if sales_elem:
                        sales = sales_elem.text.strip()
                        sales = sales.replace(',', '').replace('万', '0000').split()[0]
                        break
                
                if title != "Unknown":  # Only add if we found a title
                    book = {
                        "rank": rank,
                        "title": title,
                        "publisher": publisher,
                        "release_date": release_date,
                        "sales": sales,
                        "image": image
                    }
                    books.append(book)
                    print(f"✓ #{rank}: {title}")
                
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
        print(f"\n{'='*60}")
        print(f"Scraping {category_name}...")
        print(f"URL: {url}")
        print('='*60)
        books = scrape_oricon_category(url)
        data["genres"][category_name] = books
        print(f"✓ Found {len(books)} books in {category_name}")
    
    # Save to JSON file
    with open('oricon_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Data saved to oricon_books.json")

if __name__ == "__main__":
    main()
