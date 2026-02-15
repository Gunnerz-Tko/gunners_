#!/usr/bin/env python3
import json
import logging
from google.cloud import translate_v2
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def translate_text(text, target_language='en'):
    """Translate text using Google Cloud Translation API"""
    try:
        # Initialize translation client
        translate_client = translate_v2.Client()
        
        result = translate_client.translate_text(
            text,
            target_language=target_language
        )
        
        return result['translatedText']
    except Exception as e:
        logger.warning(f"Translation error: {e}")
        return text  # Return original if translation fails

def translate_books_data(data):
    """Translate book titles and authors to English"""
    print("\n🌐 Translating data to English...\n")
    
    for genre, books in data['genres'].items():
        print(f"📖 Translating {genre}...")
        
        for book in books:
            # Translate title
            if book['title'] and book['title'] != '-':
                book['title_en'] = translate_text(book['title'])
            else:
                book['title_en'] = book['title']
            
            # Translate author
            if book['author'] and book['author'] != '-':
                book['author_en'] = translate_text(book['author'])
            else:
                book['author_en'] = book['author']
            
            # Translate publisher
            if book['publisher'] and book['publisher'] != '-':
                book['publisher_en'] = translate_text(book['publisher'])
            else:
                book['publisher_en'] = book['publisher']
        
        print(f"   ✅ {len(books)} books translated")
    
    return data

def main():
    print("📚 Starting Tohan Data Translation...\n")
    
    # Read data.js
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract JSON from "const oricon_data = {...};"
            json_str = content.replace('const oricon_data = ', '').rstrip(';')
            data = json.loads(json_str)
    except Exception as e:
        logger.error(f"Error reading data.js: {e}")
        return
    
    # Translate data
    data = translate_books_data(data)
    
    # Save translated data.js
    try:
        js_content = f"const oricon_data = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"\n✅ Successfully saved translated data.js")
    
    except Exception as e:
        logger.error(f"Error saving data.js: {e}")

if __name__ == "__main__":
    main()
