#!/usr/bin/env python3
"""
Comprehensive test of all lobbyharvest scrapers after fixes
"""

import sys
import time
from datetime import datetime
import traceback

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

def test_scraper(name, scraper_module, test_cases):
    """Test a scraper with multiple test cases"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print('-'*60)

    results_summary = []

    for firm_name, extra_args in test_cases:
        print(f"\n  Testing with: {firm_name}")
        try:
            start_time = time.time()

            # Call the appropriate scrape function
            if name == "Lobbyfacts" and extra_args:
                # Lobbyfacts needs URL
                results = lobbyfacts.scrape_lobbyfacts(firm_name, extra_args)
            elif hasattr(scraper_module, 'scrape'):
                results = scraper_module.scrape(firm_name)
            elif hasattr(scraper_module, 'scrape_' + name.lower().replace(' ', '_')):
                func_name = 'scrape_' + name.lower().replace(' ', '_')
                results = getattr(scraper_module, func_name)(firm_name)
            else:
                print(f"    ❌ No scrape function found")
                continue

            elapsed_time = time.time() - start_time

            if results:
                print(f"    ✅ Found {len(results)} results in {elapsed_time:.2f}s")
                # Show first result as sample
                if results:
                    sample = results[0]
                    print(f"       Sample: {sample.get('client_name', 'N/A')}")
                results_summary.append((firm_name, len(results), 'success'))
            else:
                print(f"    ⚠️  No results in {elapsed_time:.2f}s")
                results_summary.append((firm_name, 0, 'no_results'))

        except Exception as e:
            print(f"    ❌ ERROR: {str(e)[:100]}")
            results_summary.append((firm_name, 0, 'error'))
            if '--verbose' in sys.argv:
                traceback.print_exc()

    return results_summary

def main():
    print("="*60)
    print("COMPREHENSIVE SCRAPER TEST SUITE")
    print("="*60)

    # Test configurations with various firm names
    test_configs = [
        ("Lobbyfacts", lobbyfacts, [
            ("FTI Consulting Belgium", "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67"),
        ]),

        ("UK Lobbying", uk_lobbying, [
            ("FTI Consulting", None),
            ("Portland", None),
            ("Weber Shandwick", None),
        ]),

        ("UK ORCL", uk_orcl, [
            ("FTI Consulting", None),
            ("Portland", None),
        ]),

        ("Australian Lobbying", australia_lobbying, [
            ("FTI", None),
            ("Hawker Britton", None),
            ("Crosby Textor", None),
        ]),

        ("AU Foreign Influence", au_foreign_influence, [
            ("FTI", None),
            ("Hawker", None),
        ]),

        ("FARA", fara, [
            ("Akin Gump", None),
            ("Squire Patton", None),
            ("FTI", None),
        ]),

        ("French HATVP", french_hatvp, [
            ("Boury Tallon", None),
            ("Image Sept", None),
            ("FTI", None),
        ]),

        ("Austrian Lobbying", austrian_lobbying, [
            ("Schönherr", None),
            ("Wolf Theiss", None),
            ("FTI", None),
        ]),

        ("Cyprus Lobbying", cyprus_lobbying, [
            ("Zenox", None),
            ("FTI", None),
        ]),

        ("Italian Lobbying", italian_lobbying, [
            ("Cattaneo Zanetto", None),
            ("Reti", None),
            ("FTI", None),
        ]),
    ]

    # Run all tests
    all_results = {}
    for name, module, test_cases in test_configs:
        results = test_scraper(name, module, test_cases)
        all_results[name] = results

    # Print summary
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60)

    working_scrapers = []
    partial_scrapers = []
    broken_scrapers = []

    for scraper_name, results in all_results.items():
        success_count = sum(1 for _, _, status in results if status == 'success')
        total_count = len(results)

        print(f"\n{scraper_name}:")
        print(f"  Success rate: {success_count}/{total_count}")

        if success_count == total_count:
            working_scrapers.append(scraper_name)
            print(f"  Status: ✅ FULLY WORKING")
        elif success_count > 0:
            partial_scrapers.append(scraper_name)
            print(f"  Status: ⚠️  PARTIALLY WORKING")
        else:
            broken_scrapers.append(scraper_name)
            print(f"  Status: ❌ NOT WORKING")

        for firm, count, status in results:
            if status == 'success':
                print(f"    ✓ {firm}: {count} results")
            elif status == 'no_results':
                print(f"    - {firm}: no results")
            else:
                print(f"    ✗ {firm}: error")

    # Final statistics
    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    print(f"✅ Fully Working: {len(working_scrapers)}/10")
    if working_scrapers:
        print(f"   {', '.join(working_scrapers)}")

    print(f"⚠️  Partially Working: {len(partial_scrapers)}/10")
    if partial_scrapers:
        print(f"   {', '.join(partial_scrapers)}")

    print(f"❌ Not Working: {len(broken_scrapers)}/10")
    if broken_scrapers:
        print(f"   {', '.join(broken_scrapers)}")

    success_rate = (len(working_scrapers) + len(partial_scrapers) * 0.5) / 10 * 100
    print(f"\n📊 Overall Success Rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main()