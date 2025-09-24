import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def search_firm(page: Page, firm_name: str) -> bool:
    try:
        await page.goto("https://lobbyists.ag.gov.au/register")
        await page.wait_for_load_state("networkidle")

        search_input = page.locator('input[placeholder*="Search"]').first
        await search_input.fill(firm_name)
        await search_input.press("Enter")

        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        return True
    except Exception as e:
        logger.error(f"Error searching for firm: {e}")
        return False


async def extract_firm_details(page: Page) -> Dict[str, str]:
    firm_info = {}
    try:
        firm_link = page.locator('a[href*="/register/view"]').first
        await firm_link.click()
        await page.wait_for_load_state("networkidle")

        firm_info['firm_name'] = await page.locator('h1').text_content() or ""

        abn_element = page.locator('text=/ABN.*:/')
        if await abn_element.count() > 0:
            abn_text = await abn_element.text_content()
            firm_info['firm_abn'] = abn_text.split(':')[-1].strip() if abn_text else ""
        else:
            firm_info['firm_abn'] = ""

    except Exception as e:
        logger.error(f"Error extracting firm details: {e}")

    return firm_info


async def extract_clients(page: Page, firm_info: Dict[str, str]) -> List[Dict[str, str]]:
    clients = []
    try:
        clients_section = page.locator('text=/Current Clients|Former Clients/')

        if await clients_section.count() > 0:
            client_rows = page.locator('.table tbody tr, table tbody tr')
            count = await client_rows.count()

            for i in range(count):
                row = client_rows.nth(i)
                client_data = {
                    'firm_name': firm_info.get('firm_name', ''),
                    'firm_abn': firm_info.get('firm_abn', ''),
                    'client_name': '',
                    'client_abn': '',
                    'start_date': '',
                    'end_date': ''
                }

                cells = row.locator('td')
                cell_count = await cells.count()

                if cell_count >= 1:
                    client_text = await cells.first.text_content()
                    if client_text:
                        parts = client_text.strip().split('\n')
                        client_data['client_name'] = parts[0].strip()

                        for part in parts:
                            if 'ABN' in part:
                                abn_parts = part.split('ABN')
                                if len(abn_parts) > 1:
                                    client_data['client_abn'] = abn_parts[1].strip().lstrip(':').strip()

                if cell_count >= 2:
                    dates_text = await cells.nth(1).text_content()
                    if dates_text:
                        if 'to' in dates_text.lower():
                            date_parts = dates_text.split('to')
                            client_data['start_date'] = date_parts[0].strip()
                            client_data['end_date'] = date_parts[1].strip() if len(date_parts) > 1 else ''
                        else:
                            client_data['start_date'] = dates_text.strip()

                if client_data['client_name']:
                    clients.append(client_data)

    except Exception as e:
        logger.error(f"Error extracting clients: {e}")

    return clients


async def scrape_australia_lobbying(firm_name: str) -> List[Dict[str, str]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            if await search_firm(page, firm_name):
                firm_info = await extract_firm_details(page)
                clients = await extract_clients(page, firm_info)
                return clients
            else:
                logger.error(f"Failed to search for firm: {firm_name}")
                return []
        finally:
            await browser.close()


def scrape(firm_name: str) -> List[Dict[str, str]]:
    return asyncio.run(scrape_australia_lobbying(firm_name))