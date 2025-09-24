"""
French HATVP Register scraper using Playwright
URL: https://www.hatvp.fr/le-repertoire/
"""

import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright, Page, Browser
import json


async def navigate_to_detail_page(page: Page, firm_name: str) -> bool:
    """
    Navigate to the detail page for a firm using the search autocomplete.

    Args:
        page: Playwright page object
        firm_name: Name of the lobbying firm to search for

    Returns:
        True if successfully navigated to detail page, False otherwise
    """
    try:
        # Navigate to HATVP repertoire page
        await page.goto('https://www.hatvp.fr/le-repertoire/', wait_until='domcontentloaded')

        # Wait for the page to fully load
        await asyncio.sleep(3)

        # Find the search input by ID
        search_input = await page.wait_for_selector('#search', timeout=10000)

        if search_input:
            # Type the firm name to trigger autocomplete
            await search_input.type(firm_name, delay=100)

            # Wait for autocomplete suggestions to appear
            await asyncio.sleep(2)

            # Look for autocomplete suggestions
            suggestions = await page.query_selector_all('.tt-suggestion')

            if suggestions:
                # Find the most relevant suggestion
                for suggestion in suggestions:
                    suggestion_text = await suggestion.inner_text()
                    # Check if this suggestion contains our firm name (case insensitive)
                    if firm_name.lower() in suggestion_text.lower():
                        # Click on this suggestion
                        await suggestion.click()
                        # Wait for navigation to complete
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)

                        # Check if we're on a detail page by looking for URL pattern
                        current_url = page.url
                        if 'fiche-organisation' in current_url or 'organisation=' in current_url:
                            return True
                        break
            else:
                # If no autocomplete, try pressing Enter
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)

                # Check if we navigated somewhere
                if page.url != 'https://www.hatvp.fr/le-repertoire/':
                    return True

        return False

    except Exception as e:
        print(f"Error navigating to detail page: {e}")
        return False


async def extract_clients_from_detail_page(page: Page, firm_name: str) -> List[Dict]:
    """
    Extract client information from a firm's detail page.

    Args:
        page: Playwright page object on the detail page
        firm_name: Name of the lobbying firm

    Returns:
        List of dictionaries containing client information
    """
    results = []

    try:
        # Wait for content to load
        await page.wait_for_selector('body', timeout=5000)

        # Extract visible text from the page
        all_text = await page.inner_text('body')

        # Split text into lines and clean them
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]

        # Look for client listings - they typically start with bullet points
        for i, line in enumerate(lines):
            # Check if this line contains a client name
            # Clients are typically listed with bullet points (•) and may have "Voir la fiche" link
            if line.startswith('• '):
                # Extract the client name, removing the bullet and any "Voir la fiche" text
                client_name = line[2:].strip()  # Remove bullet point
                client_name = client_name.replace(' Voir la fiche', '').strip()

                # Skip if this is not a valid client name
                if not client_name:
                    continue

                # Skip section headers and metadata
                skip_words = ['identité', 'fonction', 'niveau', 'secteur', 'domaine',
                              'président', 'directeur', 'consultant', 'associé', 'local',
                              'national', 'economie', 'finances', 'environnement', 'numérique',
                              'santé', 'transport', 'energie', 'agriculture']
                if any(skip in client_name.lower() for skip in skip_words):
                    continue

                # Skip single words (likely section headers)
                if ' ' not in client_name and client_name.upper() != client_name:
                    continue

                # Create client record
                client_record = {
                    'firm_name': firm_name,
                    'firm_registration_number': '',
                    'client_name': client_name,
                    'client_registration_number': '',
                    'start_date': '',
                    'end_date': ''
                }

                # Only add if we haven't seen this client yet
                if not any(r['client_name'] == client_record['client_name'] for r in results):
                    results.append(client_record)

        # Alternative approach: look for clients in specific sections
        if not results:
            in_client_section = False

            for line in lines:
                line_lower = line.lower()

                # Check if we're entering a clients section
                if 'actions de représentation' in line_lower or 'clients' in line_lower or 'mandants' in line_lower:
                    in_client_section = True
                    continue

                # Check if we're leaving the clients section
                if in_client_section and any(section in line_lower for section in ['rapport', 'déclaration', 'informations']):
                    in_client_section = False
                    continue

                # If we're in the client section and the line looks like a company name
                if in_client_section and line:
                    # Basic validation for company names
                    if (len(line) > 3 and len(line) < 200 and
                        not line.lower().startswith(('http', 'www')) and
                        not '@' in line and
                        not line.isdigit() and
                        not any(skip in line_lower for skip in ['téléphone', 'email', 'adresse', 'contact'])):

                        # Check if it contains typical company indicators
                        company_indicators = ['SAS', 'SARL', 'SA ', 'EURL', 'SNC', 'ASSOCIATION',
                                            'FONDATION', 'GROUPE', 'INSTITUT', 'FEDERATION',
                                            'SYNDICAT', 'UNION', 'SOCIETE', 'MUTUELLE']

                        if any(indicator in line.upper() for indicator in company_indicators):
                            client_record = {
                                'firm_name': firm_name,
                                'firm_registration_number': '',
                                'client_name': line,
                                'client_registration_number': '',
                                'start_date': '',
                                'end_date': ''
                            }

                            if not any(r['client_name'] == client_record['client_name'] for r in results):
                                results.append(client_record)

        print(f"Extracted {len(results)} unique clients")

    except Exception as e:
        print(f"Error extracting clients: {e}")

    return results


async def scrape_french_hatvp(firm_name: str) -> List[Dict]:
    """
    Scrape French HATVP register for a given firm name.

    Args:
        firm_name: Name of the lobbying firm to search for

    Returns:
        List of dictionaries containing client information
    """
    results = []
    browser = None

    try:
        async with async_playwright() as p:
            # Launch browser with options for better stability
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            # Navigate to the detail page
            if await navigate_to_detail_page(page, firm_name):
                print(f"Successfully navigated to detail page for {firm_name}")
                print(f"Current URL: {page.url}")

                # Extract client information
                results = await extract_clients_from_detail_page(page, firm_name)

                if results:
                    print(f"Found {len(results)} clients for {firm_name}")
                else:
                    print(f"No clients found for {firm_name} on detail page")
            else:
                print(f"Could not find detail page for {firm_name}")

            await browser.close()

    except Exception as e:
        print(f"Error in main scraping function: {e}")
        if browser:
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