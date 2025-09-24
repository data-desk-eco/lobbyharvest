# Comprehensive database of lobbying firm clients

The purpose of this project is to build a reliable but extremely minimal data pipeline that aggregates information on a lobbying firm's clients from a range of public sources. Ultimately, the pipeline should be able to take a company name — e.g. "FTI Consulting" — and query all the relevant data sources to extract a normalised list of the firm's clients, including the period in which they were a client (at the highest possible level of granularity given in the source) and any IDs for the clients. An example data structure might be a CSV with columns `firm_name`, `firm_registration_number`, `client_name`, `client_registration_number`, `client_start_date`, `client_end_date`.

The tool should be developed as a CLI using Python and Click, keeping code as minimal as possible. It should contain a separate module for each data access tool, which browses to the relevant website, sends a query and extracts the data using Playwright. When developing the tools, consider building other useful utilities to help you work more effectively, e.g. a tool to take screenshots of the running browser to aid with navigation. If you do build these, do them as shell scripts and clearly separate them from the rest of the code.

Use `uv` for everything and remember: keep the code and architecture _minimal_!
 
## Data sources

1. **U.S. Court bankruptcy documents** (ignore for now)
   1. [Type 1](https://drive.google.com/file/d/1mvZCTXcopd3SG90_nZsHGBtluUEoJHCf/view?usp=sharing)  
   2. [Type 2](https://drive.google.com/file/d/1qP1JISaaw4F4d8rV9PSScgB0kcFvMza0/view?usp=sharing)  
2. **Lobby Facts records**  
   1. [https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67](https://www.lobbyfacts.eu/datacard/fti-consulting-belgium?rid=29896393398-67) \-(specifically the ‘**Clients for closed financial year)**  
3. **UK Lobbying Register**   
   1. [https://lobbying-register.uk/](https://lobbying-register.uk/)  
4. **UK Office of the Registrar of Consultant Lobbyists**  
   1. [https://orcl.my.site.com/CLR\_Search](https://orcl.my.site.com/CLR_Search)   
5. **FR HATVP Register"**	  
   1. [https://www.hatvp.fr/](https://www.hatvp.fr/)  
6. **DE Deutscher Bundestag Lobby Register**  
   1. [https://www.lobbyregister.bundestag.de/suche-im-lobbyregister?lang=de](https://www.lobbyregister.bundestag.de/suche-im-lobbyregister?lang=de)   
7. **AU Australian Lobbying Register"**	  
   1. [https://lobbyists.ag.gov.au/register](https://lobbyists.ag.gov.au/register)   
8. **AU "Foreign Influence Transparency Scheme Public Register**  
   1. [https://transparency.ag.gov.au/](https://transparency.ag.gov.au/)  
9. **CA Canada Registry of Lobbyists**  
   1. [https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/guest](https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/guest)  
10. **AT "Austrian Lobbying and Advocacy Register**  
    1. [https://lobbyreg.justiz.gv.at/](https://lobbyreg.justiz.gv.at/)   
11. **FARA**  
    1. [https://efile.fara.gov/ords/fara/f?p=1381:200:6969228758052:::RP,200:P200\_REG\_NUMBER:7120](https://efile.fara.gov/ords/fara/f?p=1381:200:6969228758052:::RP,200:P200_REG_NUMBER:7120)   
12. **Cyprus lobbying register**  
    1. [https://www.iaac.org.cy/iaac/iaac.nsf/table3\_el/table3\_el?openform](https://www.iaac.org.cy/iaac/iaac.nsf/table3_el/table3_el?openform)   
13. **Irish lobbying register**  
    1. [FTI Consulting Management Solutions Limited](https://www.lobbying.ie/organisation/1234/fti-consulting?currentPage=0&pageSize=20&queryText=&subjectMatters=&subjectMatterAreas=&publicBodys=&jobTitles=&returnDateFrom=&returnDateTo=&period=&dpo=&client=&responsible=&lobbyist=&lobbyistId=1234)  
14. **Italian Lobbying Register**  
    1. [https://rappresentantidiinteressi.camera.it/sito/legal\_353/scheda-persona-giuridica.html](https://rappresentantidiinteressi.camera.it/sito/legal_353/scheda-persona-giuridica.html)    
15. **Open Secrets US Lobbying database**  
    1. [FTI Government Affairs Lobbying Profile • OpenSecrets](https://www.opensecrets.org/federal-lobbying/firms/summary?cycle=2025&id=D000066805) 
- Make extensive use of subagents for any task that you feel can be delegated.
- Commit regularly to facilitate rollbacks

## Current Project Status (Sept 2025)

### Implementation Summary
- **10 scrapers implemented** using Playwright and requests/BeautifulSoup
- **50% success rate** (5 working, 5 need fixes)
- **CLI fully functional** with all scrapers integrated
- **Parallel development approach** proven effective using TMUX

### ✅ Working Scrapers (5/10 implemented)
1. **Lobbyfacts EU** - 73+ clients extracted (requires direct URL)
2. **UK ORCL** - Fully automated, 100% reliable
3. **French HATVP** - Excellent (200+ clients for some firms)
4. **Australian Lobbying** - Works with local firm names
5. **Cyprus** - 6+ clients extracted

### ❌ Need Fixing (5/10 implemented)
1. **UK Lobbying** - JS rendering issues
2. **FARA (US)** - Registration lookup failing
3. **Austrian** - Search form not detected
4. **Italian** - Registry navigation issues
5. **AU Foreign Influence** - Angular app challenges

### 📝 Not Yet Implemented (5/15 total)
- German Bundestag Register
- Canadian Registry
- Irish Registry (direct URL available)
- OpenSecrets US (direct URL available)
- US Bankruptcy docs (deferred)

## Urgent Action Plan

### Fix Broken Scrapers (Priority 1)
1. **FARA**: Use direct URL pattern like `P200_REG_NUMBER:7120`
2. **Italian**: Navigate directly to `/sito/registro.html`
3. **UK Lobbying**: Add proper JS wait conditions

### Quick Wins (Priority 2)
1. **Irish**: Direct URL provided - straightforward implementation
2. **OpenSecrets**: Direct URL provided - simple HTML scraping
3. **German**: Standard form-based site

### Testing Protocol
- Run `python test_scrapers.py` for comprehensive testing
- Test with country-appropriate firms (not just FTI)
- Success = ANY firm returns results

### Architecture Notes
- Keep minimal: one scraper per file in `src/scrapers/`
- Use Playwright only when necessary (JS-heavy sites)
- Prefer requests/BeautifulSoup for simple HTML
- All scrapers must have `scrape(firm_name)` function