import re
from datetime import datetime
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page
import click

def extract_rid_from_url(url: str) -> Optional[str]:
    match = re.search(r'rid=([^&]+)', url)
    return match.group(1) if match else None

def search_firm(page: Page, firm_name: str) -> Optional[str]:
    search_url = "https://www.lobbyfacts.eu/search/all"
    page.goto(search_url)
    page.wait_for_load_state("networkidle")

    search_input = page.locator('input[name="q"]')
    search_input.fill(firm_name)
    search_input.press("Enter")

    page.wait_for_load_state("networkidle")

    results = page.locator('.search-result-item a[href*="/datacard/"]')
    if results.count() > 0:
        first_result = results.first
        href = first_result.get_attribute("href")
        if href:
            return f"https://www.lobbyfacts.eu{href}"

    return None

def scrape_lobbyfacts(firm_name: str, url: Optional[str] = None) -> List[Dict[str, str]]:
    clients = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            if "Host system is missing dependencies" in str(e):
                click.echo("Browser dependencies missing. Please run: sudo playwright install-deps", err=True)
                click.echo("Or install manually: sudo apt-get install libgbm1", err=True)
                return clients
            raise

        page = browser.new_page()

        try:
            if not url:
                url = search_firm(page, firm_name)
                if not url:
                    click.echo(f"No results found for {firm_name}")
                    return clients

            page.goto(url)
            page.wait_for_load_state("networkidle")

            rid = extract_rid_from_url(url)

            clients_section = page.locator('h3:has-text("Clients for closed financial year")')

            if clients_section.count() > 0:
                clients_container = clients_section.locator('xpath=..').locator('..')

                client_items = clients_container.locator('.client-item, .list-group-item, li, div[class*="client"]')

                if client_items.count() == 0:
                    client_items = clients_container.locator('xpath=.//following-sibling::*[1]//a | .//following-sibling::*[1]//li')

                for i in range(client_items.count()):
                    client_item = client_items.nth(i)
                    client_text = client_item.text_content().strip()

                    if client_text:
                        client_data = {
                            "firm_name": firm_name,
                            "firm_registration_number": rid or "",
                            "client_name": client_text,
                            "client_registration_number": "",
                            "client_start_date": "",
                            "client_end_date": ""
                        }

                        date_match = re.search(r'(\d{4})', client_text)
                        if date_match:
                            year = date_match.group(1)
                            client_data["client_start_date"] = f"{year}-01-01"
                            client_data["client_end_date"] = f"{year}-12-31"
                            client_data["client_name"] = re.sub(r'\s*\d{4}\s*', '', client_text).strip()

                        clients.append(client_data)

            if not clients:
                table_rows = page.locator('table tr:has(td)')
                for i in range(table_rows.count()):
                    row = table_rows.nth(i)
                    cells = row.locator('td')
                    if cells.count() >= 2:
                        client_name = cells.first.text_content().strip()
                        if client_name and "client" in row.text_content().lower():
                            clients.append({
                                "firm_name": firm_name,
                                "firm_registration_number": rid or "",
                                "client_name": client_name,
                                "client_registration_number": "",
                                "client_start_date": "",
                                "client_end_date": ""
                            })

        except Exception as e:
            click.echo(f"Error scraping Lobbyfacts: {e}", err=True)
        finally:
            browser.close()

    return clients

def main(firm_name: str, url: Optional[str] = None) -> List[Dict[str, str]]:
    return scrape_lobbyfacts(firm_name, url)