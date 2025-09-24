"""
Austrian Lobbying and Advocacy Register scraper - extracts client data using Playwright
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

async def scrape_async(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Async scrape client information from Austrian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    # Navigate directly to the main page which redirects to the search form
    base_url = "https://lobbyreg.justiz.gv.at/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to the site - it will redirect to the search form
            await page.goto(base_url, wait_until="networkidle", timeout=30000)

            # The search input has id="FT" and name="FT"
            search_input = await page.wait_for_selector('#FT', timeout=5000)

            if search_input:
                # Fill the search field (fill() automatically clears existing content)
                await search_input.fill(firm_name)

                # Find and click the "Suchen" (Search) button
                # The button has value="   Suchen   "
                search_button = await page.query_selector('input[type="submit"][value*="Suchen"]')

                if search_button:
                    # Try to click the button using JavaScript to avoid viewport issues
                    try:
                        await page.evaluate('(button) => button.click()', search_button)
                    except:
                        # Fallback to normal click
                        await search_button.click()
                else:
                    # Fallback: press Enter
                    await search_input.press('Enter')

                # Wait for results to load
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)  # Additional wait for dynamic content

                # Extract results
                clients = await extract_clients_from_page(page, firm_name)

                # Check if there are detail pages to follow
                firm_links = await page.query_selector_all(f'a:has-text("{firm_name}")')
                if not firm_links and not clients:
                    # Try case-insensitive search for links
                    all_links = await page.query_selector_all('a')
                    for link in all_links[:10]:  # Check first 10 links
                        link_text = await link.text_content()
                        if link_text and firm_name.lower() in link_text.lower():
                            firm_links = [link]
                            break

                # Follow first matching link for more details
                if firm_links and not clients:
                    await firm_links[0].click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(1)

                    # Extract from detail page
                    detail_clients = await extract_clients_from_page(page, firm_name)
                    clients.extend(detail_clients)

        except Exception as e:
            logger.error(f"Failed to scrape Austrian lobbying data: {e}")
        finally:
            await browser.close()

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

async def extract_clients_from_page(page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract client information from the current page"""
    clients = []

    # Try to find tables with client information
    tables = await page.query_selector_all('table')
    for table in tables:
        # Check if table might contain client data
        table_text = await table.text_content()
        if table_text and any(keyword in table_text.lower() for keyword in ['klient', 'client', 'auftrag', 'mandat']):
            rows = await table.query_selector_all('tr')

            # Find header row to identify columns
            headers = []
            if rows:
                header_cells = await rows[0].query_selector_all('th')
                if not header_cells:
                    header_cells = await rows[0].query_selector_all('td')
                for cell in header_cells:
                    header_text = await cell.text_content()
                    headers.append(header_text.strip() if header_text else '')

            # Process data rows
            for row in rows[1:]:
                cells = await row.query_selector_all('td')
                if not cells:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    cell_text = await cell.text_content()
                    if i < len(headers) and headers[i]:
                        row_data[headers[i]] = cell_text.strip() if cell_text else ''
                    else:
                        row_data[f'col_{i}'] = cell_text.strip() if cell_text else ''

                # Try to identify client name from row data
                client_name = None
                for key in ['Klient', 'Client', 'Auftraggeber', 'Name', 'Kunde']:
                    if key in row_data:
                        client_name = row_data[key]
                        break

                # If no specific client column, try to find non-empty cells that look like names
                if not client_name:
                    for value in row_data.values():
                        if value and len(value) > 3 and value != firm_name:
                            client_name = value
                            break

                if client_name:
                    # Extract dates
                    start_date = None
                    end_date = None
                    for key, value in row_data.items():
                        key_lower = key.lower()
                        if any(term in key_lower for term in ['start', 'beginn', 'von', 'from']):
                            start_date = parse_german_date(value)
                        elif any(term in key_lower for term in ['end', 'ende', 'bis', 'to']):
                            end_date = parse_german_date(value)
                        elif 'datum' in key_lower or 'date' in key_lower:
                            if not start_date:
                                start_date = parse_german_date(value)

                    # Extract registration numbers
                    firm_reg = None
                    client_reg = None
                    for key, value in row_data.items():
                        key_lower = key.lower()
                        if any(term in key_lower for term in ['registr', 'nummer', 'id']) and value:
                            if 'klient' in key_lower or 'client' in key_lower:
                                client_reg = value
                            elif not firm_reg:
                                firm_reg = value

                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': firm_reg,
                        'client_name': client_name,
                        'client_registration_number': client_reg,
                        'start_date': start_date,
                        'end_date': end_date
                    })

    # If no tables, try to find client information in lists or divs
    if not clients:
        # Look for sections with client-related keywords
        sections = await page.query_selector_all('section, div, article')
        for section in sections[:20]:  # Limit to first 20 sections
            section_text = await section.text_content()
            if section_text and any(keyword in section_text.lower() for keyword in ['klient', 'client', 'auftrag']):
                # Look for lists within this section
                lists = await section.query_selector_all('ul, ol')
                for lst in lists:
                    items = await lst.query_selector_all('li')
                    for item in items:
                        item_text = await item.text_content()
                        if item_text and len(item_text.strip()) > 3:
                            clients.append({
                                'firm_name': firm_name,
                                'firm_registration_number': None,
                                'client_name': item_text.strip(),
                                'client_registration_number': None,
                                'start_date': None,
                                'end_date': None
                            })

    return clients

def parse_german_date(date_str: str) -> Optional[str]:
    """Parse German date format and return ISO format"""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try common German date formats
    formats = [
        '%d.%m.%Y',  # 31.12.2024
        '%d. %m. %Y',  # 31. 12. 2024
        '%d/%m/%Y',  # 31/12/2024
        '%Y-%m-%d',  # Already ISO
        '%d.%m.%y',  # 31.12.24
        '%d-%m-%Y',  # 31-12-2024
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue

    # If no format matches, return original string
    return date_str

def scrape(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Synchronous wrapper for scraping Austrian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    # Navigate directly to the main page which redirects to the search form
    base_url = "https://lobbyreg.justiz.gv.at/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to the site - it will redirect to the search form
            page.goto(base_url, wait_until="networkidle", timeout=30000)

            # The search input has id="FT" and name="FT"
            search_input = page.wait_for_selector('#FT', timeout=5000)

            if search_input:
                # Fill the search field (fill() automatically clears existing content)
                search_input.fill(firm_name)

                # Find and click the "Suchen" (Search) button
                # The button has value="   Suchen   "
                search_button = page.query_selector('input[type="submit"][value*="Suchen"]')

                if search_button:
                    # Try to click the button using JavaScript to avoid viewport issues
                    try:
                        page.evaluate('(button) => button.click()', search_button)
                    except:
                        # Fallback to normal click
                        search_button.click()
                else:
                    # Fallback: press Enter
                    search_input.press('Enter')

                # Wait for results to load
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)  # Additional wait for dynamic content

                # Extract results
                clients = extract_clients_from_page_sync(page, firm_name)

                # Check if there are detail pages to follow
                firm_links = page.query_selector_all(f'a:has-text("{firm_name}")')
                if not firm_links and not clients:
                    # Try case-insensitive search for links
                    all_links = page.query_selector_all('a')
                    for link in all_links[:10]:  # Check first 10 links
                        link_text = link.text_content()
                        if link_text and firm_name.lower() in link_text.lower():
                            firm_links = [link]
                            break

                # Follow first matching link for more details
                if firm_links and not clients:
                    firm_links[0].click()
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(1000)

                    # Extract from detail page
                    detail_clients = extract_clients_from_page_sync(page, firm_name)
                    clients.extend(detail_clients)

        except Exception as e:
            logger.error(f"Failed to scrape Austrian lobbying data: {e}")
        finally:
            browser.close()

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def extract_clients_from_page_sync(page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Synchronous version of extract_clients_from_page"""
    clients = []

    # Try to find tables with client information
    tables = page.query_selector_all('table')
    for table in tables:
        # Check if table might contain client data
        table_text = table.text_content()
        if table_text and any(keyword in table_text.lower() for keyword in ['klient', 'client', 'auftrag', 'mandat']):
            rows = table.query_selector_all('tr')

            # Find header row to identify columns
            headers = []
            if rows:
                header_cells = rows[0].query_selector_all('th')
                if not header_cells:
                    header_cells = rows[0].query_selector_all('td')
                for cell in header_cells:
                    header_text = cell.text_content()
                    headers.append(header_text.strip() if header_text else '')

            # Process data rows
            for row in rows[1:]:
                cells = row.query_selector_all('td')
                if not cells:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    cell_text = cell.text_content()
                    if i < len(headers) and headers[i]:
                        row_data[headers[i]] = cell_text.strip() if cell_text else ''
                    else:
                        row_data[f'col_{i}'] = cell_text.strip() if cell_text else ''

                # Try to identify client name from row data
                client_name = None
                for key in ['Klient', 'Client', 'Auftraggeber', 'Name', 'Kunde']:
                    if key in row_data:
                        client_name = row_data[key]
                        break

                # If no specific client column, try to find non-empty cells that look like names
                if not client_name:
                    for value in row_data.values():
                        if value and len(value) > 3 and value != firm_name:
                            client_name = value
                            break

                if client_name:
                    # Extract dates
                    start_date = None
                    end_date = None
                    for key, value in row_data.items():
                        key_lower = key.lower()
                        if any(term in key_lower for term in ['start', 'beginn', 'von', 'from']):
                            start_date = parse_german_date(value)
                        elif any(term in key_lower for term in ['end', 'ende', 'bis', 'to']):
                            end_date = parse_german_date(value)
                        elif 'datum' in key_lower or 'date' in key_lower:
                            if not start_date:
                                start_date = parse_german_date(value)

                    # Extract registration numbers
                    firm_reg = None
                    client_reg = None
                    for key, value in row_data.items():
                        key_lower = key.lower()
                        if any(term in key_lower for term in ['registr', 'nummer', 'id']) and value:
                            if 'klient' in key_lower or 'client' in key_lower:
                                client_reg = value
                            elif not firm_reg:
                                firm_reg = value

                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': firm_reg,
                        'client_name': client_name,
                        'client_registration_number': client_reg,
                        'start_date': start_date,
                        'end_date': end_date
                    })

    # If no tables, try to find client information in lists or divs
    if not clients:
        # Look for sections with client-related keywords
        sections = page.query_selector_all('section, div, article')
        for section in sections[:20]:  # Limit to first 20 sections
            section_text = section.text_content()
            if section_text and any(keyword in section_text.lower() for keyword in ['klient', 'client', 'auftrag']):
                # Look for lists within this section
                lists = section.query_selector_all('ul, ol')
                for lst in lists:
                    items = lst.query_selector_all('li')
                    for item in items:
                        item_text = item.text_content()
                        if item_text and len(item_text.strip()) > 3:
                            clients.append({
                                'firm_name': firm_name,
                                'firm_registration_number': None,
                                'client_name': item_text.strip(),
                                'client_registration_number': None,
                                'start_date': None,
                                'end_date': None
                            })

    return clients