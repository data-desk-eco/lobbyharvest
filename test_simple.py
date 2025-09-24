#!/usr/bin/env python3
"""Simple test to check if scrapers work without browser"""
import requests
from bs4 import BeautifulSoup

def test_lobbyfacts():
    url = "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        title = soup.find('title')
        print(f"Title: {title.text if title else 'No title'}")

        # Check if there's JavaScript-rendered content
        if 'Loading' in response.text or 'JavaScript' in response.text:
            print("⚠️  Page seems to require JavaScript")
        else:
            print("✓ Static HTML content detected")

        # Look for client mentions
        client_mentions = soup.find_all(string=lambda text: 'client' in text.lower() if text else False)
        print(f"Found {len(client_mentions)} mentions of 'client'")

def test_uk_lobbying():
    url = "https://lobbying-register.uk/"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"\nUK Lobbying - Status: {response.status_code}")

    if 'api' in response.text.lower() or 'json' in response.text.lower():
        print("✓ Might have API endpoints available")

def test_opensecrets():
    url = "https://www.opensecrets.org/federal-lobbying/firms/summary?id=D000066805"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"\nOpenSecrets - Status: {response.status_code}")

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")

if __name__ == "__main__":
    test_lobbyfacts()
    test_uk_lobbying()
    test_opensecrets()