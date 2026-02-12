import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re

def get_book_info_from_amazon_jp(title):
    """Scrape book info from Amazon.co.jp with improved parsing"""
    try:
        # Search on Amazon.co.jp
        search_url = f"https://www.amazon.co.jp/s?k={title}&i=books"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first book result - more reliable selector
        book_item = soup.find('div', {'data-component-type': 's-search-result'})
        
        if not book_item:
            # Try alternative selector
            book_item = soup.find('div', class_='s-result-item')
        
        if not book_item:
            return None
        
        # Get the link to the book detail page
        book_link = book_item.find('a', class_='a-link-normal')
        
        if not book_link or not book_link.get('href'):
            return None
        
        book_url = book_link['href']
        if not book_url.startswith('http'):
            book_url = 'https://www.amazon.co.jp' + book_url
        
        print(f"    📄 Fetching: {book_url}")
        
        # Fetch the book detail page
        response = requests.get(book_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract author from the title area
        author = "-"
        
        # Method 1: Look in the product details table (detailBullets or feature-bullets)
        details_section = soup.find('div', {'data-feature-name': 'detailBullets'})
        
        if not details_section:
            details_section = soup.find('div', {'data-feature-name': 'featurebullets'})
        
        if details_section:
            for li in details_section.find_all('li'):
                li_text = li.get_text(strip=True)
                
                # Look for author
                if any(x in li_text for x in ['著者', '作者', '著']):
                    # Extract the author name (usually after the label)
                    author = re.sub(r'著者[：:]\s*', '', li_text)
                    author = re.sub(r'作者[：:]\s*', '', author)
                    # Remove any comma-separated additional info
                    author = author.split('、')[0].strip()
                    break
        
        # Method 2: Look in the attribute table
        if author == "-":
            table = soup.find('table', {'role': 'presentation'})
            if not table:
                table = soup.find('table', class_='a-normal')
            
            if table:
                for tr in table.find_all('tr'):
                    th = tr.find('th')
                    td = tr.find('td')
                    
                    if th and td:
                        th_text = th.get_text(strip=True)
                        
                        if '著者' in th_text or '作者' in th_text:
                            author = td.get_text(strip=True)
                            break
        
        # Extract publisher
        publisher = "-"
        
        if details_section:
            for li in details_section.find_all('li'):
                li_text = li.get_text(strip=True)
                
                # Look for publisher
                if any(x in li_text for x in ['出版社', 'Publisher', '出版']):
                    # Extract the publisher name
                    publisher = re.sub(r'出版社[：:]\s*', '', li_text)
                    publisher = re.sub(r'Publisher[：:]\s*', '', publisher)
                    # Remove any additional info after semicolon or comma
                    publisher = publisher.split('；')[0].split('、')[0].strip()
                    break
        
        # Method 2: Look in the attribute table for publisher
        if publisher == "-":
            table = soup.find('table', {'role': 'presentation'})
            if not table:
                table = soup.find('table', class_='a-normal')
            
            if table:
                for tr in table.find_all('tr'):
                    th = tr.find('th')
                    td = tr.find('td')
                    
                    if th and td:
                        th_text = th.get_text(strip=True)
                        
                        if '出版社' in th_text or 'Publisher' in th_text:
                            publisher = td.get_text(strip=True)
                            break
        
        # Clean up publisher name
        publisher = re.sub(r'[\(\)（）].*', '', publisher).strip()
        
        return {
            'author': author if author and author != "-" else "-",
            'publisher': publisher if publisher and publisher != "-" else "-",
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
