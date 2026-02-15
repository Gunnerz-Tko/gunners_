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
    options.add_argument('--start-maximized')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    return driver

def scrape_oricon_page(url, genre):
    """Scrape Oricon page with OCR"""
    print(f"\n🔄 Scraping {genre}...")
    
    driver = None
    books = []
    
    try:
        driver = setup_driver()
        driver.get(url)
        time.sleep(3)
        
        # Scroll to load all content
        for _ in range(5):
            driver.execute_script("window.scrollBy(0, window.innerHeight)")
            time.sleep(1)
        
        # Take full page screenshot
        screenshot_path = f'/tmp/oricon_{genre}.png'
        driver.save_screenshot(screenshot_path)
        
        # OCR extraction
        image = Image.open(screenshot_path)
        ocr_text = pytesseract.image_to_string(image, lang='jpn+eng')
        
        # Parse OCR text pour extraire les livres
        books = parse_oricon_ocr(ocr_text)
        
        print(f"   ✅ {genre}: {len(books)} books extracted via OCR")
        
        # Fallback: Extract from HTML structure if OCR fails
        if len(books) < 5:
            print(f"   ⚠️  OCR result too small, trying HTML extraction...")
            books = extract_from_html(driver)
            print(f"   ✅ {genre}: {len(books)} books extracted from HTML")
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        
        return books[:10]
    
    except Exception as e:
        logger.error(f"Error scraping {genre}: {e}")
        return []
    
    finally:
        if driver:
            driver.quit()

def parse_oricon_ocr(ocr_text):
    """Parse OCR text to extract book rankings"""
    books = []
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    
    i = 0
    rank = 1
    
    while i < len(lines) and rank <= 10:
        line = lines[i]
        
        # Look for rank number (1-10)
        if re.match(r'^[0-9]+$', line):
            rank_num = int(line)
            
            if 1 <= rank_num <= 10:
                # Extract next lines
                title = lines[i + 1] if i + 1 < len(lines) else ""
                author = lines[i + 2] if i + 2 < len(lines) else ""
                publisher = lines[i + 3] if i + 3 < len(lines) else ""
                # Skip published date (i+4)
                sales = lines[i + 5] if i + 5 < len(lines) else ""
                
                if title and len(title) > 2:  # Valid title
                    # Clean up sales number
                    sales_clean = re.sub(r'[^0-9,]', '', sales)
                    
                    books.append({
                        "rank": rank_num,
                        "title": title,
                        "author": author if author else "-",
                        "publisher": publisher if publisher else "-",
                        "sales": sales_clean if sales_clean else "-"
                    })
                    
                    i += 6
                    continue
        
        i += 1
    
    return books

def extract_from_html(driver):
    """Fallback: Extract data from HTML structure"""
    books = []
    
    try:
        # Find all ranking items
        items = driver.find_elements(By.CLASS_NAME, "rank")
        
        for idx, item in enumerate(items[:10]):
            try:
                rank = idx + 1
                
                # Title (blue, clickable link)
                title_elem = item.find_element(By.TAG_NAME, "a")
                title = title_elem.text.strip()
                
                # Author (bold)
                author_elem = item.find_element(By.CSS_SELECTOR, "strong")
                author = author_elem.text.strip()
                
                # Publisher
                all_text = item.text.split('\n')
                publisher = ""
                sales = ""
                
                # Parse text structure
                for j, text in enumerate(all_text):
                    if '出版社' in text or j > 2:
                        publisher = all_text[j + 1] if j + 1 < len(all_text) else ""
                    if '推定売上' in text or '売上' in text:
                        sales = re.sub(r'[^0-9,]', '', all_text[j + 1] if j + 1 < len(all_text) else "")
                
                if title:
                    books.append({
                        "rank": rank,
                        "title": title,
                        "author": author if author else "-",
                        "publisher": publisher if publisher else "-",
                        "sales": sales if sales else "-"
                    })
            
            except Exception as e:
                logger.debug(f"Error parsing item {idx}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error extracting from HTML: {e}")
    
    return books

def main():
    print("📚 Starting Oricon OCR Scraper...\n")
    print(f"⏰ Time: {datetime.now().isoformat()}\n")
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "oricon.co.jp",
        "genres": {}
    }
    
    for genre, url in ORICON_URLS.items():
        books = scrape_oricon_page(url, genre)
        data["genres"][genre] = books
        time.sleep(3)  # Be polite to Oricon
    
    # Generate data.js
    try:
        js_content = f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"\n✅ Successfully saved data.js")
        print(f"📊 Total genres: {len(data['genres'])}")
        
        for genre, books in data['genres'].items():
            print(f"   - {genre}: {len(books)} books")
    
    except Exception as e:
        logger.error(f"Error saving data.js: {e}")

if __name__ == "__main__":
    main()
