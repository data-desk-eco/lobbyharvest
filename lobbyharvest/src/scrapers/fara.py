import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, Page, TimeoutError


class FARAScraper:
    BASE_URL = "https://efile.fara.gov/ords/fara/f?p=1381:200"

    def __init__(self):
        self.results = []

    async def scrape(self, firm_name: str) -> List[Dict[str, Optional[str]]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await self._navigate_to_search(page)
                await self._perform_search(page, firm_name)
                await self._extract_registration_data(page, firm_name)
            finally:
                await browser.close()

        return self.results

    async def _navigate_to_search(self, page: Page):
        await page.goto(self.BASE_URL)
        await page.wait_for_load_state('networkidle')

    async def _perform_search(self, page: Page, firm_name: str):
        search_field = page.locator('input[name="P200_SEARCH"]')
        await search_field.fill(firm_name)

        await page.press('input[name="P200_SEARCH"]', 'Enter')

        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

    async def _extract_registration_data(self, page: Page, firm_name: str):
        rows = page.locator('table.t-Report-report tbody tr')
        row_count = await rows.count()

        if row_count == 0:
            return

        for i in range(row_count):
            row = rows.nth(i)

            reg_link = row.locator('td:nth-child(2) a')
            if await reg_link.count() > 0:
                reg_number = await reg_link.inner_text()
                reg_number = reg_number.strip()

                await reg_link.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)

                await self._extract_client_info(page, firm_name, reg_number)

                await page.go_back()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)

    async def _extract_client_info(self, page: Page, firm_name: str, reg_number: str):
        try:
            exhibits_link = page.locator('a:has-text("Exhibits")')
            if await exhibits_link.count() > 0:
                await exhibits_link.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)

            exhibit_rows = page.locator('table.t-Report-report tbody tr')
            exhibit_count = await exhibit_rows.count()

            for i in range(min(exhibit_count, 10)):
                row = exhibit_rows.nth(i)

                link = row.locator('a')
                if await link.count() > 0:
                    link_text = await link.inner_text()
                    if 'Exhibit' in link_text or 'AB' in link_text:
                        await link.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(1)

                        await self._parse_exhibit_page(page, firm_name, reg_number)

                        await page.go_back()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(1)

        except TimeoutError:
            pass

    async def _parse_exhibit_page(self, page: Page, firm_name: str, reg_number: str):
        page_text = await page.content()

        client_patterns = [
            r'Foreign Principal[:\s]+([^<\n]+)',
            r'Name of Foreign Principal[:\s]+([^<\n]+)',
            r'Client[:\s]+([^<\n]+)',
            r'Name of Client[:\s]+([^<\n]+)'
        ]

        country_patterns = [
            r'Country[:\s]+([^<\n]+)',
            r'Principal Country[:\s]+([^<\n]+)',
            r'Country/Region[:\s]+([^<\n]+)'
        ]

        date_patterns = [
            r'Date of Registration[:\s]+([^<\n]+)',
            r'Effective Date[:\s]+([^<\n]+)',
            r'Date Filed[:\s]+([^<\n]+)'
        ]

        client_name = None
        for pattern in client_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                client_name = match.group(1).strip()
                client_name = re.sub(r'<[^>]+>', '', client_name)
                if client_name and len(client_name) > 2:
                    break

        if not client_name:
            labels = page.locator('span.t-Form-label:has-text("Foreign Principal"), span.t-Form-label:has-text("Name of Foreign Principal")')
            if await labels.count() > 0:
                label = labels.first
                parent = label.locator('..')
                text_element = parent.locator('span.display_only, div.t-Form-inputContainer')
                if await text_element.count() > 0:
                    client_name = await text_element.inner_text()
                    client_name = client_name.strip()

        client_country = None
        for pattern in country_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                client_country = match.group(1).strip()
                client_country = re.sub(r'<[^>]+>', '', client_country)
                if client_country and len(client_country) > 1:
                    break

        start_date = None
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                date_str = re.sub(r'<[^>]+>', '', date_str)
                start_date = self._parse_date(date_str)
                if start_date:
                    break

        if client_name:
            self.results.append({
                'firm_name': firm_name,
                'firm_registration_number': reg_number,
                'client_name': client_name,
                'client_country': client_country,
                'start_date': start_date,
                'end_date': None
            })

    def _parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None

        date_formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%m-%d-%Y'
        ]

        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return date_str


def scrape_fara(firm_name: str) -> List[Dict[str, Optional[str]]]:
    scraper = FARAScraper()
    return asyncio.run(scraper.scrape(firm_name))