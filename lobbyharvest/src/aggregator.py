#!/usr/bin/env python3
import asyncio
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .utils.normalize import merge_client_records, validate_record

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LobbyingAggregator:
    """Aggregate lobbying data from multiple sources"""

    def __init__(self, output_dir: Path = Path("./output")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.scrapers = []
        self._load_scrapers()

    def _load_scrapers(self):
        """Dynamically load available scrapers"""
        scraper_modules = [
            'lobbyfacts',
            'uk_lobbying',
            'australia_lobbying',
            'fara',
            'irish_lobbying',
            'opensecrets'
        ]

        for module_name in scraper_modules:
            try:
                module = __import__(f'src.scrapers.{module_name}', fromlist=['scrape'])
                if hasattr(module, 'scrape'):
                    self.scrapers.append({
                        'name': module_name,
                        'func': module.scrape
                    })
                    logger.info(f"Loaded scraper: {module_name}")
            except ImportError as e:
                logger.debug(f"Scraper {module_name} not available: {e}")

    async def aggregate(self, firm_name: str) -> List[Dict]:
        """Run all scrapers and aggregate results"""
        all_results = []
        tasks = []

        for scraper in self.scrapers:
            logger.info(f"Running {scraper['name']} scraper for {firm_name}")
            try:
                # Check if scraper is async
                if asyncio.iscoroutinefunction(scraper['func']):
                    task = scraper['func'](firm_name)
                    tasks.append(task)
                else:
                    # Run sync scrapers in executor
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(None, scraper['func'], firm_name)
                    tasks.append(task)
            except Exception as e:
                logger.error(f"Error with {scraper['name']}: {e}")

        # Gather all results
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for scraper, result in zip(self.scrapers, results):
                if isinstance(result, Exception):
                    logger.error(f"Scraper {scraper['name']} failed: {result}")
                elif result:
                    all_results.extend(result)
                    logger.info(f"{scraper['name']} returned {len(result)} records")

        # Merge and validate
        valid_results = [r for r in all_results if validate_record(r)]
        merged_results = merge_client_records(valid_results)

        logger.info(f"Total unique records: {len(merged_results)}")
        return merged_results

    def save_results(self, results: List[Dict], firm_name: str, format: str = 'csv'):
        """Save aggregated results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_firm_name = firm_name.replace(' ', '_').replace('/', '_')

        if format == 'csv':
            filename = self.output_dir / f"{safe_firm_name}_{timestamp}.csv"
            with open(filename, 'w', newline='') as f:
                if results:
                    fieldnames = list(results[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)
            logger.info(f"Saved CSV to {filename}")

        elif format == 'json':
            filename = self.output_dir / f"{safe_firm_name}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Saved JSON to {filename}")

        return filename

def run_aggregator(firm_name: str, output_format: str = 'csv') -> Path:
    """Main entry point for aggregation"""
    aggregator = LobbyingAggregator()

    # Run async aggregation
    results = asyncio.run(aggregator.aggregate(firm_name))

    # Save results
    output_file = aggregator.save_results(results, firm_name, output_format)

    return output_file