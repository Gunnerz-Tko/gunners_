import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def get_week_date():
    """Get the date for the current week (Monday of current week)"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime('%Y-%m-%d')

async def scrape_oricon_category(browser, category_url):
    """Scrape Oricon data using Playwright to load JavaScript"""
    try:
        page = await browser.new_page()
        await page.goto(category_url, wait_until='networkidle', timeout=30000)
        
        # Wait for the ranking table to load
        await page.wait_for_selector('tr.rank_item', timeout=10000)
        
        # Get the page content after JavaScript loads
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        books = []
        rank_items = soup.select('tr.rank_item')
        print(f"Found {len(rank_items)} rank items")
        
        for idx, item in enumerate(rank_items[:10], 1):
            try:
                # Rank
                rank_elem = item.select_one('td.rank_num')
                rank = rank_elem.text.strip() if rank_elem else str(idx)
                rank = rank.replace('位', '').strip()
                
                # Book cover image
                img_elem = item.select_one('img')
                image = img_elem.get('src', '') if img_elem else ""
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
                print(f"  #{rank}: {title}")
                
            except Exception as e:
                print(f"Error parsing item {idx}: {e}")
                continue
        
        await page.close()
        return books
        
    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return []

async def main():
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
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for category_name, url in categories.items():
            print(f"\nScraping {category_name}...")
            books = await scrape_oricon_category(browser, url)
            data["genres"][category_name] = books
            print(f"✓ Found {len(books)} books")
        
        await browser.close()
    
    # Save to JSON file
    with open('oricon_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Data saved to oricon_books.json")

if __name__ == "__main__":
    asyncio.run(main())
