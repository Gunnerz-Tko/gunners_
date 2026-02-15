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

# Genre order
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
    """Parse Tohan PDF and extract rankings from text"""
    print("\n📖 Parsing Tohan PDF...\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "tohan.jp",
        "genres": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}\n")
            
            # Extract all text from PDF
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Parse each genre
            for genre in GENRES:
                print(f"🔍 Extracting 【{genre}】...")
                
                # Find genre section
                genre_pattern = f"【{genre}】"
                
                if genre_pattern not in full_text:
                    print(f"   ⚠️  Not found\n")
                    continue
                
                # Find start of this genre section
                start_idx = full_text.find(genre_pattern)
                
                # Find start of next genre section (or end of document)
                end_idx = len(full_text)
                for next_genre in GENRES:
                    if next_genre != genre:
                        next_idx = full_text.find(f"【{next_genre}��", start_idx + 1)
                        if next_idx != -1 and next_idx < end_idx:
                            end_idx = next_idx
                
                # Extract genre section
                genre_section = full_text[start_idx:end_idx]
                
                # Parse books in this section
                books = parse_genre_section(genre_section)
                
                if books:
                    data["genres"][genre] = books
                    print(f"   ✅ {len(books)} books extracted\n")
                else:
                    print(f"   ⚠️  No books found\n")
        
        return data
    
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_genre_section(section_text):
    """Parse a genre section and extract book rankings
    
    Format:
    【Genre】
    書 名 著者 出版社 本体(円) ISBNコード
    1 Title Author Publisher Price ISBN
    2 Title Author Publisher Price ISBN
    ...
    10 Title Author Publisher Price ISBN
    """
    books = []
    lines = [line.strip() for line in section_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} lines...")
    
    # Skip header lines (書 名, 著者, etc)
    i = 0
    while i < len(lines):
        if '書' in lines[i] and '名' in lines[i]:
            i += 1
            break
        i += 1
    
    # Parse books (ranks 1-20, but take only top 10)
    rank_count = 0
    while i < len(lines) and rank_count < 10:
        line = lines[i]
        
        # Look for rank number at start: "1 ", "2 ", etc.
        match = re.match(r'^(\d+)\s+(.+)$', line)
        
        if not match:
            i += 1
            continue
        
        rank = int(match.group(1))
        
        # Only process ranks 1-10
        if rank < 1 or rank > 10:
            i += 1
            continue
        
        # Get the rest of the line after rank
        rest = match.group(2).strip()
        
        # Split by multiple spaces or tabs to separate fields
        # Pattern: Title  Author  Publisher  Price  ISBN
        parts = re.split(r'\s{2,}|\t', rest)
        
        title = parts[0] if len(parts) > 0 else ""
        author = parts[1] if len(parts) > 1 else ""
        publisher = parts[2] if len(parts) > 2 else ""
        price = parts[3] if len(parts) > 3 else ""
        isbn = parts[4] if len(parts) > 4 else ""
        
        # Look ahead for continuation lines
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            
            # Stop if we hit next rank
            if re.match(r'^(\d+)\s+', next_line):
                break
            
            # Stop if we hit next genre or section
            if '【' in next_line:
                break
            
            # Check what field this line belongs to
            if re.match(r'^978-', next_line):
                # This is ISBN
                isbn = next_line
            elif re.match(r'^[\d,]+$', next_line):
                # This is PRICE
                if not price:
                    price = next_line
                else:
                    isbn = next_line
            elif not author or (author == "" or "/" not in author):
                # Likely author (contains ／)
                if "/" in next_line or not author:
                    author += " " + next_line if author else next_line
            elif not publisher:
                # Continuation of publisher
                publisher += " " + next_line
            elif not title:
                # Continuation of title
                title += " " + next_line
            
            j += 1
        
        # Clean up fields
        title = title.replace('\n', ' ').strip()
        author = author.replace('\n', ' ').strip()
        publisher = publisher.replace('\n', ' ').strip()
        price = price.strip()
        isbn = isbn.strip()
        
        if title:
            books.append({
                "rank": rank,
                "title": title,
                "author": author if author else "-",
                "publisher": publisher if publisher else "-",
                "price": price if price else "-",
                "isbn": isbn if isbn else "-"
            })
            print(f"      ✓ Rank {rank}: {title}")
            rank_count += 1
        
        i = j if j > i + 1 else i + 1
    
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
