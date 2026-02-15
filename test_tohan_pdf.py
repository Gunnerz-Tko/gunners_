#!/usr/bin/env python3
import requests
import pdfplumber
import json

pdf_url = "https://www.tohan.jp/wp/wp-content/uploads/2026/02/202601.pdf"

print("📥 Downloading Tohan PDF...")
response = requests.get(pdf_url, timeout=30)

with open('/tmp/tohan.pdf', 'wb') as f:
    f.write(response.content)

print("✅ PDF downloaded!")
print("\n📖 Analyzing PDF structure...\n")

with pdfplumber.open('/tmp/tohan.pdf') as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Analyze first 5 pages
    for page_idx in range(min(5, len(pdf.pages))):
        page = pdf.pages[page_idx]
        text = page.extract_text()
        
        print(f"\n{'='*60}")
        print(f"PAGE {page_idx + 1}")
        print(f"{'='*60}")
        print(text[:800])
        print("...\n")
