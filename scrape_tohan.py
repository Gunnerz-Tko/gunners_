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
    """Parse a genre section and extract book rankings"""
    books = []
    lines = [line.strip() for line in section_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} lines...")
    
    # Skip header lines
    i = 0
    while i < len(lines):
        if '書' in lines[i] and '名' in lines[i]:
            i += 1
            break
        i += 1
    
    # Parse books
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for rank number at start
        match = re.match(r'^(\d+)\s+(.+)$', line)
        
        if not match:
            i += 1
            continue
        
        rank = int(match.group(1))
        
        if rank < 1 or rank > 10:
            i += 1
            continue
        
        # Get everything after rank
        rest = match.group(2).strip()
        
        title = ""
        author = ""
        publisher = ""
        price = ""
        isbn = ""
        
        # Collect all lines for this book entry
        book_lines = [rest]
        j = i + 1
        
        while j < len(lines):
            next_line = lines[j]
            
            # Stop if next rank or section
            if re.match(r'^(\d+)\s+', next_line) or '【' in next_line:
                break
            
            book_lines.append(next_line)
            j += 1
        
        # Join all lines for this book
        full_entry = ' '.join(book_lines)
        
        # Now parse: Title Author Publisher Price ISBN
        # Author usually has ／著 or ／原作 or ／漫画
        # Price is always digits with optional commas
        # ISBN starts with 978-
        
        # Extract ISBN (ends the entry)
        isbn_match = re.search(r'(978-[\d-]+)$', full_entry)
        if isbn_match:
            isbn = isbn_match.group(1)
            full_entry = full_entry[:isbn_match.start()].strip()
        
        # Extract PRICE (last sequence of digits/commas before end or ISBN)
        price_match = re.search(r'([\d,]+)\s*$', full_entry)
        if price_match:
            price = price_match.group(1)
            full_entry = full_entry[:price_match.start()].strip()
        
        # Extract AUTHOR (contains ／著, ／原作, ／漫画, ／作 etc)
        author_match = re.search(r'([^／]*／(?:著|原作|漫画|作|編|訳|監修|イラスト)[^\／]*)', full_entry)
        if author_match:
            author = author_match.group(1).strip()
            # Remove author part from entry
            full_entry = full_entry[:author_match.start()].strip() + ' ' + full_entry[author_match.end():].strip()
            full_entry = full_entry.strip()
        
        # Split remaining by multiple spaces to get Publisher and Title
        parts = re.split(r'\s{2,}|\t', full_entry)
        
        if len(parts) >= 2:
            # Last non-empty part is publisher
            publisher = parts[-1].strip()
            # Everything else is title
            title = ' '.join(parts[:-1]).strip()
        else:
            title = full_entry.strip()
        
        # Clean up
        title = title.replace('\n', ' ').strip()
        author = author.replace('\n', ' ').strip()
        publisher = publisher.replace('\n', ' ').strip()
        
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
