#!/usr/bin/env python3
import os
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easyocr
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des URLs Oricon
ORICON_URLS = {
    "Comics": "https://www.oricon.co.jp/rank/obc/w/2026-02-16/",
    "Paperback": "https://www.oricon.co.jp/rank/obb/w/2026-02-16/",
    "Light Novel": "https://www.oricon.co.jp/rank/obl/w/2026-02-16/",
    "Light Literature": "https://www.oricon.co.jp/rank/obll/w/2026-02-16/",
    "Literary": "https://www.oricon.co.jp/rank/oba/w/2026-02-16/"
}

def setup_driver():
    """Setup Chrome WebDriver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    return driver

def scrape_oricon_page(url, genre, reader):
    """Scrape Oricon page with EasyOCR"""
    print(f"\n🔄 Scraping {genre}...")
    
    driver = None
    books = []
    
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(4)
        
        # Scroll to load all content
        for _ in range(5):
            driver.execute_script("window.scrollBy(0, window.innerHeight)")
            time.sleep(1)
        
        # Take full page screenshot
        screenshot_path = f'/tmp/oricon_{genre}.png'
        driver.save_screenshot(screenshot_path)
        
        print(f"   📸 Screenshot saved: {screenshot_path}")
        
        # EasyOCR extraction (Japanese + English)
        print(f"   🔍 Running EasyOCR on image...")
        results = reader.readtext(screenshot_path, detail=1)
        
        # Convert OCR results to text
        ocr_text = "\n".join([text[1] for text in results])
        
        print(f"   📝 OCR text extracted ({len(ocr_text)} chars)")
        
        # Parse OCR text
        books = parse_ocr_text(ocr_text)
        
        print(f"   ✅ {genre}: {len(books)} books extracted")
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        
        return books[:10]
    
    except Exception as e:
        logger.error(f"Error scraping {genre}: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        if driver:
            driver.quit()

def parse_ocr_text(ocr_text):
    """Parse EasyOCR text to extract book rankings
    
    Format expected:
    1
    チェンソーマン 23
    藤本タツキ
    集英社
    2026年02月
    572円(税込)
    81,020
    """
    books = []
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    
    i = 0
    
    while i < len(lines) and len(books) < 10:
        line = lines[i]
        
        # Look for rank number (1-10)
        rank_match = re.match(r'^(\d+)$', line)
        
        if rank_match:
            rank = int(rank_match.group(1))
            
            if 1 <= rank <= 10:
                # Next line should be title
                if i + 1 < len(lines):
                    title = lines[i + 1]
                    
                    # Next line should be author
                    author = lines[i + 2] if i + 2 < len(lines) else "-"
                    
                    # Next line should be publisher
                    publisher = lines[i + 3] if i + 3 < len(lines) else "-"
                    
                    # Skip date (i+4)
                    # Skip price (i+5)
                    
                    # Sales should be at i+6
                    sales = lines[i + 6] if i + 6 < len(lines) else "-"
                    
                    # Clean up sales (remove non-digits except comma)
                    sales_clean = re.sub(r'[^\d,]', '', sales)
                    
                    # Validate title (should not be empty or a number)
                    if title and len(title) > 2 and not re.match(r'^\d+$', title):
                        books.append({
                            "rank": rank,
                            "title": title,
                            "author": author if author and author != "-" else "-",
                            "publisher": publisher if publisher and publisher != "-" else "-",
                            "sales": sales_clean if sales_clean else "-"
                        })
                        
                        print(f"      Rank {rank}: {title} by {author}")
                        i += 7
                        continue
        
        i += 1
    
    return books

def main():
    print("📚 Starting Oricon OCR Scraper (EasyOCR)...\n")
    print(f"⏰ Time: {datetime.now().isoformat()}\n")
    
    # Initialize EasyOCR reader (Japanese + English)
    print("🚀 Initializing EasyOCR reader...")
    reader = easyocr.Reader(['ja', 'en'], gpu=False)
    print("✅ EasyOCR ready!\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "oricon.co.jp",
        "genres": {}
    }
    
    for genre, url in ORICON_URLS.items():
        books = scrape_oricon_page(url, genre, reader)
        data["genres"][genre] = books
        time.sleep(3)  # Be polite to Oricon
    
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

if __name__ == "__main__":
    main()
