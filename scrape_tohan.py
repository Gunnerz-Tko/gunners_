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
    
    # Find header line with column names (if it exists)
    header_idx = -1
    for i, line in enumerate(lines):
        if '書' in line and '名' in line:
            header_idx = i
            break
    
    # If no header found, start from first line after genre marker
    if header_idx == -1:
        # Find the genre marker line
        for i, line in enumerate(lines):
            if '【' in line and '】' in line:
                header_idx = i
                break
    
    if header_idx == -1:
        return []
    
    # Parse data lines starting after header/genre marker
    i = header_idx + 1
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for rank (1-10) at start
        match = re.match(r'^(\d+)\s+', line)
        
        if not match:
            i += 1
            continue
        
        rank = int(match.group(1))
        # Only process ranks 1-10
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
            if 'トーハン' in next_line:
                i += 1
                break
            
            # Skip empty lines but continue
            if next_line.strip():
                book_data.append(next_line)
            
            i += 1
        
        # Parse the book data
        book = parse_book_entry(book_data, rank)
        if book:
            books.append(book)
            print(f"      ✓ Rank {rank}: {book['title']}")
    
    return books

# List of known publishers
# List of known publishers
PUBLISHERS = [
    "SBクリエイティブ", "KADOKAWA", "幸福の科学出版", "オレンジページ", "小学館",
    "神宮館", "Gakken", "朝日新聞出版", "ワン･パブリッシング", "幻冬舎",
    "日本経済新聞出版", "高橋書店", "ときわ総合サービス", "サンクチュアリ出版",
    "1万年堂出版", "PHP研究所", "毎日新聞出版", "日経BP", "ブラウンズブックス",
    "スイッチ･パブリッシング", "すばる舎", "サンマーク出版", "ワニブックス",
    "マガジンハウス", "福音館書店", "岩崎書店", "ハーパーコリンズ･ジャパン",
    "文藝春秋", "新潮社", "双葉社", "飛鳥新社", "講談社", "東京創元社",
    "宝島社", "ダイヤモンド社", "東洋経済新報社", "朝日新聞出版", "新星出版社",
    "中央公論新社", "集英社", "光文社", "クラーケンコミックス", "NHK出版"
]

def parse_book_entry(lines, rank):
    """Parse a single book entry from multiple lines"""
    
    # Join all lines
    full_text = ' '.join(line.strip() for line in lines if line.strip())
    
    # Remove rank number from start
    full_text = re.sub(r'^(\d+)\s+', '', full_text).strip()
    
    # Remove dash characters (―)
    full_text = full_text.replace('―', '').replace('――――――――', '').strip()
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    # Extract ISBN (starts with 978 and has digits/dashes)
    isbn = ""
    isbn_match = re.search(r'(978[\d\-]{10,})', full_text)
    if isbn_match:
        isbn = isbn_match.group(1)
        full_text = full_text[:isbn_match.start()].strip() + ' ' + full_text[isbn_match.end():].strip()
        full_text = full_text.strip()
    
    # Extract PRICE (3+ digits or digits with commas)
    price = ""
    price_match = re.search(r'\b([\d,]{3,}|\d{3,})\b(?![\d\-])', full_text)
    if price_match:
        price = price_match.group(1)
        full_text = full_text[:price_match.start()].strip() + ' ' + full_text[price_match.end():].strip()
        full_text = full_text.strip()
    
    # Extract AUTHOR - always contains ／
    # Can be: Name／著, Name／編著, Name／作, Name／原作, Name／漫画, etc.
    # Multiple authors: Name1／著　Name2／著 or Name1／著　Name2／漫画
    author = ""
    # Match: text with ／ followed by 著/編著/作/原作/漫画/編/訳/監修/イラスト/ストーリー協力
    author_pattern = r'([^\s／]+(?:／(?:著|編著|作|原作|漫画|編|訳|監修|イラスト|ストーリー協力))+(?:\s+[^\s／]+(?:／(?:著|編著|作|原作|漫画|編|訳|監修|イラスト|ストーリー協力))+)*)'
    author_match = re.search(author_pattern, full_text)
    
    if author_match:
        author = author_match.group(1).strip()
        # Remove author from full_text
        full_text = full_text[:author_match.start()].strip() + ' ' + full_text[author_match.end():].strip()
        full_text = full_text.strip()
    
    # Extract PUBLISHER (match known publishers or words ending with 社)
    publisher = ""
    
    # First, try to match known publishers
    for pub in sorted(PUBLISHERS, key=len, reverse=True):  # Longest first
        if pub in full_text:
            publisher = pub
            # Remove publisher from full_text
            idx = full_text.find(pub)
            full_text = full_text[:idx].strip() + ' ' + full_text[idx + len(pub):].strip()
            full_text = full_text.strip()
            break
    
    # If no known publisher found, look for word ending with 社
    if not publisher:
        society_match = re.search(r'(\S+社)', full_text)
        if society_match:
            publisher = society_match.group(1)
            # Remove publisher from full_text
            full_text = full_text[:society_match.start()].strip() + ' ' + full_text[society_match.end():].strip()
            full_text = full_text.strip()
    
    # What remains is the TITLE
    title = full_text.strip()
    
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

def correct_overall_from_other_genres(data):
    """Not needed - OVERALL tab removed"""
    return data
    
    overall_books = data["genres"]["総合"]
    
    # Build a reference map from all other genres
    reference_map = {}  # title -> book data
    
    for genre, books in data["genres"].items():
        if genre == "総合":
            continue
        
        for book in books:
            title = book["title"].lower().strip()
            # Use this genre's data as reference if not already set
            if title not in reference_map:
                reference_map[title] = book.copy()
    
    # Correct overall books using reference map
    corrected_books = []
    for book in overall_books:
        title = book["title"].lower().strip()
        
        # Check if this title exists in other genres
        if title in reference_map:
            ref_book = reference_map[title]
            # Use reference data to fill in missing fields
            corrected = {
                "rank": book["rank"],
                "title": ref_book["title"],  # Use correct title from other genre
                "author": ref_book["author"] if ref_book["author"] != "-" else book["author"],
                "publisher": ref_book["publisher"] if ref_book["publisher"] != "-" else book["publisher"],
                "price": ref_book["price"] if ref_book["price"] != "-" else book["price"],
                "isbn": ref_book["isbn"] if ref_book["isbn"] != "-" else book["isbn"]
            }
            corrected_books.append(corrected)
        else:
            # Keep original if no reference found
            corrected_books.append(book)
    
    data["genres"]["総合"] = corrected_books
    return data

def main():
    print("📚 Starting Tohan PDF Scraper...\n")
    
    pdf_path = download_tohan_pdf(TOHAN_PDF_URL)
    if not pdf_path:
        return
    
    data = parse_tohan_pdf(pdf_path)
    if not data:
        return
    
    # Correct OVERALL genre using other genres
    data = correct_overall_from_other_genres(data)
    
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
