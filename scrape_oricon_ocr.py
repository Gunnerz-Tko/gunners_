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
import pytesseract
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def scrape_oricon_page(url, genre):
    """Scrape Oricon page with Tesseract OCR"""
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
        
        print(f"   📸 Screenshot saved")
        
        # Tesseract OCR (Japanese config)
        print(f"   🔍 Running Tesseract OCR...")
        image = Image.open(screenshot_path)
        
        # Use jpn config for better Japanese recognition
        ocr_text = pytesseract.image_to_string(image, lang='jpn')
        
        print(f"   📝 OCR text extracted ({len(ocr_text)} chars)")
        
        # Parse OCR text
        books = parse_ocr_text(ocr_text)
        
        print(f"   ✅ {genre}: {len(books)} books extracted")
        
        # Log first book for debugging
        if books:
            print(f"      Sample: Rank {books[0]['rank']} - {books[0]['title']}")
        
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
    """Parse Tesseract OCR text to extract book rankings
    
    Expected format from Oricon:
    1
    チェンソーマン 23
    藤本タツキ
    集英社
    2026年02月
    572円
    81,020
    
    2
    ...
    """
    books = []
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    
    print(f"   📋 Processing {len(lines)} OCR lines...")
    
    i = 0
    rank_found = 0
    
    while i < len(lines) and rank_found < 10:
        line = lines[i]
        
        # Look for rank number (1-10)
        rank_match = re.match(r'^(\d+)$', line)
        
        if rank_match:
            rank_num = int(rank_match.group(1))
            
            if 1 <= rank_num <= 10:
                print(f"      Found Rank {rank_num} at line {i}")
                
                # Title should be next
                title = ""
                author = ""
                publisher = ""
                sales = ""
                
                if i + 1 < len(lines):
                    title = lines[i + 1]
                
                if i + 2 < len(lines):
                    author = lines[i + 2]
                
                if i + 3 < len(lines):
                    publisher = lines[i + 3]
                
                # Sales might be 3-4 lines after publisher
                for j in range(i + 4, min(i + 8, len(lines))):
                    line_check = lines[j]
                    # Sales line contains numbers
                    if re.search(r'\d{3,}', line_check):
                        sales = line_check
                        break
                
                # Validate and clean data
                if title and len(title) > 2 and not re.match(r'^[\d\s]+$', title):
                    # Clean sales (keep only digits and comma)
                    sales_clean = re.sub(r'[^\d,]', '', sales)
                    
                    books.append({
                        "rank": rank_num,
                        "title": title.strip(),
                        "author": author.strip() if author else "-",
                        "publisher": publisher.strip() if publisher else "-",
                        "sales": sales_clean if sales_clean else "-"
                    })
                    
                    print(f"         ✓ {title}")
                    rank_found += 1
                    i += 8
                    continue
        
        i += 1
    
    return books

def main():
    print("📚 Starting Oricon OCR Scraper (Tesseract)...\n")
    print(f"⏰ Time: {datetime.now().isoformat()}\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "oricon.co.jp",
        "genres": {}
    }
    
    for genre, url in ORICON_URLS.items():
        books = scrape_oricon_page(url, genre)
        data["genres"][genre] = books
        time.sleep(3)
    
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
