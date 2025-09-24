"""
French HATVP Register scraper using Playwright
URL: https://www.hatvp.fr/
"""

import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright


async def scrape_french_hatvp(firm_name: str) -> List[Dict]:
    """
    Scrape French HATVP register for a given firm name.

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
            # Navigate to HATVP search page
            await page.goto('https://www.hatvp.fr/le-repertoire/', wait_until='networkidle')

            # Wait for the search interface to load
            await page.wait_for_selector('input[type="text"], input[type="search"]', timeout=10000)

            # Find the search input field
            search_input = await page.query_selector('input[placeholder*="Rechercher"]')
            if not search_input:
                search_input = await page.query_selector('input[type="search"]')
            if not search_input:
                search_input = await page.query_selector('input[type="text"]')

            if search_input:
                await search_input.fill(firm_name)
                await page.keyboard.press('Enter')

                # Wait for results to load
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(3)

                # Look for results
                # Try to find firm in results
                firm_elements = await page.query_selector_all(f'a:has-text("{firm_name}"), div:has-text("{firm_name}")')

                for element in firm_elements:
                    # Check if this is a clickable link to firm details
                    tag_name = await element.evaluate('el => el.tagName')
                    if tag_name == 'A':
                        await element.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)

                        # Now on firm detail page, look for client information
                        # French sites often use "mandants" for clients
                        client_sections = await page.query_selector_all('.mandant, .client, [class*="mandant"], [class*="client"]')

                        if not client_sections:
                            # Try to find in tables
                            tables = await page.query_selector_all('table')
                            for table in tables:
                                rows = await table.query_selector_all('tr')
                                for row in rows:
                                    text = await row.inner_text()
                                    # Look for client-related keywords in French
                                    if any(keyword in text.lower() for keyword in ['mandant', 'client', 'représente']):
                                        cells = await row.query_selector_all('td')
                                        if cells and len(cells) > 0:
                                            client_name = await cells[0].inner_text()
                                            client_record = {
                                                'firm_name': firm_name,
                                                'firm_registration_number': '',
                                                'client_name': client_name.strip(),
                                                'client_registration_number': '',
                                                'start_date': '',
                                                'end_date': ''
                                            }

                                            # Try to extract dates if available
                                            if len(cells) > 1:
                                                date_text = await cells[1].inner_text()
                                                if '/' in date_text or '-' in date_text:
                                                    dates = date_text.split('-')
                                                    if len(dates) == 2:
                                                        client_record['start_date'] = dates[0].strip()
                                                        client_record['end_date'] = dates[1].strip()
                                                    else:
                                                        client_record['start_date'] = date_text.strip()

                                            if client_record['client_name']:
                                                results.append(client_record)

                        # Also try to extract from divs
                        if not results:
                            content_divs = await page.query_selector_all('div.content, div.detail, article')
                            for div in content_divs:
                                text = await div.inner_text()
                                # Look for sections mentioning clients/mandants
                                lines = text.split('\n')
                                in_client_section = False

                                for line in lines:
                                    line = line.strip()
                                    if any(keyword in line.lower() for keyword in ['mandant', 'client']):
                                        in_client_section = True
                                    elif in_client_section and line and not any(skip in line.lower() for skip in ['contact', 'adresse', 'téléphone']):
                                        # This might be a client name
                                        client_record = {
                                            'firm_name': firm_name,
                                            'firm_registration_number': '',
                                            'client_name': line,
                                            'client_registration_number': '',
                                            'start_date': '',
                                            'end_date': ''
                                        }
                                        results.append(client_record)
                                    elif line == '' or any(section in line.lower() for section in ['activité', 'secteur', 'domaine']):
                                        in_client_section = False

                        # Go back to continue searching for more firms
                        await page.go_back()
                        await page.wait_for_load_state('networkidle')

        except Exception as e:
            print(f"Error scraping French HATVP: {e}")
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
    return asyncio.run(scrape_french_hatvp(firm_name))


if __name__ == "__main__":
    # Test with FTI
    test_results = scrape("FTI")
    print(f"Found {len(test_results)} clients")
    for result in test_results:
        print(result)