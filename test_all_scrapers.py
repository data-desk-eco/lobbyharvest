#!/usr/bin/env python3
"""
Test all lobbyharvest scrapers with FTI Consulting
"""

import sys
import time
from datetime import datetime
import traceback

# Add the lobbyharvest directory to path
sys.path.insert(0, 'lobbyharvest')

from src.scrapers import (
    lobbyfacts,
    uk_lobbying,
    australia_lobbying,
    fara,
    uk_orcl,
    french_hatvp,
    austrian_lobbying,
    cyprus_lobbying,
    italian_lobbying,
    au_foreign_influence
)

def test_scraper(name, scraper_module, firm_name="FTI Consulting"):
    """Test a single scraper and return results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Firm: {firm_name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('-'*60)

    try:
        start_time = time.time()

        # Call the scrape function
        if hasattr(scraper_module, 'scrape'):
            results = scraper_module.scrape(firm_name)
        elif hasattr(scraper_module, 'scrape_' + name.lower().replace(' ', '_')):
            func_name = 'scrape_' + name.lower().replace(' ', '_')
            results = getattr(scraper_module, func_name)(firm_name)
        else:
            print(f"❌ No scrape function found in {name}")
            return None

        elapsed_time = time.time() - start_time

        # Print results
        if results:
            print(f"✅ SUCCESS - Found {len(results)} clients in {elapsed_time:.2f}s")

            # Show first 3 results as examples
            for i, result in enumerate(results[:3]):
                print(f"\n  Client {i+1}:")
                print(f"    Name: {result.get('client_name', 'N/A')}")
                print(f"    Registration: {result.get('client_registration_number', 'N/A')}")
                print(f"    Start: {result.get('start_date', 'N/A')}")
                print(f"    End: {result.get('end_date', 'N/A')}")

            if len(results) > 3:
                print(f"\n  ... and {len(results) - 3} more clients")
        else:
            print(f"⚠️  No results found (took {elapsed_time:.2f}s)")

        return {
            'name': name,
            'status': 'success' if results else 'no_results',
            'count': len(results) if results else 0,
            'time': elapsed_time,
            'sample': results[:3] if results else []
        }

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        if '--verbose' in sys.argv:
            traceback.print_exc()

        return {
            'name': name,
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__
        }

def main():
    """Test all scrapers"""
    print("="*60)
    print("LOBBYHARVEST SCRAPER TEST SUITE")
    print("="*60)

    # Define scrapers to test
    scrapers = [
        ("Lobbyfacts", lobbyfacts),
        ("UK Lobbying", uk_lobbying),
        ("Australian Lobbying", australia_lobbying),
        ("FARA", fara),
        ("UK ORCL", uk_orcl),
        ("French HATVP", french_hatvp),
        ("Austrian Lobbying", austrian_lobbying),
        ("Cyprus Lobbying", cyprus_lobbying),
        ("Italian Lobbying", italian_lobbying),
        ("AU Foreign Influence", au_foreign_influence)
    ]

    # Test each scraper
    results = []
    for name, module in scrapers:
        result = test_scraper(name, module)
        if result:
            results.append(result)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    successful = [r for r in results if r['status'] == 'success']
    no_results = [r for r in results if r['status'] == 'no_results']
    errors = [r for r in results if r['status'] == 'error']

    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['name']}: {r['count']} clients in {r['time']:.2f}s")

    if no_results:
        print(f"\n⚠️  No Results: {len(no_results)}")
        for r in no_results:
            print(f"   - {r['name']}: took {r['time']:.2f}s")

    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for r in errors:
            print(f"   - {r['name']}: {r['error_type']} - {r['error'][:50]}...")

    # Overall status
    print("\n" + "="*60)
    if len(successful) == len(results):
        print("🎉 ALL TESTS PASSED!")
    elif len(errors) == 0:
        print("✅ All scrapers ran without errors (some had no results)")
    else:
        print(f"⚠️  {len(errors)} scrapers failed - review errors above")

    return 0 if len(errors) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())