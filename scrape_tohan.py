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
    """Parse Tohan PDF and extract rankings using tables"""
    print("\n📖 Parsing Tohan PDF with table extraction...\n")
    
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
    """Parse a genre section and extract book rankings
    
    Structure:
    【Genre】
    書 名 著 者 出版社 本体(円) ISBNコード
    1 Title Author Publisher Price ISBN
    2 Title Author Publisher Price ISBN
    ...
    """
    books = []
    lines = [line.strip() for line in section_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} lines...")
    
    rank = None
    title = None
    author = None
    publisher = None
    price = None
    isbn = None
    
    for line in lines:
        # Skip header lines
        if '書 名' in line or '著 者' in line or '出版社' in line or '本体(円)' in line or 'ISBNコード' in line:
            continue
        
        if line.startswith('【'):
            # Genre marker, skip
            continue
        
        # Try to match: RANK + DATA
        # Format: "1 Title Author Publisher Price ISBN"
        match = re.match(r'^(\d+)\s+(.+)$', line)
        
        if match:
            rank_num = int(match.group(1))
            
            if 1 <= rank_num <= 10:
                # Save previous book if exists
                if rank is not None and title:
                    books.append({
                        "rank": rank,
                        "title": title.strip(),
                        "author": author.strip() if author else "-",
                        "publisher": publisher.strip() if publisher else "-",
                        "price": price.strip() if price else "-",
                        "isbn": isbn.strip() if isbn else "-"
                    })
                    print(f"      ✓ Rank {rank}: {title}")
                
                # Start new book
                rank = rank_num
                remaining_data = match.group(2).strip()
                
                # Split by common delimiters (multiple spaces, tabs)
                parts = re.split(r'\s{2,}|\t', remaining_data)
                
                title = parts[0] if len(parts) > 0 else ""
                author = parts[1] if len(parts) > 1 else ""
                publisher = parts[2] if len(parts) > 2 else ""
                price = parts[3] if len(parts) > 3 else ""
                isbn = parts[4] if len(parts) > 4 else ""
        else:
            # This might be continuation of previous data (multi-line)
            # Try to detect what field this is
            if re.match(r'^978-', line):
                # This is ISBN
                isbn = line
            elif re.match(r'^[\d,]+$', line):
                # This is PRICE
                if not price:
                    price = line
                else:
                    isbn = line
            elif '社' in line or '出版' in line.lower():
                # This might be publisher
                if not publisher:
                    publisher = line
                else:
                    isbn = line
            elif not author and title:
                # This might be author
                author = line
            elif not publisher and title and author:
                # This might be publisher
                publisher = line
    
    # Don't forget last book
    if rank is not None and title:
        books.append({
            "rank": rank,
            "title": title.strip(),
            "author": author.strip() if author else "-",
            "publisher": publisher.strip() if publisher else "-",
            "price": price.strip() if price else "-",
            "isbn": isbn.strip() if isbn else "-"
        })
        print(f"      ✓ Rank {rank}: {title}")
    
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
