import pdfplumber
import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_hanmoto_data(isbn):
    """Fetch book details from Hanmoto using ISBN"""
    try:
        isbn_clean = isbn.replace('-', '')
        url = f'https://www.hanmoto.com/bd/isbn/{isbn_clean}'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_elem = soup.find('h1', class_='bookTitle')
        if not title_elem:
            title_elem = soup.find('h1')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Extract author
        author = "-"
        for dt in soup.find_all('dt'):
            if '著' in dt.get_text() or '編' in dt.get_text():
                dd = dt.find_next('dd')
                if dd:
                    author = dd.get_text(strip=True)
                    break
        
        # Extract publisher
        publisher = "-"
        for dt in soup.find_all('dt'):
            if '発行' in dt.get_text():
                dd = dt.find_next('dd')
                if dd:
                    publisher = dd.get_text(strip=True)
                    break
        
        if title:
            return {
                'title': title,
                'author': author,
                'publisher': publisher
            }
        return None
        
    except Exception as e:
        logger.warning(f"Error fetching Hanmoto for {isbn}: {e}")
        return None

def extract_price(text):
    """Extract price from text"""
    price_match = re.search(r'\b([\d]{1,3}(?:,\d{3})*|\d{3})\b(?![\d\-])', text)
    if price_match:
        price_candidate = price_match.group(1)
        if ',' in price_candidate or (len(price_candidate.replace(',', '')) <= 3):
            return price_candidate
    return "-"

def parse_book_entry(lines, rank):
    """Parse a single book entry and fetch data from Hanmoto"""
    full_text = ' '.join(line.strip() for line in lines if line.strip())
    full_text = re.sub(r'^(\d+)\s+', '', full_text).strip()
    
    # Extract ISBN
    isbn = ""
    isbn_match = re.search(r'(978[\d\-]{10,})', full_text)
    if isbn_match:
        isbn = isbn_match.group(1)
    
    # Extract price
    price = extract_price(full_text)
    
    # Fetch from Hanmoto if ISBN exists
    if isbn:
        logger.info(f"Fetching ISBN {isbn}...")
        hanmoto_data = fetch_hanmoto_data(isbn)
        if hanmoto_data:
            return {
                "rank": rank,
                "title": hanmoto_data['title'],
                "author": hanmoto_data['author'],
                "publisher": hanmoto_data['publisher'],
                "price": price,
                "isbn": isbn
            }
    
    return None

def scrape_tohan_pdf():
    """Scrape Tohan PDF and extract book data"""
    try:
        pdf_url = "https://www.tohan.jp/data/ranking/weekly/pdf/2025-12-01-2025-12-07.pdf"
        response = requests.get(pdf_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to download PDF: {response.status_code}")
            return None
        
        with open('/tmp/tohan.pdf', 'wb') as f:
            f.write(response.content)
        
        books_by_genre = {}
        
        with pdfplumber.open('/tmp/tohan.pdf') as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                current_genre = None
                book_lines = []
                rank = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line is a genre header
                    if line in ["総合", "文芸書", "ノンフィクション・ライトエッセイ", "エンターテイメント", 
                               "ビジネス書", "趣味実用書", "生活実用書", "児童書", "ノベルス", "新書", "文庫", "コミックス"]:
                        if book_lines and current_genre:
                            book_data = parse_book_entry(book_lines, rank)
                            if book_data:
                                if current_genre not in books_by_genre:
                                    books_by_genre[current_genre] = []
                                books_by_genre[current_genre].append(book_data)
                            book_lines = []
                        current_genre = line
                        rank = 0
                    
                    # Check if line starts with a rank number
                    elif re.match(r'^\d+\s+', line):
                        if book_lines and current_genre:
                            book_data = parse_book_entry(book_lines, rank)
                            if book_data:
                                if current_genre not in books_by_genre:
                                    books_by_genre[current_genre] = []
                                books_by_genre[current_genre].append(book_data)
                        rank = int(re.match(r'^(\d+)', line).group(1))
                        book_lines = [line]
                    else:
                        if current_genre:
                            book_lines.append(line)
                
                # Process last book
                if book_lines and current_genre:
                    book_data = parse_book_entry(book_lines, rank)
                    if book_data:
                        if current_genre not in books_by_genre:
                            books_by_genre[current_genre] = []
                        books_by_genre[current_genre].append(book_data)
        
        return books_by_genre
        
    except Exception as e:
        logger.error(f"Error scraping PDF: {e}")
        return None

def main():
    logger.info("Starting Tohan scraper...")
    books = scrape_tohan_pdf()
    
    if books:
        data = {
            "updated": datetime.now().isoformat(),
            "genres": books
        }
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};")
        
        logger.info("✓ data.js updated successfully!")
    else:
        logger.error("No data extracted")

if __name__ == "__main__":
    main()
