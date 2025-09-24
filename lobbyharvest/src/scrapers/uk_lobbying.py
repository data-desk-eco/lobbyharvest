import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page


async def search_firm(page: Page, firm_name: str) -> None:
    await page.goto("https://lobbying-register.uk/")

    search_input = page.locator("input[type='search'], input[placeholder*='Search'], #search")
    await search_input.wait_for(timeout=10000)
    await search_input.fill(firm_name)
    await search_input.press("Enter")

    await page.wait_for_load_state("networkidle", timeout=10000)
    await asyncio.sleep(2)


async def extract_firm_details(page: Page) -> Dict[str, Optional[str]]:
    firm_data = {"firm_name": None, "firm_registration_number": None}

    try:
        firm_name_elem = page.locator("h1, h2").filter(has_text=lambda text: text and len(text) > 0).first
        if await firm_name_elem.count() > 0:
            firm_data["firm_name"] = await firm_name_elem.text_content()
            firm_data["firm_name"] = firm_data["firm_name"].strip() if firm_data["firm_name"] else None

        reg_number_elem = page.locator("text=/Registration [Nn]umber|Reg\\.? [Nn]o\\.?/i").first
        if await reg_number_elem.count() > 0:
            parent = reg_number_elem.locator("..")
            text = await parent.text_content()
            if text:
                import re
                match = re.search(r'[A-Z0-9]{6,}', text)
                if match:
                    firm_data["firm_registration_number"] = match.group(0)
    except:
        pass

    return firm_data


async def extract_clients(page: Page) -> List[Dict[str, Optional[str]]]:
    clients = []

    client_sections = page.locator("div, section, article").filter(
        has_text=lambda text: "client" in text.lower() if text else False
    )

    for i in range(await client_sections.count()):
        section = client_sections.nth(i)
        text = await section.text_content()
        if not text:
            continue

        lines = text.split('\n')
        current_client = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if not current_client.get("client_name") and len(line) > 2 and not any(
                keyword in line.lower() for keyword in ["client", "period", "date", "from", "to"]
            ):
                current_client["client_name"] = line

            import re
            date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
            dates = re.findall(date_pattern, line)
            if dates:
                if not current_client.get("start_date"):
                    current_client["start_date"] = dates[0]
                if len(dates) > 1:
                    current_client["end_date"] = dates[1]

            reg_pattern = r'\b[A-Z0-9]{6,}\b'
            reg_match = re.search(reg_pattern, line)
            if reg_match and not current_client.get("client_registration_number"):
                current_client["client_registration_number"] = reg_match.group(0)

            if current_client.get("client_name") and (
                current_client.get("start_date") or current_client.get("client_registration_number")
            ):
                if current_client not in clients:
                    clients.append(current_client.copy())
                current_client = {}

    return clients


async def scrape_uk_lobbying(firm_name: str) -> List[Dict[str, Optional[str]]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        results = []

        try:
            await search_firm(page, firm_name)

            search_results = page.locator("a").filter(has_text=lambda text: firm_name.lower() in text.lower() if text else False)
            if await search_results.count() > 0:
                await search_results.first.click()
                await page.wait_for_load_state("networkidle", timeout=10000)

            firm_data = await extract_firm_details(page)
            clients = await extract_clients(page)

            for client in clients:
                result = {
                    "firm_name": firm_data.get("firm_name") or firm_name,
                    "firm_registration_number": firm_data.get("firm_registration_number"),
                    "client_name": client.get("client_name"),
                    "client_registration_number": client.get("client_registration_number"),
                    "start_date": client.get("start_date"),
                    "end_date": client.get("end_date")
                }
                results.append(result)

            if not results and firm_data.get("firm_name"):
                results.append({
                    "firm_name": firm_data.get("firm_name") or firm_name,
                    "firm_registration_number": firm_data.get("firm_registration_number"),
                    "client_name": None,
                    "client_registration_number": None,
                    "start_date": None,
                    "end_date": None
                })

        except Exception as e:
            print(f"Error scraping UK Lobbying Register: {e}")

        finally:
            await browser.close()

        return results


def scrape(firm_name: str) -> List[Dict[str, Optional[str]]]:
    return asyncio.run(scrape_uk_lobbying(firm_name))