"""
Australian Foreign Influence Transparency Scheme scraper - extracts registrant/client data
"""
import asyncio
import logging
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

async def scrape_async(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Asynchronously scrape client information from Australian Foreign Influence Transparency Scheme

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries with firm and client details
    """
    clients = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate directly to the registrants page
            await page.goto('https://transparency.ag.gov.au/Registrants', wait_until='networkidle')
            await page.wait_for_timeout(2000)

            # Search for the firm
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                'input[name*="search"]',
                'input[id*="search"]',
                'input[type="text"]'
            ]

            search_input = None
            for selector in search_selectors:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    search_input = elem
                    logger.info(f"Found search input with selector: {selector}")
                    break

            if search_input:
                await search_input.fill(firm_name)
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
            else:
                logger.warning("Could not find search input")

            # Look for result links with the firm name - try multiple approaches
            result_links = []

            # Try exact match first
            exact_links = await page.locator(f'a:has-text("{firm_name}")').all()
            result_links.extend(exact_links)

            # If no exact matches, try case-insensitive partial match
            if not result_links:
                all_links = await page.locator('a').all()
                for link in all_links:
                    link_text = await link.text_content()
                    if link_text and firm_name.lower() in link_text.lower():
                        result_links.append(link)

            for link in result_links[:3]:  # Process first 3 matches
                try:
                    # Skip if it's a navigation link
                    href = await link.get_attribute('href')
                    if not href or not ('/registrant/' in href or '/registration/' in href or 'id=' in href):
                        continue

                    # Click on the registrant link
                    await link.click()
                    await page.wait_for_load_state('networkidle')

                    # Extract registrant details
                    registrant_data = await extract_registrant_details(page, firm_name)
                    if registrant_data:
                        clients.extend(registrant_data)

                    # Go back to results
                    await page.go_back()
                    await page.wait_for_load_state('networkidle')

                except Exception as e:
                    logger.warning(f"Error processing registrant link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape Foreign Influence data: {e}")
        finally:
            await browser.close()

    logger.info(f"Found {len(clients)} client entries for {firm_name}")
    return clients

async def extract_registrant_details(page: Page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract registrant and client details from detail page"""
    clients = []

    try:
        # Extract registration number
        reg_number = None
        reg_elem = page.locator('text=/Registration.*number.*[:：]/i')
        if await reg_elem.count() > 0:
            reg_text = await reg_elem.first.text_content()
            # Extract number after colon
            if ':' in reg_text or '：' in reg_text:
                reg_number = reg_text.split(':')[-1].strip() if ':' in reg_text else reg_text.split('：')[-1].strip()

        if not reg_number:
            # Try alternative patterns
            reg_elem = page.locator('text=/.*[A-Z0-9]{3,}-[A-Z0-9]{3,}.*/i')
            if await reg_elem.count() > 0:
                reg_text = await reg_elem.first.text_content()
                import re
                match = re.search(r'[A-Z0-9]{3,}-[A-Z0-9]{3,}', reg_text)
                if match:
                    reg_number = match.group(0)

        # Look for foreign principal/client section
        principal_headers = []

        # Try multiple selectors
        selectors = [
            'h2:has-text("Foreign principal")',
            'h3:has-text("Foreign principal")',
            'h2:has-text("Client")',
            'h3:has-text("Client")',
            'text=/.*Foreign.*principal.*/i'
        ]

        for selector in selectors:
            try:
                headers = await page.locator(selector).all()
                principal_headers.extend(headers)
            except:
                continue

        for header in principal_headers:
            # Get the parent section
            parent = await header.locator('xpath=ancestor::*[self::div or self::section][1]').first
            if parent:
                # Extract client name
                client_name = None
                name_elem = await parent.locator('text=/Name.*[:：]/i').first
                if name_elem and await name_elem.count() > 0:
                    name_text = await name_elem.text_content()
                    if ':' in name_text or '：' in name_text:
                        client_name = name_text.split(':')[-1].strip() if ':' in name_text else name_text.split('：')[-1].strip()

                if not client_name:
                    # Try to get text after the header
                    next_elem = await header.locator('xpath=following-sibling::*[1]').first
                    if next_elem and await next_elem.count() > 0:
                        client_name = await next_elem.text_content()
                        client_name = client_name.strip() if client_name else None

                # Extract dates
                start_date = None
                end_date = None

                date_elem = await parent.locator('text=/.*Start.*date.*[:：]/i, text=/.*Commencement.*[:：]/i').first
                if date_elem and await date_elem.count() > 0:
                    date_text = await date_elem.text_content()
                    if ':' in date_text or '：' in date_text:
                        start_date = date_text.split(':')[-1].strip() if ':' in date_text else date_text.split('：')[-1].strip()

                end_elem = await parent.locator('text=/.*End.*date.*[:：]/i, text=/.*Cessation.*[:：]/i').first
                if end_elem and await end_elem.count() > 0:
                    end_text = await end_elem.text_content()
                    if ':' in end_text or '：' in end_text:
                        end_date = end_text.split(':')[-1].strip() if ':' in end_text else end_text.split('：')[-1].strip()

                if client_name and len(client_name) > 2:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': reg_number,
                        'client_name': client_name,
                        'client_registration_number': None,  # Not typically provided
                        'start_date': start_date,
                        'end_date': end_date
                    })

        # If no clients found with structured approach, try tables
        if not clients:
            tables = await page.locator('table').all()
            for table in tables:
                # Check if table has relevant headers
                headers = await table.locator('th').all()
                header_texts = [await h.text_content() for h in headers]

                if any('principal' in (h or '').lower() or 'client' in (h or '').lower() for h in header_texts):
                    rows = await table.locator('tbody tr').all()
                    for row in rows:
                        cells = await row.locator('td').all()
                        if cells:
                            cell_texts = [await c.text_content() for c in cells]
                            # First cell is usually the name
                            if cell_texts[0] and len(cell_texts[0].strip()) > 2:
                                clients.append({
                                    'firm_name': firm_name,
                                    'firm_registration_number': reg_number,
                                    'client_name': cell_texts[0].strip(),
                                    'client_registration_number': None,
                                    'start_date': cell_texts[1].strip() if len(cell_texts) > 1 else None,
                                    'end_date': cell_texts[2].strip() if len(cell_texts) > 2 else None
                                })

    except Exception as e:
        logger.error(f"Error extracting registrant details: {e}")

    return clients

def scrape(firm_name: str) -> List[Dict[str, Optional[str]]]:
    """
    Synchronously scrape client information from Australian Foreign Influence Transparency Scheme

    Args:
        firm_name: Name of the lobbying firm to search

    Returns:
        List of client dictionaries with firm and client details
    """
    clients = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate directly to the registrants page
            page.goto('https://transparency.ag.gov.au/Registrants', wait_until='networkidle')
            page.wait_for_timeout(2000)

            # Search for the firm
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                'input[name*="search"]',
                'input[id*="search"]',
                'input[type="text"]'
            ]

            search_input = None
            for selector in search_selectors:
                elem = page.locator(selector).first
                if elem.count() > 0:
                    search_input = elem
                    logger.info(f"Found search input with selector: {selector}")
                    break

            if search_input:
                search_input.fill(firm_name)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
            else:
                logger.warning("Could not find search input")

            # Look for result links with the firm name - try multiple approaches
            result_links = []

            # Try exact match first
            exact_links = page.locator(f'a:has-text("{firm_name}")').all()
            result_links.extend(exact_links)

            # If no exact matches, try case-insensitive partial match
            if not result_links:
                all_links = page.locator('a').all()
                for link in all_links:
                    link_text = link.text_content()
                    if link_text and firm_name.lower() in link_text.lower():
                        result_links.append(link)

            for link in result_links[:3]:  # Process first 3 matches
                try:
                    # Skip if it's a navigation link
                    href = link.get_attribute('href')
                    if not href or not ('/registrant/' in href or '/registration/' in href or 'id=' in href):
                        continue

                    # Click on the registrant link
                    link.click()
                    page.wait_for_load_state('networkidle')

                    # Extract registrant details (sync version)
                    registrant_data = extract_registrant_details_sync(page, firm_name)
                    if registrant_data:
                        clients.extend(registrant_data)

                    # Go back to results
                    page.go_back()
                    page.wait_for_load_state('networkidle')

                except Exception as e:
                    logger.warning(f"Error processing registrant link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape Foreign Influence data: {e}")
        finally:
            browser.close()

    logger.info(f"Found {len(clients)} client entries for {firm_name}")
    return clients

def extract_registrant_details_sync(page, firm_name: str) -> List[Dict[str, Optional[str]]]:
    """Extract registrant and client details from detail page (sync version)"""
    clients = []

    try:
        # Extract registration number
        reg_number = None
        reg_elem = page.locator('text=/Registration.*number.*[:：]/i')
        if reg_elem.count() > 0:
            reg_text = reg_elem.first.text_content()
            # Extract number after colon
            if ':' in reg_text or '：' in reg_text:
                reg_number = reg_text.split(':')[-1].strip() if ':' in reg_text else reg_text.split('：')[-1].strip()

        if not reg_number:
            # Try alternative patterns - look for ID patterns
            reg_elem = page.locator('text=/[A-Z0-9]{2,}-[A-Z0-9]{2,}/i').first
            if reg_elem.count() > 0:
                reg_text = reg_elem.text_content()
                import re
                match = re.search(r'[A-Z0-9]{2,}-[A-Z0-9]{2,}', reg_text)
                if match:
                    reg_number = match.group(0)

        # Look for foreign principal/client section
        principal_headers = []

        # Try multiple selectors
        selectors = [
            'h2:has-text("Foreign principal")',
            'h3:has-text("Foreign principal")',
            'h2:has-text("Client")',
            'h3:has-text("Client")',
            'text=/.*Foreign.*principal.*/i'
        ]

        for selector in selectors:
            try:
                headers = page.locator(selector).all()
                principal_headers.extend(headers)
            except:
                continue

        for header in principal_headers:
            # Get the parent section
            parent = header.locator('xpath=ancestor::*[self::div or self::section][1]').first
            if parent:
                # Extract client name
                client_name = None
                name_elem = parent.locator('text=/Name.*[:：]/i').first
                if name_elem and name_elem.count() > 0:
                    name_text = name_elem.text_content()
                    if ':' in name_text or '：' in name_text:
                        client_name = name_text.split(':')[-1].strip() if ':' in name_text else name_text.split('：')[-1].strip()

                if not client_name:
                    # Try to get text after the header
                    next_elem = header.locator('xpath=following-sibling::*[1]').first
                    if next_elem and next_elem.count() > 0:
                        client_name = next_elem.text_content()
                        client_name = client_name.strip() if client_name else None

                # Extract dates
                start_date = None
                end_date = None

                date_elem = parent.locator('text=/.*Start.*date.*[:：]/i, text=/.*Commencement.*[:：]/i').first
                if date_elem and date_elem.count() > 0:
                    date_text = date_elem.text_content()
                    if ':' in date_text or '：' in date_text:
                        start_date = date_text.split(':')[-1].strip() if ':' in date_text else date_text.split('：')[-1].strip()

                end_elem = parent.locator('text=/.*End.*date.*[:：]/i, text=/.*Cessation.*[:：]/i').first
                if end_elem and end_elem.count() > 0:
                    end_text = end_elem.text_content()
                    if ':' in end_text or '：' in end_text:
                        end_date = end_text.split(':')[-1].strip() if ':' in end_text else end_text.split('：')[-1].strip()

                if client_name and len(client_name) > 2:
                    clients.append({
                        'firm_name': firm_name,
                        'firm_registration_number': reg_number,
                        'client_name': client_name,
                        'client_registration_number': None,  # Not typically provided
                        'start_date': start_date,
                        'end_date': end_date
                    })

        # If no clients found with structured approach, try tables
        if not clients:
            tables = page.locator('table').all()
            for table in tables:
                # Check if table has relevant headers
                headers = table.locator('th').all()
                header_texts = [h.text_content() or '' for h in headers]

                # Look for tables with foreign principal or client columns
                for h_idx, h_text in enumerate(header_texts):
                    if 'principal' in h_text.lower() or 'client' in h_text.lower() or 'name' in h_text.lower():
                        rows = table.locator('tbody tr, tr').all()
                        for row in rows:
                            cells = row.locator('td').all()
                            if cells and len(cells) > h_idx:
                                cell_text = cells[h_idx].text_content()
                                if cell_text and len(cell_text.strip()) > 2 and not any(skip in cell_text.lower() for skip in ['sort by', 'read more', 'filter']):
                                    # Look for dates in other columns
                                    start_date = None
                                    end_date = None
                                    for i, cell in enumerate(cells):
                                        cell_content = cell.text_content() or ''
                                        if 'start' in header_texts[i].lower() if i < len(header_texts) else False:
                                            start_date = cell_content.strip()
                                        elif 'end' in header_texts[i].lower() if i < len(header_texts) else False:
                                            end_date = cell_content.strip()

                                    clients.append({
                                        'firm_name': firm_name,
                                        'firm_registration_number': reg_number,
                                        'client_name': cell_text.strip(),
                                        'client_registration_number': None,
                                        'start_date': start_date,
                                        'end_date': end_date
                                    })
                        break  # Found the right column, no need to check others

    except Exception as e:
        logger.error(f"Error extracting registrant details: {e}")

    return clients