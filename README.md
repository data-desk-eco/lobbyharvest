# Lobbyharvest

Minimal lobbying firm client data aggregator.

## Installation

```bash
uv pip install -e lobbyharvest/
playwright install chromium
```

## Usage

```bash
# Run specific scraper
uv run python lobbyharvest/main.py uk-orcl-register "FTI Consulting"

# With output file
uv run python lobbyharvest/main.py lobbyfacts-scrape "FTI Consulting Belgium" \
  --url "https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67" \
  -o clients.csv
```

## Testing

```bash
python test_scrapers.py
```

## Scrapers Status

- ✅ Working: Lobbyfacts, UK ORCL, French HATVP, Australian, Cyprus
- ❌ Need fixing: UK Lobbying, FARA, Austrian, Italian, AU Foreign Influence
- 📝 Not implemented: German, Canadian, Irish, OpenSecrets, Bankruptcy docs

See CLAUDE.md for implementation details and action plan.