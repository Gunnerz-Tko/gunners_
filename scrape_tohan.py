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
    """Parse a genre section and extract book rankings
    
    Expected format:
    1 Title Author Publisher Price ISBN
    2 Title Author Publisher Price ISBN
    ...
    """
    books = []
    lines = [line.strip() for line in section_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} lines...")
    
    i = 0
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for RANK number (1-10) at start of line
        rank_match = re.match(r'^(\d+)\s+(.*)$', line)
        
        if rank_match:
            rank_num = int(rank_match.group(1))
            
            if 1 <= rank_num <= 10:
                # Start collecting data for this book
                title = ""
                author = ""
                publisher = ""
                price = ""
                isbn = ""
                
                # Line i: RANK + remaining text
                remaining = rank_match.group(2).strip()
                
                # Check if title is on same line
                if remaining:
                    title = remaining
                    current_line = i + 1
                else:
                    # Title is on next line
                    if i + 1 < len(lines):
                        title = lines[i + 1]
                    current_line = i + 2
                
                # Now collect author, publisher, price, ISBN from following lines
                # until we hit another RANK or end
                data_lines = []
                j = current_line
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Check if this is a new RANK
                    if re.match(r'^(\d+)\s+', next_line):
                        break
                    
                    data_lines.append(next_line)
                    j += 1
                
                # Parse data_lines: author, publisher, price, isbn
                if len(data_lines) > 0:
                    author = data_lines[0]
                
                if len(data_lines) > 1:
                    publisher = data_lines[1]
                
                if len(data_lines) > 2:
                    price = data_lines[2]
                
                if len(data_lines) > 3:
                    isbn = data_lines[3]
                
                # Validate data
                if title and len(title) > 2:
                    books.append({
                        "rank": rank_num,
                        "title": title.strip(),
                        "author": author.strip() if author else "-",
                        "publisher": publisher.strip() if publisher else "-",
                        "price": price.strip() if price else "-",
                        "isbn": isbn.strip() if isbn else "-"
                    })
                    
                    print(f"      ✓ Rank {rank_num}: {title} | {author}")
                
                i = j
                continue
        
        i += 1
    
    return books

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
