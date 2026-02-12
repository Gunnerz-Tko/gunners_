import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re

def get_book_info_from_honyaclub(title, nippan_link):
    """Scrape book info from honyaclub.com (the actual source)"""
    try:
        # If we have the direct link from Nippan, use it
        if nippan_link and 'honyaclub' in nippan_link:
            url = nippan_link
        else:
            # Otherwise search on honyaclub
            search_url = f"https://www.honyaclub.com/search/?q={title}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            first_result = soup.find('a', class_='searchResultItemLink')
            
            if not first_result or not first_result.get('href'):
                return None
            
            url = first_result['href']
            if not url.startswith('http'):
                url = 'https://www.honyaclub.com' + url
        
        # Fetch the book page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract author
        author = "-"
        # Try multiple selectors for author
        author_elem = soup.find('div', class_='author')
        if not author_elem:
            author_elem = soup.find('span', class_='author')
        if not author_elem:
            # Look for 著者 (author) text
            author_elem = soup.find(string=re.compile('著者|作者'))
            if author_elem:
                author_elem = author_elem.find_next('span')
        
        if author_elem:
            author = author_elem.get_text(strip=True)
            author = re.sub(r'著者:|著|作|編|訳', '', author).strip()
        
        # Extract publisher
        publisher = "-"
        # Try multiple selectors for publisher
        publisher_elem = soup.find('div', class_='publisher')
        if not publisher_elem:
            publisher_elem = soup.find('span', class_='publisher')
        if not publisher_elem:
            # Look for 出版社 (publisher) text
            publisher_elem = soup.find(string=re.compile('出版社|出版'))
            if publisher_elem:
                publisher_elem = publisher_elem.find_next('span')
        
        if publisher_elem:
            publisher = publisher_elem.get_text(strip=True)
            publisher = re.sub(r'出版社:|出版:', '', publisher).strip()
        
        # Also try to find in product details section
        if author == "-" or publisher == "-":
            details = soup.find('div', class_='productDetails')
            if details:
                rows = details.find_all('tr')
                for row in rows:
                    label = row.find('th')
                    value = row.find('td')
                    if label and value:
                        label_text = label.get_text(strip=True)
                        value_text = value.get_text(strip=True)
                        
                        if '著者' in label_text or '作者' in label_text:
                            if author == "-":
                                author = value_text
                        elif '出版社' in label_text:
                            if publisher == "-":
                                publisher = value_text
        
        return {
            'author': author if author else "-",
            'publisher': publisher if publisher else "-",
            'url': url
        }
        
    except Exception as e:
        print(f"    ⚠️  Error scraping honyaclub: {e}")
        return None

def scrape_nippan_books():
    """Scrape from Nippan, get details from honyaclub links"""
    
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
                
                # Get title and link from Nippan
                title_link = cells[1].find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                nippan_link = title_link.get('href', '')
                if not nippan_link.startswith('http'):
                    nippan_link = 'https://www.nippan.co.jp' + nippan_link
                
                last_week = cells[4].get_text(strip=True) if len(cells) > 4 else "-"
                
                print(f"📖 {rank}. {title}")
                print(f"   🔗 Link: {nippan_link}")
                print(f"   🔍 Fetching from honyaclub...")
                
                # Get info from honyaclub
                book_info = get_book_info_from_honyaclub(title, nippan_link)
                
                if book_info:
                    author = book_info['author']
                    publisher = book_info['publisher']
                    print(f"   ✅ Author: {author}")
                    print(f"   ✅ Publisher: {publisher}")
                else:
                    author = "-"
                    publisher = "-"
                    print(f"   ⚠️  Could not fetch from honyaclub")
                
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
