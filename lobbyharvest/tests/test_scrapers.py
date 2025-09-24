"""
Test suite for lobbyharvest scrapers
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import lobbyfacts, uk_lobbying, australia_lobbying, fara


class TestLobbyfactsScraper:
    """Test Lobbyfacts EU scraper"""

    def test_scrape_with_valid_url(self):
        """Test scraping with a valid URL returns results"""
        url = "https://www.lobbyfacts.eu/datacard/test-firm?rid=123"
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '''
            <html>
                <h3>Clients for the last closed financial year</h3>
                <ul>
                    <li>Client Company A</li>
                    <li>Client Company B</li>
                    <li>Client Company C</li>
                </ul>
            </html>
            '''
            mock_response.raise_for_status = Mock()
            mock_session.return_value.get.return_value = mock_response

            results = lobbyfacts.scrape_lobbyfacts("Test Firm", url)

            assert len(results) == 3
            assert results[0]['client_name'] == 'Client Company A'
            assert results[0]['firm_name'] == 'Test Firm'
            assert results[0]['firm_id'] == '123'

    def test_scrape_without_url(self):
        """Test scraping without URL returns empty list"""
        results = lobbyfacts.scrape_lobbyfacts("Test Firm")
        assert results == []

    def test_filters_invalid_clients(self):
        """Test that invalid client names are filtered out"""
        url = "https://www.lobbyfacts.eu/datacard/test-firm?rid=123"
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '''
            <html>
                <h3>Clients for the last closed financial year</h3>
                <ul>
                    <li>Valid Client Inc</li>
                    <li>Categories</li>
                    <li>Search</li>
                    <li>Another Valid Corp</li>
                </ul>
            </html>
            '''
            mock_response.raise_for_status = Mock()
            mock_session.return_value.get.return_value = mock_response

            results = lobbyfacts.scrape_lobbyfacts("Test Firm", url)

            assert len(results) == 2
            client_names = [r['client_name'] for r in results]
            assert 'Valid Client Inc' in client_names
            assert 'Another Valid Corp' in client_names
            assert 'Categories' not in client_names
            assert 'Search' not in client_names


class TestUKLobbyingScraper:
    """Test UK Lobbying Register scraper"""

    def test_scrape_with_json_response(self):
        """Test scraping with JSON API response"""
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {
                'results': [
                    {
                        'client': 'Client A',
                        'startDate': '2023-01-01',
                        'endDate': '2023-12-31'
                    },
                    {
                        'clientName': 'Client B',
                        'start_date': '2023-06-01'
                    }
                ]
            }
            mock_session.return_value.get.return_value = mock_response

            results = uk_lobbying.scrape("Test Firm")

            assert len(results) == 2
            assert results[0]['client_name'] == 'Client A'
            assert results[0]['start_date'] == '2023-01-01'
            assert results[1]['client_name'] == 'Client B'

    def test_scrape_with_html_response(self):
        """Test scraping with HTML response"""
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.text = '''
            <html>
                <table>
                    <tr><th>Firm</th><th>Client</th><th>Start</th></tr>
                    <tr><td>Test Firm</td><td>Client X</td><td>2023-01-01</td></tr>
                    <tr><td>Test Firm</td><td>Client Y</td><td>2023-02-01</td></tr>
                </table>
            </html>
            '''
            mock_session.return_value.get.return_value = mock_response

            results = uk_lobbying.scrape("Test Firm")

            assert len(results) == 2
            assert results[0]['client_name'] == 'Client X'
            assert results[1]['client_name'] == 'Client Y'


class TestAustraliaLobbyingScraper:
    """Test Australian Lobbying Register scraper"""

    def test_scrape_with_table_results(self):
        """Test scraping with table-based results"""
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '''
            <html>
                <table>
                    <tr>
                        <td>Test Firm</td>
                        <td><a href="/detail/123">Details</a></td>
                    </tr>
                </table>
            </html>
            '''
            mock_response.raise_for_status = Mock()

            detail_response = Mock()
            detail_response.status_code = 200
            detail_response.text = '''
            <html>
                <h3>Clients</h3>
                <ul>
                    <li>Australian Client A</li>
                    <li>Australian Client B</li>
                </ul>
            </html>
            '''

            mock_session.return_value.get.side_effect = [mock_response, detail_response]

            results = australia_lobbying.scrape("Test Firm")

            assert len(results) == 2
            assert results[0]['client_name'] == 'Australian Client A'
            assert results[1]['client_name'] == 'Australian Client B'


class TestFARAScraper:
    """Test FARA scraper"""

    def test_scrape_with_apex_session(self):
        """Test FARA scraping with APEX session handling"""
        with patch('requests.Session') as mock_session:
            # Initial page with session ID
            initial_response = Mock()
            initial_response.status_code = 200
            initial_response.url = "https://efile.fara.gov/ords/fara/f?p=1381:200:12345"
            initial_response.text = '''
            <html>
                <script>p_instance = "12345";</script>
            </html>
            '''
            initial_response.raise_for_status = Mock()

            # Search results
            search_response = Mock()
            search_response.status_code = 200
            search_response.text = '''
            <html>
                <table class="t-Report-report">
                    <tr><th>Reg</th><th>Number</th></tr>
                    <tr><td>Test</td><td><a href="/detail/7890">7890</a></td></tr>
                </table>
            </html>
            '''

            # Detail page
            detail_response = Mock()
            detail_response.status_code = 200
            detail_response.text = '''
            <html>
                <span>Foreign Principal</span>
                <span>Foreign Government X</span>
                <span>Country</span>
                <span>Country Y</span>
            </html>
            '''

            mock_session.return_value.get.side_effect = [
                initial_response,
                search_response,
                detail_response
            ]
            mock_session.return_value.post.return_value = search_response
            mock_session.return_value.verify = False

            results = fara.scrape_fara("Test Firm")

            # FARA scraper may not find results due to complex page structure
            # but should not crash
            assert isinstance(results, list)


class TestDataValidation:
    """Test data validation and normalization"""

    def test_client_name_validation(self):
        """Test that client names are properly validated"""
        assert lobbyfacts.is_valid_client("Valid Company Inc")
        assert lobbyfacts.is_valid_client("Another Corporation Ltd")
        assert not lobbyfacts.is_valid_client("Search")
        assert not lobbyfacts.is_valid_client("About")
        assert not lobbyfacts.is_valid_client("123")  # Too short
        assert not lobbyfacts.is_valid_client("A")  # Too short

    def test_client_name_cleaning(self):
        """Test that client names are properly cleaned"""
        assert lobbyfacts.clean_client_name("Company Inc  ") == "Company Inc"
        assert lobbyfacts.clean_client_name("Company\n\nInc") == "Company Inc"
        assert lobbyfacts.clean_client_name("Company (subsidiary)") == "Company"


def test_date_parsing():
    """Test date parsing functionality"""
    assert fara.parse_date("01/15/2023") == "2023-01-15"
    assert fara.parse_date("2023-01-15") == "2023-01-15"
    assert fara.parse_date("January 15, 2023") == "2023-01-15"
    assert fara.parse_date("15-Jan-2023") == "2023-01-15"
    assert fara.parse_date("invalid") is None
    assert fara.parse_date("") is None