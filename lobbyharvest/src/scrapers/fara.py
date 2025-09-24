"""
FARA (Foreign Agents Registration Act) scraper - extracts client data from US FARA database
"""
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape_fara(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Scrape client information from FARA database

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    base_url = "https://efile.fara.gov/ords/fara"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    # Skip SSL verification for FARA site due to certificate issues
    session.verify = False
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        # First, search for the firm
        search_url = f"{base_url}/f?p=1381:200"
        response = session.get(search_url, timeout=10)
        response.raise_for_status()

        # Try to find a session ID or form token
        # FARA uses Oracle APEX which requires session management
        # Look for the APEX session in the page
        apex_match = re.search(r'p_instance["\']?\s*[:=]\s*["\']?(\d+)', response.text)
        if apex_match:
            instance_id = apex_match.group(1)
        else:
            # Try to extract from URL redirects or page content
            instance_match = re.search(r':(\d+):', response.url)
            if instance_match:
                instance_id = instance_match.group(1)
            else:
                logger.error("Could not find APEX instance ID")
                return []

        # Search for the firm using APEX AJAX
        search_params = {
            'p_flow_id': '1381',
            'p_flow_step_id': '200',
            'p_instance': instance_id,
            'p_debug': '',
            'p_request': 'SEARCH',
            'p_widget_name': 'apex.go',
            'p_widget_action': 'reset',
            'x01': firm_name,  # Search term
            'x02': 'P200_SEARCH'  # Field name
        }

        # Try POST request for search
        ajax_url = f"{base_url}/wwv_flow.ajax"
        search_response = session.post(ajax_url, data=search_params, timeout=10)

        # If AJAX doesn't work, try direct page navigation with search
        if search_response.status_code != 200:
            # Alternative: Try navigating with search in URL
            alt_search_url = f"{base_url}/f?p=1381:200:{instance_id}::NO:200:P200_SEARCH:{firm_name}"
            search_response = session.get(alt_search_url, timeout=10)

        if search_response.status_code == 200:
            search_soup = BeautifulSoup(search_response.text, 'lxml')

            # Look for registration results table
            results_table = search_soup.find('table', class_='t-Report-report')
            if not results_table:
                # Try alternative table classes
                results_table = search_soup.find('table', {'id': re.compile(r'report', re.I)})

            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip header

                for row in rows[:5]:  # Process first 5 registrations
                    cells = row.find_all(['td', 'th'])

                    if len(cells) >= 2:
                        # Extract registration number
                        reg_link = cells[1].find('a')
                        if reg_link:
                            reg_number = reg_link.get_text(strip=True)

                            # Follow the registration link to get details
                            reg_href = reg_link.get('href')
                            if reg_href:
                                if not reg_href.startswith('http'):
                                    reg_href = base_url + '/' + reg_href.lstrip('/')

                                detail_response = session.get(reg_href, timeout=10)
                                if detail_response.status_code == 200:
                                    detail_soup = BeautifulSoup(detail_response.text, 'lxml')

                                    # Extract client information from detail page
                                    client_info = extract_client_info(detail_soup, firm_name, reg_number)
                                    if client_info:
                                        clients.extend(client_info)
            else:
                logger.warning("No results table found in FARA search")

    except requests.RequestException as e:
        logger.error(f"Failed to fetch FARA data: {e}")
    except Exception as e:
        logger.error(f"Error processing FARA data: {e}")

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def extract_client_info(soup: BeautifulSoup, firm_name: str, reg_number: str) -> List[Dict[str, Optional[str]]]:
    """Extract client information from FARA detail page"""
    clients = []

    # Look for foreign principal information
    # Common patterns in FARA pages
    principal_labels = ['Foreign Principal', 'Name of Foreign Principal', 'Client']

    for label in principal_labels:
        # Find label element
        label_elem = soup.find(string=re.compile(label, re.I))
        if label_elem:
            # Get the parent and look for the value
            parent = label_elem.parent
            if parent:
                # Value might be in next sibling or within a span/div
                value = None
                next_elem = parent.find_next_sibling()
                if next_elem:
                    value = next_elem.get_text(strip=True)
                else:
                    # Try finding within parent's parent
                    grandparent = parent.parent
                    if grandparent:
                        value_elem = grandparent.find('span', class_='display_only')
                        if not value_elem:
                            value_elem = grandparent.find('div', class_='t-Form-inputContainer')
                        if value_elem:
                            value = value_elem.get_text(strip=True)

                if value and len(value) > 2:
                    # Extract country if present
                    country = None
                    country_elem = soup.find(string=re.compile(r'Country', re.I))
                    if country_elem:
                        country_parent = country_elem.parent
                        country_next = country_parent.find_next_sibling() if country_parent else None
                        if country_next:
                            country = country_next.get_text(strip=True)

                    # Extract date if present
                    start_date = None
                    date_elem = soup.find(string=re.compile(r'Date.*Registration|Effective Date', re.I))
                    if date_elem:
                        date_parent = date_elem.parent
                        date_next = date_parent.find_next_sibling() if date_parent else None
                        if date_next:
                            date_str = date_next.get_text(strip=True)
                            start_date = parse_date(date_str)

                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': reg_number,
                        'client_name': value,
                        'client_country': country,
                        'start_date': start_date,
                        'end_date': None
                    })
                    break

    # If no clients found on main page, check for exhibits link
    if not clients:
        # Look for exhibits or supplemental documents
        exhibits_link = soup.find('a', string=re.compile(r'Exhibit|Supplemental', re.I))
        if exhibits_link:
            logger.debug("Found exhibits link but cannot follow without JavaScript")

    return clients

def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats into ISO format"""
    if not date_str:
        return None

    date_formats = [
        '%m/%d/%Y',
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%m-%d-%Y',
        '%d-%b-%Y'
    ]

    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str.strip(), fmt)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # If no format matches, return as-is if it looks like a date
    if re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', date_str):
        return date_str

    return None