#!/usr/bin/env python3
import json
import logging
import os
import time
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_gemini():
    """Setup Gemini API"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        return None
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def translate_text(model, text):
    """Translate text using Gemini"""
    if not text or text == '-':
        return text
    
    try:
        prompt = f"Translate this Japanese text to English. Return ONLY the translation, nothing else:\n\n{text}"
        
        response = model.generate_content(prompt)
        
        if response.text:
            return response.text.strip()
        else:
            return text
    
    except Exception as e:
        logger.warning(f"Translation error for '{text}': {e}")
        return text

def translate_books_data(data, model):
    """Translate book titles, authors, and publishers to English"""
    print("\n🌐 Translating data to English with Gemini...\n")
    
    for genre, books in data['genres'].items():
        print(f"📖 Translating {genre}... ({len(books)} books)")
        
        for idx, book in enumerate(books):
            # Translate title
            if book['title'] and book['title'] != '-':
                book['title_en'] = translate_text(model, book['title'])
                print(f"   [{idx+1}] {book['title']} → {book['title_en']}")
            else:
                book['title_en'] = book['title']
            
            # Translate author
            if book['author'] and book['author'] != '-':
                book['author_en'] = translate_text(model, book['author'])
            else:
                book['author_en'] = book['author']
            
            # Translate publisher
            if book['publisher'] and book['publisher'] != '-':
                book['publisher_en'] = translate_text(model, book['publisher'])
            else:
                book['publisher_en'] = book['publisher']
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"   ✅ {len(books)} books translated\n")
    
    return data

def main():
    print("📚 Starting Tohan Data Translation with Gemini...\n")
    
    # Setup Gemini
    model = setup_gemini()
    if not model:
        logger.error("Failed to setup Gemini API")
        return
    
    # Read data.js
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract JSON from "const oricon_data = {...};"
            json_str = content.replace('const oricon_data = ', '').rstrip(';')
            data = json.loads(json_str)
        print("✅ data.js loaded")
    except Exception as e:
        logger.error(f"Error reading data.js: {e}")
        return
    
    # Translate data
    data = translate_books_data(data, model)
    
    # Save translated data.js
    try:
        js_content = f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"\n✅ Successfully saved translated data.js")
        print(f"📊 Total genres: {len(data['genres'])}")
        
        total_books = 0
        for genre, books in data['genres'].items():
            print(f"   - {genre}: {len(books)} books")
            total_books += len(books)
        
        print(f"\n📈 Total books translated: {total_books}")
    
    except Exception as e:
        logger.error(f"Error saving data.js: {e}")

if __name__ == "__main__":
    main()
