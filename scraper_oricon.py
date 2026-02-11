import requests
import json
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
from datetime import datetime

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

def translate_japanese_to_english(text):
    """Translate Japanese text to English using Gemini"""
    try:
        response = model.generate_content(f"Translate this Japanese text to English. Only provide the translation, nothing else:\n\n{text}")
        return response.text.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def scrape_oricon_rankings(genre_url):
    """Scrape Oricon rankings for a specific genre"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(genre_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rankings = []
        
        # Adjust selectors based on Oricon's actual HTML structure
        items = soup.select('div.ranking-item')[:10]  # Get top 10
        
        for idx, item in enumerate(items, 1):
            try:
                title_elem = item.select_one('h3.title, .book-title')
                author_elem = item.select_one('.author, .writer')
                sales_elem = item.select_one('.sales, .point')
                image_elem = item.select_one('img.book-image, img')
                
                if title_elem:
                    title = title_elem.text.strip()
                    author = author_elem.text.strip() if author_elem else "Unknown"
                    sales = sales_elem.text.strip() if sales_elem else "0"
                    image = image_elem.get('src', '') if image_elem else ""
                    
                    # Translate to English
                    title_en = translate_japanese_to_english(title)
                    author_en = translate_japanese_to_english(author)
                    
                    rankings.append({
                        "rank": str(idx),
                        "title": title_en,
                        "title_jp": title,
                        "author": author_en,
                        "author_jp": author,
                        "sales": int(''.join(filter(str.isdigit, sales)) or '0'),
                        "image": image
                    })
            except Exception as e:
                print(f"Error parsing item {idx}: {e}")
                continue
        
        return rankings
    except Exception as e:
        print(f"Scraping error for {genre_url}: {e}")
        return []

def main():
    """Main scraper function"""
    
    # Oricon genres and their URLs
    genres = {
        "General": "https://www.oricon.co.jp/rank/book/",
        "Literature": "https://www.oricon.co.jp/rank/book/d/1/",
        "Light Novels": "https://www.oricon.co.jp/rank/book/d/2/",
        "Comics": "https://www.oricon.co.jp/rank/book/d/3/"
    }
    
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "week": f"Week {datetime.now().isocalendar()[1]} {datetime.now().year}",
        "genres": {},
        "total_genres": len(genres)
    }
    
    print("Starting Oricon scraper with Gemini translation...")
    
    for genre_name, genre_url in genres.items():
        print(f"Scraping {genre_name}...")
        rankings = scrape_oricon_rankings(genre_url)
        data["genres"][genre_name] = rankings
        print(f"  Found {len(rankings)} books")
    
    # Save to JSON
    with open('oricon_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("Scraping complete! Data saved to oricon_books.json")

if __name__ == "__main__":
    main()
