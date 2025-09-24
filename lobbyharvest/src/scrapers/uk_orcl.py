"""
UK Office of the Registrar of Consultant Lobbyists scraper using Playwright
URL: https://orcl.my.site.com/CLR_Search
"""

import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_uk_orcl(firm_name: str) -> List[Dict]:
    """
    Scrape UK ORCL register for a given firm name.

    Args:
        firm_name: Name of the lobbying firm to search for

    Returns:
        List of dictionaries containing client information
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to search page
            await page.goto('https://orcl.my.site.com/CLR_Search', wait_until='networkidle')

            # Wait for the search form to load
            await page.wait_for_selector('input[type="text"]', timeout=10000)

            # Find the search input field and enter firm name
            search_input = await page.query_selector('input[placeholder*="Search"]')
            if not search_input:
                search_input = await page.query_selector('input[type="text"]')

            if search_input:
                await search_input.fill(firm_name)

                # Look for search button
                search_button = await page.query_selector('button:has-text("Search")')
                if not search_button:
                    search_button = await page.query_selector('input[type="submit"]')

                if search_button:
                    await search_button.click()

                    # Wait for results to load
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)

                    # Check if we have results
                    # Try to find the firm in results and click on it
                    firm_links = await page.query_selector_all(f'a:has-text("{firm_name}")')

                    if firm_links:
                        # Click on the first matching firm
                        await firm_links[0].click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)

                        # Now we should be on the firm's detail page
                        # Look for client information - typically in tables or lists

                        # Try to find client sections
                        client_sections = await page.query_selector_all('.client-info, .client-record, [class*="client"]')

                        if not client_sections:
                            # Try to find tables with client data
                            tables = await page.query_selector_all('table')

                            for table in tables:
                                # Check if this table contains client information
                                headers = await table.query_selector_all('th')
                                header_texts = [await h.inner_text() for h in headers]

                                if any('client' in h.lower() for h in header_texts):
                                    rows = await table.query_selector_all('tbody tr')

                                    for row in rows:
                                        cells = await row.query_selector_all('td')
                                        if cells:
                                            cell_texts = [await cell.inner_text() for cell in cells]

                                            # Try to extract client name and dates
                                            client_record = {
                                                'firm_name': firm_name,
                                                'firm_registration_number': '',
                                                'client_name': '',
                                                'client_registration_number': '',
                                                'start_date': '',
                                                'end_date': ''
                                            }

                                            # Map cell data to fields based on headers
                                            for i, header in enumerate(header_texts):
                                                if i < len(cell_texts):
                                                    if 'client' in header.lower() and 'name' in header.lower():
                                                        client_record['client_name'] = cell_texts[i].strip()
                                                    elif 'client' in header.lower():
                                                        client_record['client_name'] = cell_texts[i].strip()
                                                    elif 'start' in header.lower() or 'from' in header.lower():
                                                        client_record['start_date'] = cell_texts[i].strip()
                                                    elif 'end' in header.lower() or 'to' in header.lower():
                                                        client_record['end_date'] = cell_texts[i].strip()

                                            if client_record['client_name']:
                                                results.append(client_record)

                        # Also try to extract from divs or other elements
                        if not results:
                            content_divs = await page.query_selector_all('div[class*="content"], div[class*="detail"]')

                            for div in content_divs:
                                text = await div.inner_text()
                                # Parse text for client information
                                lines = text.split('\n')

                                current_client = None
                                for line in lines:
                                    line = line.strip()
                                    if line and not line.startswith('©'):
                                        # Look for patterns that indicate client names
                                        if 'client' in line.lower():
                                            if current_client:
                                                results.append(current_client)
                                            current_client = {
                                                'firm_name': firm_name,
                                                'firm_registration_number': '',
                                                'client_name': line,
                                                'client_registration_number': '',
                                                'start_date': '',
                                                'end_date': ''
                                            }
                                        elif current_client and any(month in line for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                                            # This might be a date
                                            if not current_client['start_date']:
                                                current_client['start_date'] = line
                                            else:
                                                current_client['end_date'] = line

                                if current_client:
                                    results.append(current_client)

        except Exception as e:
            print(f"Error scraping UK ORCL: {e}")
        finally:
            await browser.close()

    return results


def scrape(firm_name: str) -> List[Dict]:
    """
    Synchronous wrapper for the async scraper function.

    Args:
        firm_name: Name of the lobbying firm to search for

    Returns:
        List of dictionaries containing client information
    """
    return asyncio.run(scrape_uk_orcl(firm_name))


if __name__ == "__main__":
    # Test with FTI Consulting
    test_results = scrape("FTI Consulting")
    print(f"Found {len(test_results)} clients")
    for result in test_results:
        print(result)