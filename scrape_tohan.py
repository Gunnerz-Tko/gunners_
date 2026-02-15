#!/usr/bin/env python3
import os
import json
import requests
import pdfplumber
from datetime import datetime
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tohan PDF URL
TOHAN_PDF_URL = "https://www.tohan.jp/wp/wp-content/uploads/2026/02/202601.pdf"

# Genre mapping (Japanese to English)
GENRES = [
    "総合",
    "文芸書",
    "ノンフィクション・ライトエッセイ",
    "エンターテイメント",
    "ビジネス書",
    "趣味実用書",
    "生活実用書",
    "児童書",
    "ノベルス",
    "新書",
    "文庫",
    "コミックス"
]

def download_tohan_pdf(url):
    """Download Tohan PDF"""
    print("📥 Downloading Tohan PDF...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        pdf_path = '/tmp/tohan.pdf'
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ PDF downloaded ({len(response.content)} bytes)")
        return pdf_path
    
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return None

def parse_tohan_pdf(pdf_path):
    """Parse Tohan PDF and extract rankings using pdfplumber tables"""
    print("\n📖 Parsing Tohan PDF with table extraction...\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "tohan.jp",
        "genres": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}\n")
            
            # Build full document with page positions
            all_content = []
            for page_idx, page in enumerate(pdf.pages):
                content = {
                    "page": page_idx + 1,
                    "text": page.extract_text(),
                    "tables": page.extract_tables()
                }
                all_content.append(content)
                print(f"📄 Page {page_idx + 1}: Found {len(content['tables'] or [])} tables")
            
            print()
            
            # Now process: for each table, find the closest genre marker before it
            for page_content in all_content:
                page_text = page_content['text']
                tables = page_content['tables'] or []
                
                if not tables:
                    continue
                
                # Find all genre positions in page text
                genre_positions = {}
                for genre in GENRES:
                    marker = f"【{genre}】"
                    pos = page_text.find(marker)
                    if pos != -1:
                        genre_positions[pos] = genre
                        print(f"Page {page_content['page']}: Found 【{genre}】")
                
                # Process each table
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                    
                    headers = table[0]
                    
                    if not is_ranking_table(headers):
                        continue
                    
                    # Find closest genre marker before this table
                    # This is a bit tricky - we assume tables appear in order after their genre marker
                    if genre_positions:
                        # Get the last genre found (closest one)
                        closest_genre = list(genre_positions.values())[-1]
                    else:
                        continue
                    
                    print(f"Page {page_content['page']}: Processing table for 【{closest_genre}】")
                    
                    # Parse table rows
                    books = parse_table_rows(table[1:])
                    
                    if books and closest_genre not in data["genres"]:
                        data["genres"][closest_genre] = books
                        print(f"   ✅ {len(books)} books extracted\n")
                        
                        # Remove this genre so we don't use it for next table
                        for pos, genre in list(genre_positions.items()):
                            if genre == closest_genre:
                                del genre_positions[pos]
                                break
        
        return data
    
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
def find_genre_in_page(page, genres):
    """Find genre marker in page text"""
    text = page.extract_text()
    
    for genre in genres:
        if f"【{genre}】" in text:
            return genre
    
    return None

def is_ranking_table(headers):
    """Check if table headers indicate a ranking table"""
    if not headers:
        return False
    
    headers_str = ' '.join([str(h).strip() for h in headers if h])
    
    # Look for ranking columns
    keywords = ['書名', '著者', '出版社', '本体', 'ISBN']
    matched = sum(1 for kw in keywords if kw in headers_str)
    
    return matched >= 3

def find_genre_in_page(page, genres):
    """Find genre marker in page text"""
    text = page.extract_text()
    
    for genre in genres:
        if f"【{genre}】" in text:
            return genre
    
    return None

def parse_table_rows(rows):
    """Parse table rows into book data"""
    books = []
    
    for row in rows:
        if not row or len(row) < 2:
            continue
        
        # First column is rank
        rank_str = str(row[0]).strip() if row[0] else ""
        
        if not rank_str or not rank_str.isdigit():
            continue
        
        rank = int(rank_str)
        
        if rank < 1 or rank > 10:
            continue
        
        # Extract columns
        title = str(row[1]).strip() if len(row) > 1 and row[1] else "-"
        author = str(row[2]).strip() if len(row) > 2 and row[2] else "-"
        publisher = str(row[3]).strip() if len(row) > 3 and row[3] else "-"
        price = str(row[4]).strip() if len(row) > 4 and row[4] else "-"
        isbn = str(row[5]).strip() if len(row) > 5 and row[5] else "-"
        
        books.append({
            "rank": rank,
            "title": title,
            "author": author,
            "publisher": publisher,
            "price": price,
            "isbn": isbn
        })
        
        print(f"      ✓ Rank {rank}: {title}")
    
    return books[:10]

def main():
    print("📚 Starting Tohan PDF Scraper...\n")
    
    # Download PDF
    pdf_path = download_tohan_pdf(TOHAN_PDF_URL)
    
    if not pdf_path:
        logger.error("Failed to download PDF")
        return
    
    # Parse PDF
    data = parse_tohan_pdf(pdf_path)
    
    if not data:
        logger.error("Failed to parse PDF")
        return
    
    # Generate data.js
    try:
        js_content = f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"\n✅ Successfully saved data.js")
        print(f"📊 Total genres: {len(data['genres'])}")
        
        total_books = 0
        for genre, books in data['genres'].items():
            print(f"   - {genre}: {len(books)} books")
            total_books += len(books)
        
        print(f"\n📈 Total books scraped: {total_books}")
    
    except Exception as e:
        logger.error(f"Error saving data.js: {e}")
    
    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

if __name__ == "__main__":
    main()
