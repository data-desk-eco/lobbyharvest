#!/usr/bin/env python3
"""Debug the HTML structure of lobbying sites"""
import requests
from bs4 import BeautifulSoup
import re

def debug_lobbyfacts():
    print("="*50)
    print("DEBUGGING LOBBYFACTS")
    print("="*50)

    url = "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})

    soup = BeautifulSoup(response.text, 'lxml')

    # Find all headers that might indicate client sections
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
    for h in headers:
        text = h.get_text(strip=True)
        if 'client' in text.lower():
            print(f"\nFound header: {h.name} - {text}")

            # Check next siblings for content
            next_elem = h.find_next_sibling()
            count = 0
            while next_elem and count < 3:
                print(f"  Next element: {next_elem.name if hasattr(next_elem, 'name') else 'text'}")
                if hasattr(next_elem, 'name'):
                    # If it's a list
                    if next_elem.name in ['ul', 'ol']:
                        items = next_elem.find_all('li')
                        print(f"    Found list with {len(items)} items")
                        for i, item in enumerate(items[:3]):
                            print(f"      Item {i}: {item.get_text(strip=True)[:50]}")

                    # If it's a table
                    elif next_elem.name == 'table':
                        rows = next_elem.find_all('tr')
                        print(f"    Found table with {len(rows)} rows")

                    # If it's a div
                    elif next_elem.name == 'div':
                        text = next_elem.get_text(strip=True)
                        print(f"    Div content: {text[:100]}")

                next_elem = next_elem.find_next_sibling() if hasattr(next_elem, 'find_next_sibling') else None
                count += 1

    # Alternative: Look for any lists or tables that might contain clients
    print("\n" + "="*30)
    print("ALL LISTS ON PAGE:")
    lists = soup.find_all(['ul', 'ol'])
    for i, lst in enumerate(lists):
        items = lst.find_all('li')
        if items and len(items) > 2:  # Only show lists with multiple items
            print(f"\nList {i}: {len(items)} items")
            for j, item in enumerate(items[:2]):
                print(f"  - {item.get_text(strip=True)[:60]}")

if __name__ == "__main__":
    debug_lobbyfacts()