#!/usr/bin/env python3
"""
Test scrapers with targeted queries for each site
"""

import sys
import asyncio
sys.path.insert(0, 'lobbyharvest')

from src.scrapers import (
    lobbyfacts,
    uk_lobbying,
    uk_orcl,
    cyprus_lobbying
)

print("="*60)
print("TARGETED SCRAPER TESTS")
print("="*60)

# Test 1: Lobbyfacts with direct URL
print("\n1. Testing Lobbyfacts with direct URL...")
print("-"*40)
try:
    results = lobbyfacts.scrape_lobbyfacts(
        'FTI Consulting Belgium',
        'https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67'
    )
    print(f"✅ Found {len(results)} clients")
    if results:
        print(f"   Sample clients: {', '.join([r['client_name'] for r in results[:3]])}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: UK ORCL
print("\n2. Testing UK ORCL...")
print("-"*40)
try:
    results = uk_orcl.scrape('FTI Consulting')
    print(f"✅ Found {len(results)} clients")
    if results:
        print(f"   Sample clients: {', '.join([r['client_name'] for r in results[:3]])}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Cyprus with specific firm
print("\n3. Testing Cyprus Lobbying...")
print("-"*40)
try:
    # Try with a Cyprus-specific firm first
    results = cyprus_lobbying.scrape('Zenox')
    if not results:
        # Try with FTI
        results = cyprus_lobbying.scrape('FTI')
    print(f"{'✅' if results else '⚠️'} Found {len(results)} clients")
    if results:
        print(f"   Sample clients: {', '.join([r['client_name'] for r in results[:3]])}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: UK Lobbying with different search
print("\n4. Testing UK Lobbying Register...")
print("-"*40)
try:
    results = uk_lobbying.scrape('Weber')
    if not results:
        results = uk_lobbying.scrape('Portland')
    print(f"{'✅' if results else '⚠️'} Found {len(results)} clients")
    if results:
        print(f"   Sample clients: {', '.join([r['client_name'] for r in results[:3]])}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)