"""
Italian Lobbying Register scraper - extracts client data from Italian registry
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

async def scrape_async(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Async scrape client information from Italian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    base_url = "https://rappresentantidiinteressi.camera.it"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='it-IT',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Navigate to the registry page which lists all firms
            registry_url = f"{base_url}/sito/registro.html"
            await page.goto(registry_url, wait_until='networkidle', timeout=30000)

            # Look for the firm in the registry
            # Try exact match first, then partial match
            firm_found = False
            firm_href = None

            # Try to find firm link with exact or partial match
            firm_links = await page.query_selector_all('a[href*="legal_"]')

            for link in firm_links:
                text = await link.text_content()
                if text:
                    text = text.strip()
                    # Check for match (case insensitive)
                    if firm_name.lower() in text.lower() or text.lower() in firm_name.lower():
                        firm_href = await link.get_attribute('href')
                        if firm_href:
                            firm_found = True
                            logger.info(f"Found firm '{text}' at {firm_href}")
                            break

            if firm_found and firm_href:
                # Navigate to the firm's detail page
                if not firm_href.startswith('http'):
                    firm_href = base_url + firm_href

                await page.goto(firm_href, wait_until='networkidle', timeout=30000)

                # Extract client information from the detail page
                clients = await extract_clients_from_page(page, firm_name)

        except PlaywrightTimeout:
            logger.warning(f"Timeout while accessing Italian registry for {firm_name}")
        except Exception as e:
            logger.error(f"Error scraping Italian registry for {firm_name}: {e}")
        finally:
            await browser.close()

    return clients

async def extract_clients_from_page(page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Extract client information from the firm's detail page
    """
    clients = []

    try:
        # Get page content to check for client sections
        content = await page.content()

        # Look for company names with Italian legal suffixes
        import re

        # Italian company patterns
        company_patterns = [
            r'\b[\w\s]+\s+S\.p\.A\.?\b',
            r'\b[\w\s]+\s+S\.r\.l\.?\b',
            r'\b[\w\s]+\s+SPA\b',
            r'\b[\w\s]+\s+SRL\b',
            r'\b[\w\s]+\s+S\.R\.L\.?\b',
            r'\b[\w\s]+\s+S\.P\.A\.?\b',
            r'\b[\w\s]+\s+S\.c\.a r\.l\.?\b',
            r'\b[\w\s]+\s+S\.n\.c\.?\b',
            r'\b[\w\s]+\s+S\.a\.s\.?\b'
        ]

        found_companies = set()

        # Extract companies from content
        for pattern in company_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                match = match.strip()
                # Skip if it's the firm itself
                if firm_name.lower() not in match.lower() and match.lower() not in firm_name.lower():
                    # Skip common non-client entries
                    if not any(skip in match.lower() for skip in ['camera', 'registro', 'cookie', 'privacy']):
                        found_companies.add(match)

        # Also look for card-div elements which may contain client info
        card_divs = await page.query_selector_all('.card-div')

        for card in card_divs:
            text = await card.text_content()
            if text:
                text = text.strip()
                # Skip the firm's own info card and category cards
                if firm_name.lower() not in text.lower():
                    if not any(skip in text.lower() for skip in ['categoria:', 'sede:', 'telefono:', 'email:', 'pec:', 'soggetti rappresentati']):
                        # Look for company patterns in this card
                        for pattern in company_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            for match in matches:
                                match = match.strip()
                                if match not in found_companies:
                                    found_companies.add(match)

        # Convert found companies to client records
        for company_name in found_companies:
            clients.append({
                'firm_name': firm_name,
                'firm_registration_number': None,
                'client_name': company_name,
                'client_registration_number': None,
                'start_date': None,
                'end_date': None
            })


    except Exception as e:
        logger.error(f"Error extracting clients from page: {e}")

    # Remove duplicates
    seen = set()
    unique_clients = []
    for client in clients:
        client_key = client['client_name']
        if client_key not in seen:
            seen.add(client_key)
            unique_clients.append(client)

    return unique_clients

def parse_italian_date(date_str: str) -> Optional[str]:
    """
    Parse Italian date format (DD/MM/YYYY) to ISO format
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try DD/MM/YYYY format
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                day, month, year = parts
                # Validate and format
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime('%Y-%m-%d')
            except:
                pass

    # Try just year
    if date_str.isdigit() and len(date_str) == 4:
        try:
            year = int(date_str)
            if 1900 <= year <= 2100:
                return f"{year}-01-01"
        except:
            pass

    return None

def scrape(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Sync wrapper for scraping Italian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    base_url = "https://rappresentantidiinteressi.camera.it"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale='it-IT',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Navigate to the registry page which lists all firms
            registry_url = f"{base_url}/sito/registro.html"
            page.goto(registry_url, wait_until='networkidle', timeout=30000)

            # Look for the firm in the registry
            # Try exact match first, then partial match
            firm_found = False
            firm_href = None

            # Try to find firm link with exact or partial match
            firm_links = page.query_selector_all('a[href*="legal_"]')

            for link in firm_links:
                text = link.text_content()
                if text:
                    text = text.strip()
                    # Check for match (case insensitive)
                    if firm_name.lower() in text.lower() or text.lower() in firm_name.lower():
                        firm_href = link.get_attribute('href')
                        if firm_href:
                            firm_found = True
                            logger.info(f"Found firm '{text}' at {firm_href}")
                            break

            if firm_found and firm_href:
                # Navigate to the firm's detail page
                if not firm_href.startswith('http'):
                    firm_href = base_url + firm_href

                page.goto(firm_href, wait_until='networkidle', timeout=30000)

                # Extract client information from the detail page
                clients = extract_clients_sync(page, firm_name)

        except Exception as e:
            logger.error(f"Error scraping Italian registry for {firm_name}: {e}")
        finally:
            browser.close()

    return clients

def extract_clients_sync(page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Sync version of client extraction from the firm's detail page
    """
    clients = []

    try:
        # Get page content to check for client sections
        content = page.content()

        # Look for company names with Italian legal suffixes
        import re

        # Italian company patterns
        company_patterns = [
            r'\b[\w\s]+\s+S\.p\.A\.?\b',
            r'\b[\w\s]+\s+S\.r\.l\.?\b',
            r'\b[\w\s]+\s+SPA\b',
            r'\b[\w\s]+\s+SRL\b',
            r'\b[\w\s]+\s+S\.R\.L\.?\b',
            r'\b[\w\s]+\s+S\.P\.A\.?\b',
            r'\b[\w\s]+\s+S\.c\.a r\.l\.?\b',
            r'\b[\w\s]+\s+S\.n\.c\.?\b',
            r'\b[\w\s]+\s+S\.a\.s\.?\b'
        ]

        found_companies = set()

        # Extract companies from content
        for pattern in company_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                match = match.strip()
                # Skip if it's the firm itself
                if firm_name.lower() not in match.lower() and match.lower() not in firm_name.lower():
                    # Skip common non-client entries
                    if not any(skip in match.lower() for skip in ['camera', 'registro', 'cookie', 'privacy']):
                        found_companies.add(match)

        # Also look for card-div elements which may contain client info
        card_divs = page.query_selector_all('.card-div')
        for card in card_divs:
            text = card.text_content()
            if text:
                text = text.strip()
                # Skip the firm's own info card and category cards
                if firm_name.lower() not in text.lower():
                    if not any(skip in text.lower() for skip in ['categoria:', 'sede:', 'telefono:', 'email:', 'pec:', 'soggetti rappresentati']):
                        # Look for company patterns in this card
                        for pattern in company_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            for match in matches:
                                match = match.strip()
                                if match not in found_companies:
                                    found_companies.add(match)

        # Convert found companies to client records
        for company_name in found_companies:
            clients.append({
                'firm_name': firm_name,
                'firm_registration_number': None,
                'client_name': company_name,
                'client_registration_number': None,
                'start_date': None,
                'end_date': None
            })

    except Exception as e:
        logger.error(f"Error extracting clients from page: {e}")

    # Remove duplicates
    seen = set()
    unique_clients = []
    for client in clients:
        client_key = client['client_name']
        if client_key not in seen:
            seen.add(client_key)
            unique_clients.append(client)

    return unique_clients

if __name__ == "__main__":
    # Test with FTI Consulting
    import sys

    if len(sys.argv) > 1:
        firm_name = sys.argv[1]
    else:
        firm_name = "FTI Consulting"

    print(f"Testing Italian Lobbying Register scraper with: {firm_name}")
    results = scrape(firm_name)

    if results:
        print(f"\nFound {len(results)} clients:")
        for client in results:
            print(f"  - {client['client_name']}")
            if client['start_date']:
                print(f"    Start: {client['start_date']}")
            if client['end_date']:
                print(f"    End: {client['end_date']}")
    else:
        print("No clients found")