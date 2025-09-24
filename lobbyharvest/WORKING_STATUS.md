# Lobbyharvest Working Status

## Summary
All scrapers have been converted from Playwright to lightweight requests/BeautifulSoup implementations to work on headless systems without browser dependencies.

## Working Scrapers
✅ **Lobbyfacts.eu** - Fully functional, extracts client lists from EU Transparency Register
- Successfully tested with FTI Consulting Belgium
- Returns 70+ clients with proper filtering

## Scrapers Requiring JavaScript/Complex Session Management
These scrapers have been converted but cannot extract data due to site limitations:

❌ **UK Lobbying Register** - Site requires JavaScript/SPA
❌ **Australian Lobbying Register** - Site requires JavaScript/SPA
❌ **FARA (US)** - Uses Oracle APEX with complex session management

## Test Coverage
- ✅ All scrapers have comprehensive unit tests
- ✅ Tests pass 100% (10/10 tests)
- ✅ Code quality validated with ruff linter

## Next Steps
For non-working scrapers, consider:
1. Using a headless browser service (Selenium Grid, BrowserStack)
2. Finding alternative data sources or APIs
3. Running a browser instance on a machine with X11 support

## Commands
```bash
# Test individual scrapers
uv run python main.py lobbyfacts-scrape -f "FTI Consulting Belgium" -u "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67"
uv run python main.py uk-lobbying-register "FTI Consulting"
uv run python main.py australia --firm "FTI Consulting"
uv run python main.py fara-scrape "FTI Consulting"

# Run tests
uv run pytest tests/

# Check code quality
uv run ruff check src/
```