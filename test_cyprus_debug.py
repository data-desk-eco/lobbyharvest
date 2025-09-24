"""Debug script to test Cyprus lobbying scraper with visible browser"""

import asyncio
from playwright.async_api import async_playwright


async def debug_cyprus():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible browser
        page = await browser.new_page()

        await page.goto('https://www.iaac.org.cy/iaac/iaac.nsf/table3_el/table3_el?openform')

        # Wait for user to see the page
        print("Page loaded. Check the content...")
        await asyncio.sleep(5)

        # Get all text content
        content = await page.content()
        print("\n--- Page Title ---")
        title = await page.title()
        print(title)

        # Get all table data
        all_rows = await page.query_selector_all('tr')
        print(f"\nFound {len(all_rows)} rows")

        # Print first 10 rows
        for i, row in enumerate(all_rows[:10]):
            cells = await row.query_selector_all('td')
            if cells:
                row_text = []
                for cell in cells:
                    text = await cell.inner_text()
                    row_text.append(text.strip())
                if any(row_text):
                    print(f"Row {i}: {row_text}")

        # Look for FTI or similar
        page_text = await page.inner_text('body')
        if 'FTI' in page_text.upper():
            print("\n!!! Found 'FTI' in page text")
        if 'ΕΦ.ΤΙ.ΑΪ' in page_text:
            print("\n!!! Found 'ΕΦ.ΤΙ.ΑΪ' in page text")

        input("Press Enter to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_cyprus())