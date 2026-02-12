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
                if len(cells) < 5:
                    print(f"  Row {idx}: Not enough cells ({len(cells)})")
                    continue
                
                # Rank (This week) - usually in first cell
                rank_text = cells[0].text.strip()
                rank = rank_text.split('\n')[0] if rank_text else str(idx)
                # Clean up rank (remove 'up', 'down', 'new', 'stay')
                rank = ''.join(c for c in rank if c.isdigit())
                
                # Last Week - usually in second cell
                last_week_text = cells[1].text.strip()
                # Extract just the number and position indicator
                last_week = last_week_text.split('\n')[0] if last_week_text else "-"
                
                # Image
                img_elem = row.find('img')
                image = img_elem.get('src', '') if img_elem else ""
                if image and not image.startswith('http'):
                    if image.startswith('//'):
                        image = 'https:' + image
                    else:
                        image = 'https://www.nippan.co.jp' + image
                
                # Book Title - usually in 3rd or 4th cell
                title = "Unknown"
                title_elem = cells[2].find('a') or cells[3].find('a') if len(cells) > 3 else None
                if title_elem:
                    title = title_elem.text.strip()
                else:
                    title = cells[2].text.strip() if len(cells) > 2 else "Unknown"
                
                # Author - usually in 4th or 5th cell
                author = "Unknown"
                if len(cells) > 4:
                    author_text = cells[4].text.strip()
                    # Sometimes includes newlines, take first line
                    author = author_text.split('\n')[0] if author_text else "Unknown"
                elif len(cells) > 3:
                    author_text = cells[3].text.strip()
                    author = author_text.split('\n')[0] if author_text else "Unknown"
                
                # Publisher - usually in 5th or 6th cell
                publisher = "Unknown"
                if len(cells) > 5:
                    publisher_text = cells[5].text.strip()
                    publisher = publisher_text.split('\n')[0] if publisher_text else "Unknown"
                
                if title != "Unknown" and rank:
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
