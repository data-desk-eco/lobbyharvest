"""
Lobbyfacts.eu scraper - extracts client data from EU Transparency Register
"""
import logging
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common navigation/UI terms to filter out
FILTER_TERMS = [
    'search', 'about', 'disclaimer', 'cabinet', 'member', 'how to',
    'latest stories', 'info', 'people', 'employment', 'transparency',
    'register', 'login', 'contact', 'privacy', 'terms', 'cookies',
    'home', 'menu', 'navigation', 'footer', 'header',
    'categories', 'affiliation', 'financial data', 'eu structures',
    'meetings', 'platforms'
]

def scrape_lobbyfacts(firm_name: str, url: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Scrape client information from Lobbyfacts.eu

    Args:
        firm_name: Name of the lobbying firm
        url: Direct URL to the firm's Lobbyfacts page (required for now)

    Returns:
        List of client dictionaries with firm and client information
    """
    if not url:
        logger.error(f"Direct URL required for {firm_name}. Search functionality coming soon.")
        return []

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')

    # Extract firm ID from URL
    rid_match = re.search(r'rid=([^&]+)', url)
    firm_id = rid_match.group(1) if rid_match else None

    clients = []
    seen_clients = set()

    # Strategy 1: Look for sections with "Clients" in the heading
    client_headers = soup.find_all(['h2', 'h3', 'h4'],
                                  string=re.compile(r'Clients.*financial year', re.I))

    for header in client_headers:
        # Get all siblings until next header
        current = header.find_next_sibling()
        while current and current.name not in ['h2', 'h3', 'h4']:
            if current.name in ['ul', 'ol']:
                for item in current.find_all('li'):
                    client_name = clean_client_name(item.get_text(strip=True))
                    if is_valid_client(client_name) and client_name not in seen_clients:
                        seen_clients.add(client_name)
                        clients.append(create_client_record(firm_name, firm_id, client_name))
            current = current.find_next_sibling() if current else None

    # Strategy 2: Find lists with many items (likely client lists)
    all_lists = soup.find_all(['ul', 'ol'])
    for lst in all_lists:
        items = lst.find_all('li')

        # Client lists typically have many entries
        if len(items) >= 5:
            # Sample first few items to check if they look like clients
            sample_items = items[:min(5, len(items))]
            valid_samples = sum(1 for item in sample_items
                              if is_valid_client(item.get_text(strip=True)))

            # If most samples look like clients, process the whole list
            if valid_samples >= 3:
                for item in items:
                    client_name = clean_client_name(item.get_text(strip=True))
                    if is_valid_client(client_name) and client_name not in seen_clients:
                        seen_clients.add(client_name)
                        clients.append(create_client_record(firm_name, firm_id, client_name))

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def clean_client_name(text: str) -> str:
    """Clean and normalize client name"""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove common suffixes in parentheses
    text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
    return text.strip()

def is_valid_client(name: str) -> bool:
    """Check if a string looks like a valid client name"""
    if not name or len(name) < 3:
        return False

    # Filter out navigation and UI elements
    name_lower = name.lower()
    if any(term in name_lower for term in FILTER_TERMS):
        return False

    # Client names typically:
    # - Start with uppercase or contain multiple words
    # - Contain letters (not just numbers/symbols)
    # - Are longer than typical UI elements

    has_letters = any(c.isalpha() for c in name)
    reasonable_length = 5 < len(name) < 200

    return has_letters and reasonable_length

def create_client_record(firm_name: str, firm_id: str, client_name: str) -> Dict[str, str]:
    """Create a standardized client record"""
    return {
        'firm_name': firm_name,
        'firm_id': firm_id,
        'client_name': client_name,
        'client_id': None,  # Would need additional lookup
        'start_date': None,  # Not available in basic listing
        'end_date': None
    }