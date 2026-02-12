import requests
import json
from datetime import datetime

def get_publisher_from_openlibrary(title, author=""):
    """Get correct publisher info from OpenLibrary API"""
    try:
        query = title
        if author:
            query += f" {author}"
        
        url = f"https://openlibrary.org/search.json?title={query}&limit=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('docs') and len(data['docs']) > 0:
                book = data['docs'][0]
                # Get publisher
                publishers = book.get('publisher', [])
                if publishers:
                    return publishers[0]
                # Get author if not provided
                if not author:
                    authors = book.get('author_name', [])
                    if authors:
                        author = authors[0]
        
        return ""
    except Exception as e:
        print(f"Error fetching from OpenLibrary: {e}")
        return ""

def scrape_nippan_books():
    """Scrape book rankings from Nippan"""
    
    try:
        # Fetch from Nippan API or parse website
        # For now, we'll use a placeholder - you may need to update the source
        
        data = {
            "updated": datetime.now().isoformat() + "Z",
            "genres": {
                "General": [],
                "Paperback": [],
                "Comics": []
            }
        }
        
        # Example: If you have a Nippan API endpoint, use it
        # Otherwise, you need to scrape from the website or provide manual data
        
        # For testing, let's create sample data and enrich it with OpenLibrary
        sample_books = {
            "General": [
                {"title": "アイドル経営者", "author": "", "rank": 1, "last_week": 2},
                {"title": "Another Book", "author": "", "rank": 2, "last_week": 1},
            ],
            "Comics": [
                {"title": "Dragon Quest", "author": "", "rank": 1, "last_week": 3},
            ]
        }
        
        # Enrich with OpenLibrary data
        for genre, books in sample_books.items():
            for book in books:
                # Get publisher from OpenLibrary
                publisher = get_publisher_from_openlibrary(book['title'], book.get('author', ''))
                
                book_entry = {
                    "rank": book['rank'],
                    "last_week": book['last_week'],
                    "title": book['title'],
                    "author": book.get('author', '-'),
                    "publisher": publisher if publisher else "-",
                    "image": ""
                }
                
                data["genres"][genre].append(book_entry)
                print(f"✅ {book['title']} -> Publisher: {publisher}")
        
        # Save to file
        with open('nippan_books.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("\n✅ Data updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    scrape_nippan_books()
