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
            # Look in detail table
            for th in soup.find_all('th'):
                if '著者' in th.get_text() or '作者' in th.get_text():
                    author_elem = th.find_next('td')
                    break
        if not author_elem:
            # Look for 著者 (author) text
            author_elem = soup.find(string=re.compile('著者|作者'))
            if author_elem:
                author_elem = author_elem.find_next('span')
        
        if author_elem:
            author = author_elem.get_text(strip=True)
            author = re.sub(r'著者:|著|作|編|訳', '', author).strip()
        
        # Extract publisher - MORE AGGRESSIVE SEARCH
        publisher = "-"
        
        # Method 1: Look in the product details table
        details_table = soup.find('table', class_='productDetails')
        if not details_table:
            details_table = soup.find('table', class_='detailsTable')
        if not details_table:
            details_table = soup.find('div', class_='productInfo')
        
        if details_table:
            rows = details_table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    th_text = th.get_text(strip=True)
                    td_text = td.get_text(strip=True)
                    
                    if '出版社' in th_text or 'Publisher' in th_text:
                        publisher = td_text
                        break
        
        # Method 2: Look for publisher in spans/divs with specific classes
        if publisher == "-":
            for elem in soup.find_all(['span', 'div']):
                class_name = elem.get('class', [])
                if isinstance(class_name, list):
                    class_str = ' '.join(class_name)
                else:
                    class_str = str(class_name)
                
                if 'publisher' in class_str.lower():
                    publisher = elem.get_text(strip=True)
                    break
        
        # Method 3: Look for label+value pattern in the page
        if publisher == "-":
            all_text = soup.get_text()
            publisher_match = re.search(r'出版社\s*[：:]\s*([^\n、。]+)', all_text)
            if publisher_match:
                publisher = publisher_match.group(1).strip()
        
        # Method 4: Search near specific elements
        if publisher == "-":
            for text in soup.find_all(string=re.compile('出版社')):
                parent = text.parent
                # Try to find the publisher name in the next element
                next_elem = parent.find_next(['span', 'div', 'a'])
                if next_elem:
                    potential_publisher = next_elem.get_text(strip=True)
                    if potential_publisher and len(potential_publisher) > 1:
                        publisher = potential_publisher
                        break
        
        # Clean up
        publisher = re.sub(r'出版社:|出版:|Publisher:|Pub\.|発行:', '', publisher).strip()
        
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
