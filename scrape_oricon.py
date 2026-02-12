import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
from bs4 import BeautifulSoup

async def scrape_nippan_category(browser, category_url, category_name):
    """Scrape Nippan ranking data using Playwright"""
    try:
        page = await browser.new_page()
        await page.goto(category_url, wait_until='networkidle', timeout=30000)
        
        # Wait for the ranking table to load
        await page.wait_for_selector('table', timeout=10000)
        
        # Get the page content after JavaScript loads
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        books = []
        
        # Find all rows in the ranking table
        rows = soup.select('table tbody tr')
        print(f"Found {len(rows)} rows in {category_name}")
        
        for idx, row in enumerate(rows[:20], 1):  # Top 20
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                # Rank (This week)
                rank_elem = cells[0]
                rank = rank_elem.text.strip() if rank_elem else str(idx)
                
                # Last Week
                last_week_elem = cells[1]
                last_week = last_week_elem.text.strip() if last_week_elem else "-"
                
                # Image
                img_elem = row.find('img')
                image = img_elem.get('src', '') if img_elem else ""
                if image and not image.startswith('http'):
                    if image.startswith('//'):
                        image = 'https:' + image
                    else:
                        image = 'https://www.nippan.co.jp' + image
                
                # Book Title
                title_elem = cells[2].find('a')
                title = title_elem.text.strip() if title_elem else "Unknown"
                
                # Author
                author_elem = cells[3]
                author = author_elem.text.strip() if author_elem else "Unknown"
                
                # Publisher
                publisher_elem = cells[4]
                publisher = publisher_elem.text.strip() if publisher_elem else "Unknown"
                
                if title != "Unknown":
                    book = {
                        "rank": rank,
                        "last_week": last_week,
                        "title": title,
                        "author": author,
                        "publisher": publisher,
                        "image": image
                    }
                    books.append(book)
                    print(f"  #{rank}: {title} - {author}")
                
            except Exception as e:
                print(f"Error parsing row {idx}: {e}")
                continue
        
        await page.close()
        return books
        
    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return []

async def main():
    print(f"Scraping Nippan ranking data...\n")
    
    categories = {
        "General": "https://www.nippan.co.jp/ranking/weekly/?ranking_cat=83",
        "Paperback": "https://www.nippan.co.jp/ranking/weekly/?ranking_cat=84",
        "Comics": "https://www.nippan.co.jp/ranking/weekly/?ranking_cat=85"
    }
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "Nippan Weekly Rankings",
        "genres": {},
        "total_genres": len(categories)
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for category_name, url in categories.items():
            print(f"\n{'='*60}")
            print(f"Scraping {category_name}...")
            print(f"URL: {url}")
            print('='*60)
            books = await scrape_nippan_category(browser, url, category_name)
            data["genres"][category_name] = books
            print(f"✓ Found {len(books)} books in {category_name}")
        
        await browser.close()
    
    # Save to JSON file
    with open('nippan_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Data saved to nippan_books.json")

if __name__ == "__main__":
    asyncio.run(main())
