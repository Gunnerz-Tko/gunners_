import pytesseract
import easyocr
from PIL import Image
import json
from datetime import datetime
import re
import os
import difflib

# Configuration
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows
# TESSERACT_PATH = "/usr/bin/tesseract"  # Linux/Mac

def load_corrections():
    """Load corrections from books_corrections.json"""
    try:
        with open('books_corrections.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('corrections', {})
    except Exception as e:
        print(f"⚠️  Could not load corrections: {e}")
        return {}

def find_correction(title, corrections_by_genre):
    """Find correction for a title with fuzzy matching"""
    
    # Normalize title (remove extra spaces)
    title_normalized = ' '.join(title.split())
    
    for genre, books in corrections_by_genre.items():
        for book in books:
            book_title = book['title']
            book_title_normalized = ' '.join(book_title.split())
            
            # Exact match
            if title_normalized.lower() == book_title_normalized.lower():
                return book
            
            # Fuzzy match (85% similarity)
            similarity = difflib.SequenceMatcher(None, title_normalized.lower(), book_title_normalized.lower()).ratio()
            if similarity > 0.85:
                print(f"   🔗 Fuzzy matched: {title_normalized} ≈ {book_title_normalized} ({similarity*100:.0f}%)")
                return book
    
    return None

def extract_with_tesseract(image_path):
    """Extract text using Tesseract OCR"""
    try:
        print("   📄 Trying Tesseract OCR...")
        
        # Set Tesseract path if on Windows
        if os.name == 'nt':
            pytesseract.pytesseract.pytesseract_cmd = TESSERACT_PATH
        
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='jpn+eng')
        
        if len(text.strip()) > 50:
            print("   ✅ Tesseract successful!")
            return text
        else:
            print("   ⚠️  Tesseract returned too little text")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Tesseract error: {e}")
        return None

def extract_with_easyocr(image_path):
    """Extract text using EasyOCR"""
    try:
        print("   📄 Trying EasyOCR...")
        
        reader = easyocr.Reader(['ja', 'en'], gpu=False)
        results = reader.readtext(image_path)
        
        # Extract text with confidence scores
        text_lines = []
        for item in results:
            if len(item) >= 2:
                text = item[1]
                confidence = item[2] if len(item) > 2 else 0
                
                if confidence > 0.3:  # Only keep if 30%+ confidence
                    text_lines.append(text)
        
        text = '\n'.join(text_lines)
        
        if len(text.strip()) > 50:
            print("   ✅ EasyOCR successful!")
            return text
        else:
            print("   ⚠️  EasyOCR returned too little text")
            return None
            
    except Exception as e:
        print(f"   ⚠️  EasyOCR error: {e}")
        return None

def extract_text_from_image(image_path):
    """Extract text from image - try Tesseract first, fallback to EasyOCR"""
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    print(f"\n🖼️  Processing: {image_path}")
    
    # Try Tesseract first (faster)
    text = extract_with_tesseract(image_path)
    
    # If Tesseract fails, try EasyOCR
    if not text:
        text = extract_with_easyocr(image_path)
    
    if not text:
        print(f"❌ Could not extract text from image")
        return None
    
    return text

def parse_ranking_table(text):
    """Parse OCR text into structured ranking data"""
    
    books = []
    lines = text.strip().split('\n')
    
    print("   📊 Parsing table...")
    
    for line in lines:
        # Clean up line
        line = line.strip()
        if not line or len(line) < 5:
            continue
        
        # Remove extra spaces
        line = ' '.join(line.split())
        
        try:
            # Try to match pattern: "Rank  Title  Author  Publisher"
            # Split by multiple spaces or tabs
            parts = re.split(r'\s{2,}|\t', line)
            
            if len(parts) >= 3:
                rank_str = parts[0].strip()
                
                # Check if first part is a number (rank)
                if rank_str.isdigit():
                    rank = int(rank_str)
                    
                    # Handle variable number of columns
                    if len(parts) >= 4:
                        title = parts[1].strip()
                        author = parts[2].strip()
                        publisher = parts[3].strip()
                    elif len(parts) == 3:
                        title = parts[1].strip()
                        author = "-"
                        publisher = "-"
                    else:
                        continue
                    
                    # Filter out price data (円 symbol)
                    if '円' in publisher:
                        publisher = publisher.split('円')[0].strip()
                    if '円' in author:
                        author = author.split('円')[0].strip()
                    
                    books.append({
                        "rank": rank,
                        "title": title,
                        "author": author,
                        "publisher": publisher
                    })
        
        except Exception as e:
            continue
    
    print(f"   ✅ Parsed {len(books)} books")
    return books

def scrape_from_image(image_path):
    """Main function: extract data from image and save to JSON"""
    
    try:
        # Load corrections
        corrections = load_corrections()
        print(f"📋 Loaded corrections: {len(corrections)} genres")
        
        # Extract text from image
        text = extract_text_from_image(image_path)
        
        if not text:
            print("❌ Failed to extract text from image")
            return
        
        print("\n📝 Extracted text:")
        print("=" * 50)
        print(text[:500])  # Print first 500 chars
        print("=" * 50)
        
        # Parse into table
        extracted_books = parse_ranking_table(text)
        
        # Create output structure
        data = {
            "updated": datetime.now().isoformat() + "Z",
            "source": f"image: {image_path}",
            "genres": {
                "General": [],
                "Paperback": [],
                "Comics": []
            }
        }
        
        general_count = 0
        paperback_count = 0
        comics_count = 0
        
        print(f"\n🔍 Matching with corrections...\n")
        
        for book in extracted_books:
            rank = book['rank']
            title = book['title']
            
            print(f"📖 {rank}. {title}")
            
            # Try to find correction
            correction = find_correction(title, corrections)
            
            if correction:
                author = correction.get('author', '-')
                publisher = correction.get('publisher', '-')
                print(f"   ✅ Correction found!")
            else:
                author = book['author']
                publisher = book['publisher']
                print(f"   ℹ️  Using extracted data")
            
            print(f"   Author: {author}")
            print(f"   Publisher: {publisher}\n")
            
            book_data = {
                "rank": rank,
                "last_week": "-",
                "title": title,
                "author": author,
                "publisher": publisher,
                "image": ""
            }
            
            # Distribute to genres
            if general_count < 10:
                data["genres"]["General"].append(book_data)
                general_count += 1
            elif paperback_count < 10:
                data["genres"]["Paperback"].append(book_data)
                paperback_count += 1
            elif comics_count < 10:
                data["genres"]["Comics"].append(book_data)
                comics_count += 1
        
        # Save to file
        with open('nippan_books.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Scraping completed!")
        print(f"📚 General: {len(data['genres']['General'])} books")
        print(f"📚 Paperback: {len(data['genres']['Paperback'])} books")
        print(f"📚 Comics: {len(data['genres']['Comics'])} books")
        print(f"💾 Saved to: nippan_books.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default: look for screenshot.png in current directory
        image_path = "screenshot.png"
    
    scrape_from_image(image_path)
