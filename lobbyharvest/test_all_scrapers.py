#!/usr/bin/env python3
"""
Test all scrapers with real queries
"""
import json
import logging
from src.scrapers import lobbyfacts, uk_lobbying, australia_lobbying, fara

logging.basicConfig(level=logging.INFO)

def test_scraper(name, scrape_func, *args):
    """Test a scraper and report results"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    try:
        results = scrape_func(*args)
        if results:
            print(f"✓ Success: Found {len(results)} clients")
            print(f"Sample: {json.dumps(results[0], indent=2, default=str)}")
        else:
            print(f"✗ No results found")
        return results
    except Exception as e:
        print(f"✗ Error: {e}")
        return []

def main():
    print("Testing all lobbyharvest scrapers")
    print("="*60)

    all_results = {}

    # Test Lobbyfacts (requires URL)
    lobbyfacts_url = "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67"
    results = test_scraper(
        "Lobbyfacts.eu",
        lobbyfacts.scrape_lobbyfacts,
        "FTI Consulting Belgium",
        lobbyfacts_url
    )
    all_results['lobbyfacts'] = results

    # Test UK Lobbying
    results = test_scraper(
        "UK Lobbying Register",
        uk_lobbying.scrape,
        "FTI Consulting"
    )
    all_results['uk'] = results

    # Test Australian Lobbying
    results = test_scraper(
        "Australian Lobbying Register",
        australia_lobbying.scrape,
        "FTI Consulting"
    )
    all_results['australia'] = results

    # Test FARA
    results = test_scraper(
        "FARA (US)",
        fara.scrape_fara,
        "FTI Consulting"
    )
    all_results['fara'] = results

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    working_scrapers = []
    non_working_scrapers = []

    for name, results in all_results.items():
        if results:
            working_scrapers.append(f"{name}: {len(results)} clients")
        else:
            non_working_scrapers.append(name)

    print("\n✓ Working scrapers:")
    for scraper in working_scrapers:
        print(f"  - {scraper}")

    print("\n✗ Non-working scrapers (need JavaScript or different approach):")
    for scraper in non_working_scrapers:
        print(f"  - {scraper}")

    # Save all results
    with open('test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nResults saved to test_results.json")

if __name__ == "__main__":
    main()