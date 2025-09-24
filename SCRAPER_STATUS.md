# Lobbyharvest Scraper Development Status

## ✅ Completed Scrapers (6)

1. **Lobbyfacts** (feature/lobbyfacts) - MERGED
   - Module: `lobbyharvest/src/scrapers/lobbyfacts.py`
   - URL: https://www.lobbyfacts.eu/
   - Status: Implemented and merged to main

2. **UK Lobbying Register** (feature/uk-lobbying) - MERGED
   - Module: `lobbyharvest/src/scrapers/uk_lobbying.py`
   - URL: https://lobbying-register.uk/
   - Status: Implemented and merged to main

3. **Australian Lobbying Register** (feature/australia) - READY TO MERGE
   - Module: `lobbyharvest/src/scrapers/australia_lobbying.py`
   - URL: https://lobbyists.ag.gov.au/register
   - Status: Implemented, committed

4. **FARA** (feature/fara) - READY TO MERGE
   - Module: `lobbyharvest/src/scrapers/fara.py`
   - URL: https://efile.fara.gov/ords/fara/f?p=1381:200
   - Status: Implemented, committed

5. **Irish Lobbying Register** (feature/irish) - READY TO MERGE
   - Module: `lobbyharvest/src/scrapers/irish_lobbying.py`
   - URL: https://www.lobbying.ie/
   - Status: Implemented, committed

6. **OpenSecrets** (feature/opensecrets) - READY TO MERGE
   - Module: `lobbyharvest/src/scrapers/opensecrets.py`
   - URL: https://www.opensecrets.org/federal-lobbying/firms
   - Status: Implemented, committed

## 🔄 In Progress (2)

1. **German Bundestag** (feature/germany)
   - Agent: Active in tmux session 'germany'
   - URL: https://www.lobbyregister.bundestag.de/

2. **Canada Registry** (feature/canada)
   - Agent: Active in tmux session 'canada'
   - URL: https://lobbycanada.gc.ca/

## 📝 Not Started (6)

1. **UK ORCL** - https://orcl.my.site.com/CLR_Search
2. **French HATVP** - https://www.hatvp.fr/
3. **Austrian Register** - https://lobbyreg.justiz.gv.at/
4. **Cyprus Register** - https://www.iaac.org.cy/
5. **Italian Register** - https://rappresentantidiinteressi.camera.it/
6. **Foreign Influence Transparency (AU)** - https://transparency.ag.gov.au/

## 🛠 Infrastructure Created

- **Utilities**:
  - `/scripts/screenshot.sh` - Browser screenshot utility
  - `/scripts/monitor_agents.sh` - Monitor tmux agent progress
  - `/scripts/merge_branches.sh` - Automated branch merging
  - `/src/utils/normalize.py` - Data normalization utilities
  - `/src/aggregator.py` - Main data aggregation module

## Next Steps

1. Monitor and complete Germany and Canada scrapers
2. Merge remaining completed branches (australia, fara, irish, opensecrets)
3. Test all scrapers with real queries
4. Implement remaining 6 scrapers
5. Create comprehensive test suite