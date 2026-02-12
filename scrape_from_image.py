import os
import json
import cv2
import pytesseract
import easyocr

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

def extract_text_with_tesseract(image_path):
    """Use Tesseract OCR to extract text from an image."""
    try:
        img = cv2.imread(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"Tesseract OCR error: {e}")
        return None

def extract_text_with_easyocr(image_path):
    """Use EasyOCR to extract text from an image."""
    try:
        result = reader.readtext(image_path)
        text = " ".join([item[1] for item in result])
        return text
    except Exception as e:
        print(f"EasyOCR error: {e}")
        return None

def extract_book_ranking_data(image_path):
    """Extract book ranking data from the image."""
    text = extract_text_with_tesseract(image_path)
    if text is None:
        text = extract_text_with_easyocr(image_path)
        
    if text:
        # Parse the text to extract book rankings (dummy parsing)
        # This should be replaced with actual logic to extract ranking data
        return [{"title": line, "rank": idx + 1} for idx, line in enumerate(text.split("\n")) if line]
    return []

def apply_corrections(book_data, corrections):
    """Apply corrections from the corrections JSON."""
    for book in book_data:
        title = book['title']
        if title in corrections:
            book['title'] = corrections[title]
    return book_data

def save_to_json(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main(image_files):
    all_books = []
    
    # Load corrections
    with open('books_corrections.json', 'r', encoding='utf-8') as f:
        corrections = json.load(f)

    for image_file in image_files:
        book_data = extract_book_ranking_data(image_file)
        all_books.extend(book_data)

    all_books = apply_corrections(all_books, corrections)
    save_to_json('nippan_books.json', all_books)

if __name__ == "__main__":
    # Replace with actual image files to process
    image_files = ['path/to/your/image1.png', 'path/to/your/image2.png']
    main(image_files)
