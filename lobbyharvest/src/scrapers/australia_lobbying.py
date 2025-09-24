"""
Australian Lobbying Register scraper - extracts client data from Australian registry
"""
import logging
import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape(firm_name: str) -> List[Dict[str, str]]:
    """
    Scrape client information from Australian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    base_url = "https://lobbyists.ag.gov.au"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        # First, get the main register page
        register_url = f"{base_url}/register"
        response = session.get(register_url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Look for search form or links to firms
        # The Australian register often uses tables
        tables = soup.find_all('table')

        for table in tables:
            # Look for firm in table rows
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    if firm_name.lower() in cell_text.lower():
                        # Found a matching firm, look for link to details
                        link = row.find('a')
                        if link and link.get('href'):
                            detail_url = link['href']
                            if not detail_url.startswith('http'):
                                detail_url = base_url + detail_url

                            # Fetch the detail page
                            detail_response = session.get(detail_url, timeout=10)
                            if detail_response.status_code == 200:
                                detail_soup = BeautifulSoup(detail_response.text, 'lxml')
                                clients.extend(parse_detail_page(detail_soup, firm_name))
                        break

        # If no results from tables, try searching
        if not clients:
            # Look for search functionality
            search_forms = soup.find_all('form')
            for form in search_forms:
                action = form.get('action', '')
                if 'search' in action.lower():
                    search_url = action if action.startswith('http') else base_url + action

                    # Submit search
                    search_data = {
                        'search': firm_name,
                        'q': firm_name,
                        'query': firm_name,
                        'name': firm_name,
                        'firm': firm_name,
                        'lobbyist': firm_name
                    }

                    # Try POST first
                    try:
                        search_response = session.post(search_url, data=search_data, timeout=10)
                        if search_response.status_code == 200:
                            search_soup = BeautifulSoup(search_response.text, 'lxml')
                            clients.extend(parse_search_results(search_soup, firm_name))
                    except Exception:
                        # Try GET
                        try:
                            search_response = session.get(search_url, params=search_data, timeout=10)
                            if search_response.status_code == 200:
                                search_soup = BeautifulSoup(search_response.text, 'lxml')
                                clients.extend(parse_search_results(search_soup, firm_name))
                        except Exception:
                            pass

                    if clients:
                        break

    except requests.RequestException as e:
        logger.error(f"Failed to fetch Australian lobbying data: {e}")

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def parse_detail_page(soup: BeautifulSoup, firm_name: str) -> List[Dict[str, str]]:
    """Parse a firm's detail page for client information"""
    clients = []

    # Extract firm ABN if present
    firm_abn = None
    abn_pattern = re.compile(r'\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b')
    abn_match = abn_pattern.search(soup.get_text())
    if abn_match:
        firm_abn = abn_match.group(0).replace(' ', '')

    # Look for client sections
    # Common patterns: "Clients", "Client Details", "Registered Clients"
    client_headers = soup.find_all(['h2', 'h3', 'h4', 'strong'],
                                  string=re.compile(r'client', re.I))

    for header in client_headers:
        # Check next siblings for client information
        current = header.find_next_sibling()
        while current and current.name not in ['h2', 'h3', 'h4']:
            if current.name == 'table':
                # Parse table of clients
                rows = current.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        client_name = cells[0].get_text(strip=True)
                        if client_name and len(client_name) > 3:
                            clients.append({
                                'firm_name': firm_name,
                                'firm_abn': firm_abn,
                                'client_name': client_name,
                                'client_abn': cells[1].get_text(strip=True) if len(cells) > 1 else None,
                                'start_date': cells[2].get_text(strip=True) if len(cells) > 2 else None,
                                'end_date': cells[3].get_text(strip=True) if len(cells) > 3 else None
                            })

            elif current.name in ['ul', 'ol']:
                # Parse list of clients
                items = current.find_all('li')
                for item in items:
                    client_name = item.get_text(strip=True)
                    # Extract ABN if present in the text
                    client_abn = None
                    abn_match = abn_pattern.search(client_name)
                    if abn_match:
                        client_abn = abn_match.group(0).replace(' ', '')
                        # Remove ABN from client name
                        client_name = abn_pattern.sub('', client_name).strip()

                    if client_name and len(client_name) > 3:
                        clients.append({
                            'firm_name': firm_name,
                            'firm_abn': firm_abn,
                            'client_name': client_name,
                            'client_abn': client_abn,
                            'start_date': None,
                            'end_date': None
                        })

            elif current.name == 'div':
                # Check for client information in divs
                text = current.get_text(strip=True)
                if text and len(text) > 3 and 'client' not in text.lower():
                    clients.append({
                        'firm_name': firm_name,
                        'firm_abn': firm_abn,
                        'client_name': text,
                        'client_abn': None,
                        'start_date': None,
                        'end_date': None
                    })

            current = current.find_next_sibling() if current else None

    return clients

def parse_search_results(soup: BeautifulSoup, firm_name: str) -> List[Dict[str, str]]:
    """Parse search results page"""
    clients = []

    # Look for result tables
    tables = soup.find_all('table')
    for table in tables:
        # Check if this table contains client information
        headers = table.find_all('th')
        has_client_column = any('client' in h.get_text(strip=True).lower() for h in headers)

        if has_client_column:
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all(['td', 'th'])
                # Find the client column
                for i, header in enumerate(headers):
                    if 'client' in header.get_text(strip=True).lower():
                        if i < len(cells):
                            client_name = cells[i].get_text(strip=True)
                            if client_name and len(client_name) > 3:
                                clients.append({
                                    'firm_name': firm_name,
                                    'firm_abn': None,
                                    'client_name': client_name,
                                    'client_abn': None,
                                    'start_date': None,
                                    'end_date': None
                                })
                        break

    # Also look for cards or result items
    if not clients:
        result_items = soup.find_all('div', class_=re.compile(r'result|item|card', re.I))
        for item in result_items:
            # Look for client information within the item
            client_elem = item.find(string=re.compile(r'client', re.I))
            if client_elem:
                # Get the next text element
                parent = client_elem.parent
                if parent:
                    next_elem = parent.find_next()
                    if next_elem:
                        client_name = next_elem.get_text(strip=True)
                        if client_name and len(client_name) > 3:
                            clients.append({
                                'firm_name': firm_name,
                                'firm_abn': None,
                                'client_name': client_name,
                                'client_abn': None,
                                'start_date': None,
                                'end_date': None
                            })

    return clients