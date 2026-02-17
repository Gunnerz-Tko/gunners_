import json
import google.generativeai as genai
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

TRANSLATIONS_CACHE = {
    "総合": "Overall",
    "文芸書": "Literature & Fiction",
    "ノンフィクション・ライトエッセイ": "Non-Fiction & Light Essays",
    "エンターテイメント": "Entertainment",
    "ビジネス書": "Business Books",
    "趣味実用書": "Hobby & Practical",
    "生活実用書": "Lifestyle & Practical",
    "児童書": "Children's Books",
    "ノベルス": "Novels",
    "新書": "New Books",
    "文庫": "Pocket Books",
    "コミックス": "Comics"
}

def translate_with_gemini(text):
    """Translate Japanese text to English using Gemini"""
    try:
        # Check cache first
        if text in TRANSLATIONS_CACHE:
            return TRANSLATIONS_CACHE[text]
        
        prompt = f"Translate this Japanese text to English. Return ONLY the translation, nothing else:\n{text}"
        response = model.generate_content(prompt)
        translation = response.text.strip()
        
        # Cache the translation
        TRANSLATIONS_CACHE[text] = translation
        logger.info(f"✓ Translated: {text} → {translation}")
        
        return translation
    except Exception as e:
        logger.error(f"Error translating '{text}': {e}")
        return text

def translate_data():
    """Translate all genre names in data.js"""
    try:
        # Read data.js
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON from data.js (remove 'const oricon_data = ' and ';')
        json_str = content.replace('const oricon_data = ', '').rstrip(';')
        data = json.loads(json_str)
        
        # Translate genre names
        translated_data = {
            "updated": data.get("updated"),
            "genres": {}
        }
        
        for genre, books in data.get("genres", {}).items():
            translated_genre = translate_with_gemini(genre)
            translated_data["genres"][translated_genre] = books
        
        # Write back to data.js
        with open('data.js', 'w', encoding='utf-8') as f:
            f.write(f"const oricon_data = {json.dumps(translated_data, ensure_ascii=False, indent=2)};")
        
        logger.info("✓ Translations complete!")
        return True
        
    except Exception as e:
        logger.error(f"Error translating data: {e}")
        return False

if __name__ == "__main__":
    translate_data()
