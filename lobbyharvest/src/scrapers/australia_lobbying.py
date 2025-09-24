"""
Australian Lobbying Register scraper - extracts client data from Australian registry
"""
import logging
import re
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)

def scrape(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Scrape client information from Australian Lobbying Register

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries
    """
    clients = []
    base_url = "https://lobbyists.ag.gov.au"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to the register (Angular app)
            logger.info(f"Navigating to Australian Lobbying Register for {firm_name}")
            page.goto(f"{base_url}/register", wait_until='networkidle')

            # Wait for Angular app to load
            page.wait_for_timeout(3000)

            # Look for search functionality
            # The Angular app may have a search box
            search_input = page.locator('input[type="search"], input[placeholder*="Search"], input[placeholder*="search"], input[name*="search"], input[id*="search"]').first

            if search_input.count() > 0:
                logger.info(f"Found search input, searching for {firm_name}")
                search_input.fill(firm_name)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
            else:
                # Try clicking on a browse/view all link first
                browse_link = page.locator('a:has-text("View all"), a:has-text("Browse"), a:has-text("All lobbyists")').first
                if browse_link.count() > 0:
                    browse_link.click()
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)

            # Look for results - try multiple selectors
            # Check for table rows or cards with firm name
            result_selectors = [
                f'tr:has-text("{firm_name}")',
                f'div.card:has-text("{firm_name}")',
                f'div.result:has-text("{firm_name}")',
                f'a:has-text("{firm_name}")',
                f'td:has-text("{firm_name}")'
            ]

            found_result = False
            for selector in result_selectors:
                results = page.locator(selector).all()
                if results:
                    logger.info(f"Found {len(results)} results with selector {selector}")
                    for result in results[:3]:  # Process first 3 matches
                        try:
                            # Look for a link to details page
                            link = result.locator('a').first
                            if link.count() > 0:
                                link.click()
                                page.wait_for_load_state('networkidle')
                                page.wait_for_timeout(2000)

                                # Extract details from the page
                                extracted = extract_details_from_page(page, firm_name)
                                if extracted:
                                    clients.extend(extracted)
                                    found_result = True

                                # Go back to results
                                page.go_back()
                                page.wait_for_load_state('networkidle')
                                page.wait_for_timeout(1000)
                            else:
                                # Try to extract from the current view
                                extracted = extract_from_result_row(result, firm_name)
                                if extracted:
                                    clients.extend(extracted)
                                    found_result = True
                        except Exception as e:
                            logger.warning(f"Error processing result: {e}")
                            continue

                    if found_result:
                        break

            if not found_result:
                # Try alternative approach - look for the firm in all page text
                page_text = page.content()
                if firm_name.lower() in page_text.lower():
                    logger.info(f"Found {firm_name} in page content, attempting extraction")
                    # Extract any visible client information
                    clients.extend(extract_clients_from_page(page, firm_name))

        except Exception as e:
            logger.error(f"Failed to scrape Australian lobbying data: {e}")
        finally:
            browser.close()

    logger.info(f"Found {len(clients)} clients for {firm_name}")
    return clients

def extract_details_from_page(page: Page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract client details from a lobbyist detail page"""
    clients = []

    try:
        # Extract firm ABN if present
        firm_abn = None
        abn_elem = page.locator('text=/\\b\\d{2}\\s?\\d{3}\\s?\\d{3}\\s?\\d{3}\\b/').first
        if abn_elem.count() > 0:
            abn_text = abn_elem.text_content()
            if abn_text:
                firm_abn = re.sub(r'\s', '', abn_text)

        # Look for client sections
        client_sections = [
            'h2:has-text("Client")',
            'h3:has-text("Client")',
            'h4:has-text("Client")',
            'strong:has-text("Client")',
            'text=/.*Clients.*/i'
        ]

        for selector in client_sections:
            headers = page.locator(selector).all()
            for header in headers:
                # Look for following content
                parent = header.locator('xpath=..').first
                if parent.count() > 0:
                    # Check for tables
                    tables = parent.locator('table').all()
                    for table in tables:
                        rows = table.locator('tbody tr, tr').all()
                        for row in rows[1:]:  # Skip header
                            cells = row.locator('td').all()
                            if cells:
                                client_name = cells[0].text_content()
                                if client_name and len(client_name.strip()) > 3:
                                    clients.append({
                                        'firm_name': firm_name,
                                        'firm_registration_number': firm_abn,
                                        'client_name': client_name.strip(),
                                        'client_registration_number': cells[1].text_content().strip() if len(cells) > 1 else None,
                                        'client_start_date': cells[2].text_content().strip() if len(cells) > 2 else None,
                                        'client_end_date': cells[3].text_content().strip() if len(cells) > 3 else None
                                    })

                    # Check for lists
                    lists = parent.locator('ul, ol').all()
                    for lst in lists:
                        items = lst.locator('li').all()
                        for item in items:
                            client_name = item.text_content()
                            if client_name and len(client_name.strip()) > 3:
                                # Extract ABN if present
                                client_abn = None
                                abn_match = re.search(r'\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b', client_name)
                                if abn_match:
                                    client_abn = abn_match.group(0).replace(' ', '')
                                    client_name = client_name.replace(abn_match.group(0), '').strip()

                                clients.append({
                                    'firm_name': firm_name,
                                    'firm_registration_number': firm_abn,
                                    'client_name': client_name.strip(),
                                    'client_registration_number': client_abn,
                                    'client_start_date': None,
                                    'client_end_date': None
                                })

    except Exception as e:
        logger.error(f"Error extracting details: {e}")

    return clients

def extract_from_result_row(result, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract client info from a result row/card"""
    clients = []

    try:
        # Check if this row/card contains client information
        text_content = result.text_content()
        if text_content and 'client' in text_content.lower():
            # Try to extract structured data
            # Look for patterns like "Client: XYZ"
            import re
            client_matches = re.findall(r'[Cc]lient[s]?[:\s]+([^,\n]+)', text_content)
            for match in client_matches:
                if match and len(match.strip()) > 3:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': None,
                        'client_name': match.strip(),
                        'client_registration_number': None,
                        'client_start_date': None,
                        'client_end_date': None
                    })
    except Exception as e:
        logger.warning(f"Error extracting from result: {e}")

    return clients

def extract_clients_from_page(page: Page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract any visible client information from the current page"""
    clients = []

    try:
        # Look for any elements mentioning clients
        client_elements = page.locator('*:has-text("client")').all()

        for elem in client_elements[:20]:  # Limit to avoid too many elements
            text = elem.text_content()
            if text and len(text) < 500:  # Avoid very long text blocks
                # Look for patterns
                import re
                # Pattern: "Client: Name" or "Clients: Name1, Name2"
                matches = re.findall(r'[Cc]lients?[:\s]+([^.\n]{3,100})', text)
                for match in matches:
                    # Split by comma if multiple
                    names = [n.strip() for n in match.split(',')]
                    for name in names:
                        if len(name) > 3 and not any(skip in name.lower() for skip in ['click', 'view', 'search', 'filter']):
                            clients.append({
                                'firm_name': firm_name,
                                'firm_registration_number': None,
                                'client_name': name,
                                'client_registration_number': None,
                                'client_start_date': None,
                                'client_end_date': None
                            })

    except Exception as e:
        logger.error(f"Error extracting clients from page: {e}")

    return clients