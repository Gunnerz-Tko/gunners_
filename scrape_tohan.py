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
    lines = [line.strip() for line in section_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} lines...")
    
    i = 0
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for rank number (1-10) at start of line
        rank_match = re.match(r'^(\d+)\s+', line)
        
        if rank_match:
            rank_num = int(rank_match.group(1))
            
            if 1 <= rank_num <= 10:
                # Get the rest of the line after rank
                rest_of_line = line[rank_match.end():].strip()
                
                # Title is the rest of this line
                title = rest_of_line
                
                # Next line should be author (contains ／著 or ／作)
                author = ""
                publisher = ""
                price = ""
                isbn = ""
                
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    
                    # Check if it contains author marker
                    if '／著' in next_line or '／作' in next_line:
                        # Extract author (before the marker)
                        if '／著' in next_line:
                            author = next_line.split('／著')[0].strip()
                        else:
                            author = next_line.split('／作')[0].strip()
                    else:
                        # No author marker, might be author or publisher
                        author = next_line
                
                # Next line should be publisher or price
                if i + 2 < len(lines):
                    next_line2 = lines[i + 2]
                    
                    if re.match(r'^[\d,]+$', next_line2):
                        # This is price
                        price = next_line2
                        # Then publisher was at i+1
                        publisher = author
                        author = lines[i + 1]
                    else:
                        # This is publisher
                        publisher = next_line2
                
                # Next line should be price (if not already found)
                if i + 3 < len(lines) and not price:
                    next_line3 = lines[i + 3]
                    if re.match(r'^[\d,]+$', next_line3):
                        price = next_line3
                
                # Next line should be ISBN (if found)
                if i + 4 < len(lines):
                    next_line4 = lines[i + 4]
                    if re.match(r'^978-', next_line4):
                        isbn = next_line4
                
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
                    
                    print(f"      ✓ Rank {rank_num}: {title}")
                    i += 5
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
