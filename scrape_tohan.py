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
GENRES = {
    "総合": "Overall",
    "文芸書": "Literary",
    "ノンフィクション・ライトエッセイ": "Non-Fiction",
    "エンターテイメント": "Entertainment",
    "ビジネス書": "Business",
    "趣味実用書": "Hobby & Practical",
    "生活実用書": "Life & Practical",
    "児童書": "Children",
    "ノベルス": "Novels",
    "新書": "New Books",
    "文庫": "Bunko",
    "コミックス": "Comics"
}

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
    """Parse Tohan PDF and extract rankings"""
    print("\n📖 Parsing Tohan PDF...\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "tohan.jp",
        "genres": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}\n")
            
            # Extract text from all pages
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Split by genre
            for genre_jp, genre_en in GENRES.items():
                print(f"🔍 Extracting {genre_jp} ({genre_en})...")
                
                # Find genre section
                genre_pattern = f"【{genre_jp}】"
                
                if genre_pattern in full_text:
                    # Find section start
                    start_idx = full_text.find(genre_pattern)
                    
                    # Find next genre or end
                    next_genre_idx = len(full_text)
                    for other_jp in GENRES.keys():
                        if other_jp != genre_jp:
                            idx = full_text.find(f"【{other_jp}】", start_idx + 1)
                            if idx != -1 and idx < next_genre_idx:
                                next_genre_idx = idx
                    
                    # Extract genre section
                    genre_section = full_text[start_idx:next_genre_idx]
                    
                    # Parse rankings
                    books = parse_genre_section(genre_section)
                    
                    data["genres"][genre_jp] = books
                    print(f"   ✅ {len(books)} books extracted\n")
                else:
                    print(f"   ⚠️  Genre not found\n")
                    data["genres"][genre_jp] = []
        
        return data
    
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_genre_section(section_text):
    """Parse a genre section and extract book rankings"""
    books = []
    
    lines = section_text.split('\n')
    
    current_rank = None
    current_title = None
    current_author = None
    current_publisher = None
    current_price = None
    current_isbn = None
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Look for rank number (1-10)
        rank_match = re.match(r'^(\d+)\s+', line)
        
        if rank_match:
            # Save previous book if exists
            if current_rank and current_title:
                books.append({
                    "rank": current_rank,
                    "title": current_title,
                    "author": current_author or "-",
                    "publisher": current_publisher or "-",
                    "price": current_price or "-",
                    "isbn": current_isbn or "-"
                })
            
            # Start new book
            current_rank = int(rank_match.group(1))
            
            # Extract title from rest of line
            rest = line[rank_match.end():].strip()
            current_title = rest if rest else None
            current_author = None
            current_publisher = None
            current_price = None
            current_isbn = None
        
        elif current_rank and not current_author:
            # Next line after rank is usually author
            if '／著' in line:
                current_author = line.replace('／著', '').strip()
            elif '／作' in line:
                current_author = line.replace('／作', '').strip()
            elif re.match(r'^[\d,]+$', line):
                # This might be price
                current_price = line
            else:
                current_author = line
        
        elif current_rank and current_author and not current_publisher:
            # After author comes publisher
            if re.match(r'^[\d,]+$', line):
                current_price = line
            elif re.match(r'^978-', line):
                current_isbn = line
            else:
                current_publisher = line
        
        elif current_rank and current_publisher and not current_price:
            # After publisher comes price
            if re.match(r'^[\d,]+$', line):
                current_price = line
            elif re.match(r'^978-', line):
                current_isbn = line
        
        elif current_rank and current_price and not current_isbn:
            # After price comes ISBN
            if re.match(r'^978-', line):
                current_isbn = line
    
    # Don't forget last book
    if current_rank and current_title:
        books.append({
            "rank": current_rank,
            "title": current_title,
            "author": current_author or "-",
            "publisher": current_publisher or "-",
            "price": current_price or "-",
            "isbn": current_isbn or "-"
        })
    
    return books[:10]  # Return top 10

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
