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

TOHAN_PDF_URL = "https://www.tohan.jp/wp/wp-content/uploads/2026/02/202601.pdf"

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
        
        print(f"✅ PDF downloaded ({len(response.content)} bytes)\n")
        return pdf_path
    
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return None

def parse_tohan_pdf(pdf_path):
    """Parse Tohan PDF and extract rankings from text"""
    print("📖 Parsing Tohan PDF...\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "tohan.jp",
        "genres": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}\n")
            
            # Extract all text
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Parse each genre
            for genre in GENRES:
                print(f"🔍 Extracting 【{genre}】...")
                
                genre_pattern = f"【{genre}】"
                
                if genre_pattern not in full_text:
                    print(f"   ⚠️  Not found\n")
                    continue
                
                # Find start and end of genre section
                start_idx = full_text.find(genre_pattern)
                
                end_idx = len(full_text)
                for next_genre in GENRES:
                    if next_genre != genre:
                        next_idx = full_text.find(f"【{next_genre}】", start_idx + 1)
                        if next_idx != -1 and next_idx < end_idx:
                            end_idx = next_idx
                
                genre_section = full_text[start_idx:end_idx]
                
                # Parse books
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
    """Parse a genre section and extract books"""
    books = []
    lines = [line.rstrip() for line in section_text.split('\n')]
    
    # Find header line with column names
    header_idx = -1
    for i, line in enumerate(lines):
        if '書' in line and '名' in line:
            header_idx = i
            break
    
    if header_idx == -1:
        return []
    
    # Parse data lines starting after header
    i = header_idx + 1
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for rank (1-10) at start
        match = re.match(r'^(\d+)\s+', line)
        
        if not match:
            i += 1
            continue
        
        rank = int(match.group(1))
        if rank < 1 or rank > 10:
            i += 1
            continue
        
        # Collect all lines for this book entry
        book_data = [line]
        i += 1
        
        # Continue until next rank or end
        while i < len(lines):
            next_line = lines[i]
            
            # Stop at next rank or genre
            if re.match(r'^(\d+)\s+', next_line) or '【' in next_line:
                break
            
            # Stop at page marker or section separator
            if 'トーハン' in next_line or next_line.strip() == '':
                if i + 1 < len(lines) and re.match(r'^(\d+)\s+', lines[i + 1]):
                    i += 1
                    break
            
            book_data.append(next_line)
            i += 1
        
        # Parse the book data
        book = parse_book_entry(book_data, rank)
        if book:
            books.append(book)
            print(f"      ✓ Rank {rank}: {book['title']}")
    
    return books

def parse_book_entry(lines, rank):
    """Parse a single book entry from multiple lines"""
    
    # Join all lines
    full_text = ' '.join(line.strip() for line in lines if line.strip())
    
    # Remove rank number from start
    full_text = re.sub(r'^(\d+)\s+', '', full_text).strip()
    
    # Extract ISBN (last element, starts with 978-)
    isbn = ""
    isbn_match = re.search(r'(978-[\d-]+)$', full_text)
    if isbn_match:
        isbn = isbn_match.group(1)
        full_text = full_text[:isbn_match.start()].strip()
    
    # Extract PRICE (sequence of digits/commas before end or ISBN)
    price = ""
    price_match = re.search(r'([\d,]+)\s*$', full_text)
    if price_match:
        price = price_match.group(1)
        full_text = full_text[:price_match.start()].strip()
    
    # Extract AUTHOR (contains ／著, ／原作, ／漫画, ���作, ／編, ／訳, ／監修, ／イラスト)
    author = ""
    author_match = re.search(
        r'((?:[^\s／]*／(?:著|原作|漫画|作|編|訳|監修|イラスト|ストーリー協力))+(?:\s+[^\s／]*／(?:著|原作|漫画|作|編|訳|監修|イラスト|ストーリー協力))*)',
        full_text
    )
    if author_match:
        author = author_match.group(1).strip()
        # Remove author from full_text
        full_text = full_text[:author_match.start()].strip() + ' ' + full_text[author_match.end():].strip()
        full_text = full_text.strip()
    
    # Remaining text: Publisher and Title
    # Publisher is usually the last part after multiple spaces
    parts = re.split(r'\s{2,}', full_text)
    
    if len(parts) >= 2:
        # Last part is publisher
        publisher = parts[-1].strip()
        # Everything else is title
        title = ' '.join(parts[:-1]).strip()
    else:
        # Only one part - it's the title
        title = full_text.strip()
        publisher = ""
    
    # Clean up
    title = re.sub(r'\s+', ' ', title).strip()
    author = re.sub(r'\s+', ' ', author).strip()
    publisher = re.sub(r'\s+', ' ', publisher).strip()
    
    if not title:
        return None
    
    return {
        "rank": rank,
        "title": title,
        "author": author if author else "-",
        "publisher": publisher if publisher else "-",
        "price": price if price else "-",
        "isbn": isbn if isbn else "-"
    }

def main():
    print("📚 Starting Tohan PDF Scraper...\n")
    
    pdf_path = download_tohan_pdf(TOHAN_PDF_URL)
    if not pdf_path:
        return
    
    data = parse_tohan_pdf(pdf_path)
    if not data:
        return
    
    # Save data.js
    try:
        js_content = f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"✅ Successfully saved data.js")
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
