import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re

def get_book_info_from_amazon_jp(title):
    """Scrape book info from Amazon.co.jp (most reliable Japanese source)"""
    try:
        # Search on Amazon.co.jp
        search_url = f"https://www.amazon.co.jp/s?k={title}&i=books"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"    ⚠️  Amazon.co.jp returned {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first book result
        # Amazon uses multiple possible selectors
        book_link = soup.find('a', {'data-component-type': 's-search-result'})
        if not book_link:
            book_link = soup.find('h2', class_='s-size-mini').find('a')
        if not book_link:
            book_link = soup.find('a', class_='a-link-normal')
        
        if not book_link or not book_link.get('href'):
            print(f"    ⚠️  No book found on Amazon")
            return None
        
        book_url = book_link['href']
        if not book_url.startswith('http'):
            book_url = 'https://www.amazon.co.jp' + book_url
        
        # Fetch the book detail page
        response = requests.get(book_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract author
        author = "-"
        # Look for author in product details
        for th in soup.find_all('th'):
            th_text = th.get_text(strip=True)
            if '著者' in th_text or '作者' in th_text:
                td = th.find_next('td')
                if td:
                    author = td.get_text(strip=True)
                    # Clean up
                    author = re.sub(r'著者:|作者:|作・編集:|,.*', '', author).strip()
                    break
        
        # If not found, try other selectors
        if author == "-":
            author_elem = soup.find(string=re.compile('著者|作者'))
            if author_elem:
                parent = author_elem.parent
                next_elem = parent.find_next(['span', 'div', 'a'])
                if next_elem:
                    author = next_elem.get_text(strip=True)
        
        # Extract publisher
        publisher = "-"
        # Look for publisher in product details
        for th in soup.find_all('th'):
            th_text = th.get_text(strip=True)
            if '出版社' in th_text or 'Publisher' in th_text:
                td = th.find_next('td')
                if td:
                    publisher = td.get_text(strip=True)
                    publisher = re.sub(r'出版社:|出版:', '', publisher).strip()
                    break
        
        # If not found, try other selectors
        if publisher == "-":
            publisher_elem = soup.find(string=re.compile('出版社'))
            if publisher_elem:
                parent = publisher_elem.parent
                next_elem = parent.find_next(['span', 'div', 'a'])
                if next_elem:
                    publisher = next_elem.get_text(strip=True)
        
        # Try to find in detail section
        if publisher == "-":
            detail_section = soup.find('div', {'data-feature-name': 'detailBullets'})
            if detail_section:
                for li in detail_section.find_all('li'):
                    li_text = li.get_text(strip=True)
                    if '出版社' in li_text:
                        publisher = re.sub(r'.*出版社[：:]\s*', '', li_text).strip()
                        break
        
        return {
            'author': author if author else "-",
            'publisher': publisher if publisher else "-",
            'url': book_url
        }
        
    except Exception as e:
        print(f"    ⚠️  Error scraping Amazon.co.jp: {e}")
        return None

def scrape_nippan_books():
    """Scrape from Nippan, get details from Amazon.co.jp"""
    
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
                
                # Get title
                title_link = cells[1].find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                
                last_week = cells[4].get_text(strip=True) if len(cells) > 4 else "-"
                
                print(f"📖 {rank}. {title}")
                print(f"   🔍 Searching Amazon.co.jp...")
                
                # Get info from Amazon.co.jp
                book_info = get_book_info_from_amazon_jp(title)
                
                if book_info:
                    author = book_info['author']
                    publisher = book_info['publisher']
                    print(f"   ✅ Author: {author}")
                    print(f"   ✅ Publisher: {publisher}")
                else:
                    author = "-"
                    publisher = "-"
                    print(f"   ⚠️  Could not fetch from Amazon")
                
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
                time.sleep(2)  # Be respectful to servers
                
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
