"""
Lightweight Lobbyfacts scraper using requests and BeautifulSoup
No browser dependencies required
"""
import re
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_lobbyfacts(firm_name: str, url: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Scrape client information from Lobbyfacts.eu

    Args:
        firm_name: Name of the lobbying firm
        url: Optional direct URL to the firm's Lobbyfacts page

    Returns:
        List of client dictionaries
    """
    clients = []

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # For now, require direct URL since search is complex
    if not url:
        logger.warning(f"Please provide direct URL to {firm_name}'s Lobbyfacts page")
        return clients

    try:
        # Fetch the datacard page
        response = session.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch datacard: {response.status_code}")
            return clients

        soup = BeautifulSoup(response.text, 'lxml')

        # Extract RID from URL if present
        rid_match = re.search(r'rid=([^&]+)', url)
        firm_id = rid_match.group(1) if rid_match else None

        # Find all lists on the page
        all_lists = soup.find_all(['ul', 'ol'])

        # Filter for lists that look like client lists
        # They typically have more than 3 items and contain company/organization names
        for lst in all_lists:
            items = lst.find_all('li')

            # Skip navigation and small lists
            if len(items) < 3:
                continue

            # Check if this looks like a client list by examining first few items
            looks_like_clients = False
            for item in items[:3]:
                text = item.get_text(strip=True)
                # Client names are typically longer, not navigation items
                if len(text) > 10 and not any(nav in text.lower() for nav in ['search', 'about', 'disclaimer', 'how to', 'info', 'people', 'employment']):
                    looks_like_clients = True
                    break

            if looks_like_clients:
                # Extract all items as clients
                for item in items:
                    client_name = item.get_text(strip=True)

                    # Filter out obvious non-clients
                    if (client_name and
                        len(client_name) > 5 and
                        not any(skip in client_name.lower() for skip in ['search', 'about', 'disclaimer', 'cabinet', 'member'])):

                        clients.append({
                            'firm_name': firm_name,
                            'firm_id': firm_id,
                            'client_name': client_name,
                            'client_id': None,
                            'start_date': None,
                            'end_date': None
                        })

        # Remove duplicates
        unique_clients = []
        seen = set()
        for client in clients:
            if client['client_name'] not in seen:
                seen.add(client['client_name'])
                unique_clients.append(client)

        logger.info(f"Found {len(unique_clients)} unique clients for {firm_name}")
        return unique_clients

    except Exception as e:
        logger.error(f"Error scraping {firm_name}: {str(e)}")
        return []