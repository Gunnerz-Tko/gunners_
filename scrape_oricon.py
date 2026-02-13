import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import difflib
import time

ORICON_URLS = {
    "Comics": "https://www.oricon.co.jp/rank/obc/w/2026-02-16/",
    "Paperback": "https://www.oricon.co.jp/rank/obb/w/2026-02-16/",
    "Light Novel": "https://www.oricon.co.jp/rank/obl/w/2026-02-16/",
    "Light Literature": "https://www.oricon.co.jp/rank/obll/w/2026-02-16/",
    "Literary": "https://www.oricon.co.jp/rank/oba/w/2026-02-16/"
}

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
    
    title_normalized = ' '.join(title.split())
    
    for genre, books in corrections_by_genre.items():
        for book in books:
            book_title = ' '.join(book['title'].split())
            
            if title_normalized.lower() == book_title.lower():
                return book
            
            similarity = difflib.SequenceMatcher(None, title_normalized.lower(), book_title.lower()).ratio()
            if similarity > 0.85:
                return book
    
    return None

def scrape_oricon(url, genre):
    """Scrape Oricon ranking page"""
    
    print(f"\n🔄 Scraping {genre} from Oricon...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch {genre}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        books = []
        rank = 1
        
        # Chercher la table de classement Oricon
        # Oricon utilise une structure spécifique
        
        # Méthode 1: Chercher les rows de classement
        ranking_items = soup.find_all('div', class_='ranking-item')
        
        if not ranking_items:
            # Méthode 2: Chercher les lignes du tableau
            ranking_items = soup.find_all('tr', class_='js-ranking-item')
        
        if not ranking_items:
            # Méthode 3: Structure générale Oricon
            ranking_items = soup.select('.ranking-item, .rankingItem, [data-rank]')
        
        print(f"   Found {len(ranking_items)} items")
        
        for item in ranking_items[:10]:  # Top 10
            try:
                # Extraire les données
                
                # Titre
                title_elem = item.find('a', class_='title')
                if not title_elem:
                    title_elem = item.find('p', class_='title')
                if not title_elem:
                    title_elem = item.find('span', class_='title')
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Auteur
                author_elem = item.find('span', class_='artist')
                if not author_elem:
                    author_elem = item.find('a', class_='artist')
                if not author_elem:
                    author_elem = item.find('p', class_='artist')
                
                author = author_elem.get_text(strip=True) if author_elem else "-"
                
                # Éditeur
                publisher_elem = item.find('span', class_='publisher')
                if not publisher_elem:
                    publisher_elem = item.find('p', class_='publisher')
                if not publisher_elem:
                    publisher_elem = item.find('td', class_='publisher')
                
                publisher = publisher_elem.get_text(strip=True) if publisher_elem else "-"
                
                # Ventes estimées
                sales_elem = item.find('span', class_='sales')
                if not sales_elem:
                    sales_elem = item.find('p', class_='sales')
                if not sales_elem:
                    sales_elem = item.find('td', class_='sales')
                
                sales = sales_elem.get_text(strip=True) if sales_elem else "-"
                
                # Rang (si pas déjà incrémenté)
                rank_elem = item.find('span', class_='rank')
                if rank_elem:
                    try:
                        rank = int(rank_elem.get_text(strip=True))
                    except:
                        pass
                
                print(f"   {rank}. {title}")
                
                books.append({
                    "rank": rank,
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "sales": sales
                })
                
                rank += 1
                
            except Exception as e:
                print(f"   ⚠️  Error parsing item: {e}")
                continue
        
        return books
        
    except Exception as e:
        print(f"❌ Error scraping {genre}: {e}")
        return []

def scrape_all_oricon():
    """Scrape all Oricon categories"""
    
    print("📚 Scraping Oricon Rankings...\n")
    
    # Load corrections
    corrections = load_corrections()
    print(f"📋 Loaded corrections: {len(corrections)} genres\n")
    
    # Data structure
    data = {
        "updated": datetime.now().isoformat() + "Z",
        "source": "oricon.co.jp",
        "genres": {
            "Comics": [],
            "Paperback": [],
            "Light Novel": [],
            "Light Literature": [],
            "Literary": []
        }
    }
    
    # Scrape each category
    for genre, url in ORICON_URLS.items():
        books = scrape_oricon(url, genre)
        
        # Apply corrections
        for book in books:
            correction = find_correction(book['title'], corrections)
            
            if correction:
                book['author'] = correction.get('author', book['author'])
                book['publisher'] = correction.get('publisher', book['publisher'])
                print(f"   ✅ Correction applied for: {book['title']}")
        
        data["genres"][genre] = books
        
        time.sleep(2)  # Be respectful
    
    # Save to file
    with open('oricon_books.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Scraping completed!")
    print(f"📚 Comics: {len(data['genres']['Comics'])} books")
    print(f"📚 Paperback: {len(data['genres']['Paperback'])} books")
    print(f"📚 Light Novel: {len(data['genres']['Light Novel'])} books")
    print(f"📚 Light Literature: {len(data['genres']['Light Literature'])} books")
    print(f"📚 Literary: {len(data['genres']['Literary'])} books")
    print(f"💾 Saved to: oricon_books.json")

if __name__ == "__main__":
    scrape_all_oricon()
