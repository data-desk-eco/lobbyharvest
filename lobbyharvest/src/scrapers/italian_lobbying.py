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
            # Navigate to the search page
            search_url = f"{base_url}/sito/ricerca-avanzata.html"
            await page.goto(search_url, wait_until='networkidle', timeout=30000)

            # Try the main listing page as fallback
            listing_url = f"{base_url}/sito/elenco-categorie.html"

            # Search for the firm
            search_input = await page.query_selector('input[type="text"], input[name*="search"], input[name*="ricerca"]')
            if search_input:
                await search_input.fill(firm_name)
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle', timeout=10000)
            else:
                # Try navigating directly to listing page
                await page.goto(listing_url, wait_until='networkidle', timeout=30000)

            # Look for links containing the firm name
            links = await page.query_selector_all('a')
            firm_found = False

            for link in links:
                text = await link.text_content()
                if text and firm_name.lower() in text.lower():
                    href = await link.get_attribute('href')
                    if href and 'scheda' in href:
                        # Found a firm detail page
                        if not href.startswith('http'):
                            href = base_url + '/' + href.lstrip('/')

                        # Navigate to firm detail page
                        await page.goto(href, wait_until='networkidle', timeout=30000)
                        firm_found = True
                        break

            if not firm_found:
                # Try direct URL patterns
                # Example: /sito/legal_353/scheda-persona-giuridica.html
                direct_urls = [
                    f"{base_url}/sito/legal_353/scheda-persona-giuridica.html",
                    f"{base_url}/sito/scheda-persona-giuridica.html"
                ]

                for url in direct_urls:
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=30000)
                        # Check if page contains firm name
                        content = await page.content()
                        if firm_name.lower() in content.lower():
                            firm_found = True
                            break
                    except:
                        continue

            if firm_found:
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
        # Look for sections containing client information
        # Italian terms: "clienti", "rappresentati", "soggetti rappresentati"
        client_sections = await page.query_selector_all(
            'section:has-text("clienti"), '
            'section:has-text("rappresentati"), '
            'div:has-text("soggetti rappresentati"), '
            'table'
        )

        # Also check for tables containing client data
        tables = await page.query_selector_all('table')
        for table in tables:
            rows = await table.query_selector_all('tr')
            for row in rows:
                cells = await row.query_selector_all('td, th')
                if len(cells) >= 2:
                    # Extract text from cells
                    cell_texts = []
                    for cell in cells:
                        text = await cell.text_content()
                        if text:
                            cell_texts.append(text.strip())

                    # Look for client-like data
                    if len(cell_texts) >= 2:
                        potential_client = cell_texts[0]
                        # Skip header rows
                        if not any(header in potential_client.lower() for header in ['cliente', 'soggetto', 'denominazione', 'nome']):
                            # Extract dates if present
                            start_date = None
                            end_date = None

                            for text in cell_texts[1:]:
                                # Look for date patterns (DD/MM/YYYY or YYYY)
                                if '/' in text or text.isdigit():
                                    if not start_date:
                                        start_date = parse_italian_date(text)
                                    elif not end_date:
                                        end_date = parse_italian_date(text)

                            if potential_client and potential_client != firm_name:
                                clients.append({
                                    'firm_name': firm_name,
                                    'firm_registration_number': None,
                                    'client_name': potential_client,
                                    'client_registration_number': None,
                                    'start_date': start_date,
                                    'end_date': end_date
                                })

        # Look for lists of clients
        lists = await page.query_selector_all('ul li, ol li')
        for item in lists:
            text = await item.text_content()
            if text and text.strip() and text.strip() != firm_name:
                # Check if this looks like a client entry
                if not any(skip in text.lower() for skip in ['cookie', 'privacy', 'menu', 'home']):
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': text.strip(),
                        'client_registration_number': None,
                        'start_date': None,
                        'end_date': None
                    })

        # Look for divs or sections with client information
        client_divs = await page.query_selector_all(
            'div.client, div.cliente, div.rappresentato, '
            'article.client, article.cliente'
        )

        for div in client_divs:
            name_elem = await div.query_selector('h3, h4, strong, .name, .nome')
            if name_elem:
                client_name = await name_elem.text_content()
                if client_name and client_name.strip() != firm_name:
                    # Look for dates in the same div
                    date_text = await div.text_content()
                    start_date = None
                    end_date = None

                    # Extract dates from text
                    import re
                    date_pattern = r'\d{1,2}/\d{1,2}/\d{4}|\d{4}'
                    dates = re.findall(date_pattern, date_text)
                    if dates:
                        start_date = parse_italian_date(dates[0])
                        if len(dates) > 1:
                            end_date = parse_italian_date(dates[1])

                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': client_name.strip(),
                        'client_registration_number': None,
                        'start_date': start_date,
                        'end_date': end_date
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
            # Navigate to the search page
            search_url = f"{base_url}/sito/ricerca-avanzata.html"
            page.goto(search_url, wait_until='networkidle', timeout=30000)

            # Try the main listing page as fallback
            listing_url = f"{base_url}/sito/elenco-categorie.html"

            # Search for the firm
            search_input = page.query_selector('input[type="text"], input[name*="search"], input[name*="ricerca"]')
            if search_input:
                search_input.fill(firm_name)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle', timeout=10000)
            else:
                # Try navigating directly to listing page
                page.goto(listing_url, wait_until='networkidle', timeout=30000)

            # Look for links containing the firm name
            links = page.query_selector_all('a')
            firm_found = False

            for link in links:
                text = link.text_content()
                if text and firm_name.lower() in text.lower():
                    href = link.get_attribute('href')
                    if href and 'scheda' in href:
                        # Found a firm detail page
                        if not href.startswith('http'):
                            href = base_url + '/' + href.lstrip('/')

                        # Navigate to firm detail page
                        page.goto(href, wait_until='networkidle', timeout=30000)
                        firm_found = True
                        break

            if not firm_found:
                # Try direct URL patterns
                direct_urls = [
                    f"{base_url}/sito/legal_353/scheda-persona-giuridica.html",
                    f"{base_url}/sito/scheda-persona-giuridica.html"
                ]

                for url in direct_urls:
                    try:
                        page.goto(url, wait_until='networkidle', timeout=30000)
                        # Check if page contains firm name
                        content = page.content()
                        if firm_name.lower() in content.lower():
                            firm_found = True
                            break
                    except:
                        continue

            if firm_found:
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
        # Look for tables containing client data
        tables = page.query_selector_all('table')
        for table in tables:
            rows = table.query_selector_all('tr')
            for row in rows:
                cells = row.query_selector_all('td, th')
                if len(cells) >= 2:
                    # Extract text from cells
                    cell_texts = []
                    for cell in cells:
                        text = cell.text_content()
                        if text:
                            cell_texts.append(text.strip())

                    # Look for client-like data
                    if len(cell_texts) >= 2:
                        potential_client = cell_texts[0]
                        # Skip header rows
                        if not any(header in potential_client.lower() for header in ['cliente', 'soggetto', 'denominazione', 'nome']):
                            # Extract dates if present
                            start_date = None
                            end_date = None

                            for text in cell_texts[1:]:
                                # Look for date patterns (DD/MM/YYYY or YYYY)
                                if '/' in text or text.isdigit():
                                    if not start_date:
                                        start_date = parse_italian_date(text)
                                    elif not end_date:
                                        end_date = parse_italian_date(text)

                            if potential_client and potential_client != firm_name:
                                clients.append({
                                    'firm_name': firm_name,
                                    'firm_registration_number': None,
                                    'client_name': potential_client,
                                    'client_registration_number': None,
                                    'start_date': start_date,
                                    'end_date': end_date
                                })

        # Look for lists of clients
        lists = page.query_selector_all('ul li, ol li')
        for item in lists:
            text = item.text_content()
            if text and text.strip() and text.strip() != firm_name:
                # Check if this looks like a client entry
                if not any(skip in text.lower() for skip in ['cookie', 'privacy', 'menu', 'home']):
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': text.strip(),
                        'client_registration_number': None,
                        'start_date': None,
                        'end_date': None
                    })

        # Look for divs or sections with client information
        client_divs = page.query_selector_all(
            'div.client, div.cliente, div.rappresentato, '
            'article.client, article.cliente'
        )

        for div in client_divs:
            name_elem = div.query_selector('h3, h4, strong, .name, .nome')
            if name_elem:
                client_name = name_elem.text_content()
                if client_name and client_name.strip() != firm_name:
                    # Look for dates in the same div
                    date_text = div.text_content()
                    start_date = None
                    end_date = None

                    # Extract dates from text
                    import re
                    date_pattern = r'\d{1,2}/\d{1,2}/\d{4}|\d{4}'
                    dates = re.findall(date_pattern, date_text)
                    if dates:
                        start_date = parse_italian_date(dates[0])
                        if len(dates) > 1:
                            end_date = parse_italian_date(dates[1])

                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': client_name.strip(),
                        'client_registration_number': None,
                        'start_date': start_date,
                        'end_date': end_date
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