import json
import google.generativeai as genai
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

TRANSLATIONS_CACHE = {}

def translate_with_gemini(text, field_type="text"):
    """Translate Japanese text to English using Gemini"""
    if not text or text == "-":
        return text
    
    try:
        # Check cache first
        cache_key = f"{field_type}:{text}"
        if cache_key in TRANSLATIONS_CACHE:
            return TRANSLATIONS_CACHE[cache_key]
        
        # Different prompts for different field types
        if field_type == "title":
            prompt = f"Translate this Japanese book title to English. Use romanization where needed (e.g., 変な地図 = Hen na Chizu). Return ONLY the translation:\n{text}"
        elif field_type == "author":
            prompt = f"Translate this Japanese author name to English. Keep the original name order. Return ONLY the translation:\n{text}"
        elif field_type == "publisher":
            prompt = f"Translate this Japanese publisher name to English. Return ONLY the translation:\n{text}"
        elif field_type == "genre":
            prompt = f"Translate this Japanese genre name to English. Return ONLY the translation:\n{text}"
        else:
            prompt = f"Translate this Japanese text to English. Return ONLY the translation:\n{text}"
        
        response = model.generate_content(prompt)
        translation = response.text.strip()
        
        # Cache the translation
        TRANSLATIONS_CACHE[cache_key] = translation
        logger.info(f"✓ [{field_type}] {text} → {translation}")
        
        # Rate limiting to avoid API errors
        time.sleep(0.5)
        
        return translation
    except Exception as e:
        logger.error(f"Error translating '{text}' ({field_type}): {e}")
        return text

def translate_data():
    """Translate all data in data.js"""
    try:
        # Read data.js
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON from data.js (remove 'const oricon_data = ' and ';')
        json_str = content.replace('const oricon_data = ', '').rstrip(';')
        data = json.loads(json_str)
        
        # Translate all genres and books
        translated_data = {
            "updated": data.get("updated"),
            "genres": {}
        }
        
        for genre, books in data.get("genres", {}).items():
            # Translate genre name
            translated_genre = translate_with_gemini(genre, "genre")
            
            # Translate each book's data
            translated_books = []
            for book in books:
                translated_book = {
                    "rank": book.get("rank"),
                    "title": translate_with_gemini(book.get("title"), "title"),
                    "author": translate_with_gemini(book.get("author"), "author"),
                    "publisher": translate_with_gemini(book.get("publisher"), "publisher"),
                    "price": book.get("price"),  # Keep price as-is
                    "isbn": book.get("isbn")      # Keep ISBN as-is
                }
                translated_books.append(translated_book)
                logger.info(f"  Translated book: {book.get('title')[:30]}...")
            
            translated_data["genres"][translated_genre] = translated_books
        
        # Write back to data.js
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(f"const oricon_data = {json.dumps(translated_data, ensure_ascii=False, indent=2)};")
        
        logger.info("✅ All translations complete!")
        return True
        
    except Exception as e:
        logger.error(f"Error translating data: {e}")
        return False

if __name__ == "__main__":
    translate_data()
