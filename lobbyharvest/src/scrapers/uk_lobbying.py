"""
UK Lobbying Register scraper - extracts client data from UK lobbying registry
"""
import logging
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape(firm_name: str) -> List[Dict[str, str]]:
    """
    Scrape client information from UK Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []

    # The UK site appears to be JavaScript-heavy but may have an API
    # Let's try searching directly
    base_url = "https://lobbying-register.uk"
    search_url = f"{base_url}/search"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/html, */*'
    })

    try:
        # Try different search approaches
        # Approach 1: Direct search endpoint
        search_params = {
            'q': firm_name,
            'query': firm_name,
            'search': firm_name,
            'name': firm_name
        }

        for param_name, param_value in search_params.items():
            try:
                response = session.get(search_url, params={param_name: param_value}, timeout=10)
                if response.status_code == 200:
                    # Check if it's JSON
                    if 'application/json' in response.headers.get('content-type', ''):
                        data = response.json()
                        clients.extend(parse_json_results(data, firm_name))
                    else:
                        # Parse HTML
                        soup = BeautifulSoup(response.text, 'lxml')
                        clients.extend(parse_html_results(soup, firm_name))

                    if clients:
                        break
            except Exception as e:
                logger.debug(f"Search with param {param_name} failed: {e}")

        # Approach 2: Try the main page and look for firm listings
        if not clients:
            response = session.get(base_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')

                # Look for links or references to the firm
                firm_links = soup.find_all('a', string=re.compile(firm_name, re.I))
                for link in firm_links[:1]:  # Follow first matching link
                    href = link.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = base_url + href

                        detail_response = session.get(href, timeout=10)
                        if detail_response.status_code == 200:
                            detail_soup = BeautifulSoup(detail_response.text, 'lxml')
                            clients.extend(parse_firm_detail_page(detail_soup, firm_name))

    except requests.RequestException as e:
        logger.error(f"Failed to fetch UK lobbying data: {e}")

    # If still no results, return placeholder data indicating the issue
    if not clients:
        logger.warning(f"No results found for {firm_name} - site may require JavaScript")
        # Return empty list rather than placeholder
        return []

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def parse_json_results(data: dict, firm_name: str) -> List[Dict[str, str]]:
    """Parse JSON response from UK lobbying API"""
    clients = []

    # Handle different possible JSON structures
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                client = extract_client_from_json(item, firm_name)
                if client:
                    clients.append(client)
    elif isinstance(data, dict):
        # Check for results array
        for key in ['results', 'data', 'items', 'clients']:
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    client = extract_client_from_json(item, firm_name)
                    if client:
                        clients.append(client)
                break

    return clients

def extract_client_from_json(item: dict, firm_name: str) -> Optional[Dict[str, str]]:
    """Extract client information from JSON item"""
    # Look for client name in various possible fields
    client_name = None
    for field in ['client', 'clientName', 'client_name', 'name', 'organisation']:
        if field in item:
            client_name = item[field]
            break

    if not client_name:
        return None

    return {
        'firm_name': firm_name,
        'firm_registration_number': item.get('registrationNumber', item.get('registration_number')),
        'client_name': client_name,
        'client_registration_number': item.get('clientRegistrationNumber', item.get('client_registration_number')),
        'start_date': item.get('startDate', item.get('start_date')),
        'end_date': item.get('endDate', item.get('end_date'))
    }

def parse_html_results(soup: BeautifulSoup, firm_name: str) -> List[Dict[str, str]]:
    """Parse HTML search results page"""
    clients = []

    # Look for result cards, tables, or lists
    # Try tables first
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Assume first cell is firm, second is client
                client_name = cells[1].get_text(strip=True)
                if client_name and len(client_name) > 3:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': client_name,
                        'client_registration_number': None,
                        'start_date': cells[2].get_text(strip=True) if len(cells) > 2 else None,
                        'end_date': cells[3].get_text(strip=True) if len(cells) > 3 else None
                    })

    # Try cards/divs
    if not clients:
        cards = soup.find_all('div', class_=re.compile(r'card|result|item|entry', re.I))
        for card in cards:
            client_elem = card.find(string=re.compile(r'client', re.I))
            if client_elem:
                client_name = client_elem.find_next().get_text(strip=True) if client_elem.find_next() else None
                if client_name:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': client_name,
                        'client_registration_number': None,
                        'start_date': None,
                        'end_date': None
                    })

    return clients

def parse_firm_detail_page(soup: BeautifulSoup, firm_name: str) -> List[Dict[str, str]]:
    """Parse a firm's detail page for client information"""
    clients = []

    # Look for sections containing client information
    client_sections = soup.find_all(['section', 'div'],
                                   string=re.compile(r'client', re.I))

    for section in client_sections:
        # Find lists or tables within the section
        lists = section.find_all(['ul', 'ol'])
        for lst in lists:
            items = lst.find_all('li')
            for item in items:
                client_name = item.get_text(strip=True)
                if client_name and len(client_name) > 3:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': client_name,
                        'client_registration_number': None,
                        'start_date': None,
                        'end_date': None
                    })

    return clients