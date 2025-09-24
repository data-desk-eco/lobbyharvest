"""
Cyprus Lobbying Register scraper using Playwright
URL: https://www.iaac.org.cy/iaac/iaac.nsf/table3_el/table3_el?openform
"""

import asyncio
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_cyprus_lobbying(firm_name: str) -> List[Dict]:
    """
    Scrape Cyprus lobbying register for a given firm name.

    The Cyprus register has columns:
    - Number
    - Lobbying firm name
    - Type (φ.π. for individual, ν.π.ι.δ. for legal entity)
    - Registration date
    - Registration number
    - Areas of interest
    - Clients
    - Address
    - Phone
    - Email

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
            # Navigate to the Cyprus lobbying register
            await page.goto('https://www.iaac.org.cy/iaac/iaac.nsf/table3_el/table3_el?openform',
                          wait_until='domcontentloaded', timeout=30000)

            # Wait for content to load
            await asyncio.sleep(3)

            # Get all table rows
            all_rows = await page.query_selector_all('tr')

            for row in all_rows[1:]:  # Skip header row
                cells = await row.query_selector_all('td')

                if cells and len(cells) >= 7:  # Ensure we have enough columns
                    # Extract text from all cells
                    row_data = []
                    for cell in cells:
                        text = await cell.inner_text()
                        row_data.append(text.strip())

                    # Column mapping based on observed structure:
                    # 0: Number
                    # 1: Lobbying firm name
                    # 2: Type
                    # 3: Registration date
                    # 4: Registration number
                    # 5: Areas of interest
                    # 6: Clients
                    # 7: Address (if present)
                    # 8: Phone (if present)
                    # 9: Email (if present)

                    firm_in_row = row_data[1] if len(row_data) > 1 else ""
                    clients_text = row_data[6] if len(row_data) > 6 else ""

                    # Check if this row contains the firm we're looking for
                    if check_firm_match(firm_in_row, firm_name):
                        # Found our firm, extract client information
                        if clients_text:
                            # Clients are often separated by newlines or numbered
                            client_lines = clients_text.split('\n')

                            for client_line in client_lines:
                                # Clean up numbered items (e.g., "1. Client Name")
                                client_name = re.sub(r'^\d+\.\s*', '', client_line).strip()

                                if client_name and len(client_name) > 2:
                                    client_record = {
                                        'firm_name': firm_name,
                                        'firm_registration_number': row_data[4] if len(row_data) > 4 else '',
                                        'client_name': client_name,
                                        'client_registration_number': '',
                                        'start_date': normalize_date(row_data[3]) if len(row_data) > 3 else '',
                                        'end_date': ''
                                    }
                                    results.append(client_record)

        except Exception as e:
            print(f"Error scraping Cyprus lobbying register: {e}")
        finally:
            await browser.close()

    return results


def check_firm_match(text: str, firm_name: str) -> bool:
    """
    Check if the text matches the firm name, considering various formats and languages.

    Args:
        text: Text to check
        firm_name: Firm name to match against

    Returns:
        True if match found, False otherwise
    """
    text_lower = text.lower()
    firm_lower = firm_name.lower()

    # Direct match
    if firm_lower in text_lower:
        return True

    # Special cases for FTI Consulting
    if 'fti' in firm_lower:
        # Check for Greek variations
        greek_variations = ['εφ.τι.αϊ', 'εφτιαϊ', 'εφ.τι.αι', 'εφτιαι']
        for variation in greek_variations:
            if variation in text_lower:
                return True

    # Remove common suffixes and check again
    suffixes = ['consulting', 'ltd', 'limited', 'plc', 'inc', 'corporation', 'corp']
    firm_base = firm_lower
    for suffix in suffixes:
        firm_base = firm_base.replace(suffix, '').strip()

    if firm_base and firm_base in text_lower:
        return True

    return False


def normalize_date(date_str: str) -> str:
    """
    Normalize various date formats to YYYY-MM-DD format.

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format
    """
    if not date_str:
        return ''

    # Replace separators with /
    date_str = date_str.replace('.', '/').replace('-', '/')

    try:
        # Try DD/MM/YYYY format first (common in Cyprus)
        parts = date_str.split('/')
        if len(parts) == 3:
            if len(parts[0]) <= 2:  # DD/MM/YYYY
                day, month, year = parts
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:  # YYYY/MM/DD
                year, month, day = parts
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass

    return date_str


def scrape(firm_name: str) -> List[Dict]:
    """
    Synchronous wrapper for the async scraper function.

    Args:
        firm_name: Name of the lobbying firm to search for

    Returns:
        List of dictionaries containing client information
    """
    return asyncio.run(scrape_cyprus_lobbying(firm_name))


if __name__ == "__main__":
    # Test with various firms
    test_firms = ["FTI Consulting", "Zenox Public Affairs", "Cyprus Fiduciary Association"]

    for firm in test_firms:
        print(f"\n=== Testing with {firm} ===")
        test_results = scrape(firm)
        print(f"Found {len(test_results)} clients")
        for result in test_results:
            print(result)