#!/usr/bin/env python3
"""
Integration test harness for lobbyharvest scrapers
Tests each scraper with known firms and validates output
"""
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configurations for each scraper
TEST_CONFIGS = {
    'lobbyfacts': {
        'command': 'lobbyfacts-scrape',
        'test_firms': [
            {'name': 'FTI Consulting Belgium', 'args': ['--firm-name', 'FTI Consulting Belgium']},
            {'name': 'Weber Shandwick', 'args': ['--firm-name', 'Weber Shandwick']},
        ],
        'required_fields': ['firm_name', 'client_name', 'client_id', 'start_date', 'end_date']
    },
    'uk_lobbying': {
        'command': 'uk-lobbying-register',
        'test_firms': [
            {'name': 'FTI Consulting', 'args': ['FTI Consulting']},
            {'name': 'Portland', 'args': ['Portland']},
        ],
        'required_fields': ['firm_name', 'client_name']
    },
    'australia': {
        'command': 'australia',
        'test_firms': [
            {'name': 'FTI Consulting', 'args': ['--firm', 'FTI Consulting']},
            {'name': 'KPMG', 'args': ['--firm', 'KPMG']},
        ],
        'required_fields': ['firm_name', 'client_name', 'firm_abn']
    },
    'fara': {
        'command': 'fara-scrape',
        'test_firms': [
            {'name': 'FTI Government Affairs', 'args': ['FTI Government Affairs']},
            {'name': 'APCO', 'args': ['APCO']},
        ],
        'required_fields': ['firm_name', 'client_name', 'client_country']
    }
}


class ScraperTester:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.results = {}
        self.python_cmd = sys.executable

    def test_scraper(self, scraper_name: str, config: Dict) -> Dict[str, Any]:
        """Test a single scraper with multiple test cases"""
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing {scraper_name} scraper")
        logger.info(f"{'='*50}")

        scraper_results = {
            'name': scraper_name,
            'command': config['command'],
            'tests': [],
            'success': False,
            'total_time': 0
        }

        for test_case in config['test_firms']:
            result = self._run_test_case(scraper_name, config['command'], test_case, config.get('required_fields', []))
            scraper_results['tests'].append(result)
            scraper_results['total_time'] += result.get('duration', 0)

        # Determine overall success
        successful_tests = sum(1 for t in scraper_results['tests'] if t['success'])
        scraper_results['success'] = successful_tests > 0
        scraper_results['success_rate'] = successful_tests / len(scraper_results['tests']) if scraper_results['tests'] else 0

        return scraper_results

    def _run_test_case(self, scraper_name: str, command: str, test_case: Dict, required_fields: List[str]) -> Dict:
        """Run a single test case for a scraper"""
        logger.info(f"\nTesting with firm: {test_case['name']}")

        output_file = f"test_output_{scraper_name}_{test_case['name'].replace(' ', '_')}.json"
        cmd = [
            self.python_cmd,
            'main.py',
            command,
            *test_case['args'],
            '--format', 'json',
            '--output', output_file
        ]

        if command in ['uk-lobbying-register', 'australia']:
            # These commands have different argument structure
            if '--output' in cmd:
                idx = cmd.index('--output')
                cmd[idx] = '--output-file' if command == 'australia' else '--output'

        start_time = time.time()
        result = {
            'firm': test_case['name'],
            'success': False,
            'records': 0,
            'duration': 0,
            'error': None,
            'missing_fields': []
        }

        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd='lobbyharvest'
            )

            result['duration'] = time.time() - start_time
            result['stdout'] = process.stdout
            result['stderr'] = process.stderr

            if process.returncode == 0:
                # Check if output file was created
                output_path = Path('lobbyharvest') / output_file
                if output_path.exists():
                    with open(output_path, 'r') as f:
                        data = json.load(f)
                        result['records'] = len(data) if isinstance(data, list) else 0

                        # Validate required fields
                        if data and isinstance(data, list):
                            missing = set()
                            for record in data[:5]:  # Check first 5 records
                                for field in required_fields:
                                    if field not in record:
                                        missing.add(field)
                            result['missing_fields'] = list(missing)

                        result['success'] = result['records'] > 0 and not result['missing_fields']

                    # Clean up test file
                    output_path.unlink()
                else:
                    result['error'] = "Output file not created"

            else:
                result['error'] = f"Command failed with code {process.returncode}"
                if process.stderr:
                    result['error'] += f": {process.stderr}"

        except subprocess.TimeoutExpired:
            result['error'] = f"Timeout after {self.timeout} seconds"
        except Exception as e:
            result['error'] = str(e)

        # Log result
        if result['success']:
            logger.info(f"✓ SUCCESS: Found {result['records']} records in {result['duration']:.2f}s")
        else:
            logger.error(f"✗ FAILED: {result['error']}")
            if result['stderr']:
                logger.error(f"  stderr: {result['stderr'][:200]}")

        return result

    def run_all_tests(self) -> Dict:
        """Run tests for all configured scrapers"""
        logger.info("Starting comprehensive scraper tests")

        for scraper_name, config in TEST_CONFIGS.items():
            self.results[scraper_name] = self.test_scraper(scraper_name, config)

        return self.results

    def generate_report(self) -> str:
        """Generate a summary report of test results"""
        report = ["\n" + "="*60]
        report.append("SCRAPER TEST SUMMARY REPORT")
        report.append("="*60)

        total_scrapers = len(self.results)
        successful_scrapers = sum(1 for r in self.results.values() if r['success'])

        report.append(f"\nOverall: {successful_scrapers}/{total_scrapers} scrapers working")
        report.append("")

        for scraper_name, result in self.results.items():
            status = "✓" if result['success'] else "✗"
            report.append(f"{status} {scraper_name.upper()}")
            report.append(f"  Success rate: {result['success_rate']*100:.0f}%")
            report.append(f"  Total time: {result['total_time']:.2f}s")

            for test in result['tests']:
                test_status = "✓" if test['success'] else "✗"
                report.append(f"    {test_status} {test['firm']}: ", end="")
                if test['success']:
                    report.append(f"{test['records']} records in {test['duration']:.2f}s")
                else:
                    report.append(f"Failed - {test.get('error', 'Unknown error')}")

            report.append("")

        return "\n".join(report)


def main():
    """Main test runner"""
    # Check if we're in the right directory
    if not Path('lobbyharvest/main.py').exists():
        logger.error("Please run this script from the project root directory")
        sys.exit(1)

    # Check for required dependencies
    try:
        subprocess.run([sys.executable, '-c', 'import playwright'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        logger.error("Playwright not installed. Run: uv add playwright")
        sys.exit(1)

    # Run tests
    tester = ScraperTester(timeout=60)
    results = tester.run_all_tests()

    # Generate and print report
    report = tester.generate_report()
    print(report)

    # Save detailed results
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Detailed results saved to test_results.json")

    # Exit with appropriate code
    success_count = sum(1 for r in results.values() if r['success'])
    sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    main()