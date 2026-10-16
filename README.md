# USI — Urban Systems Intelligence website

## Automated scholarly publication feed

The publications section is data-driven.

- **Identity/source list:** ORCID `0000-0002-9507-1279`
- **Canonical metadata enrichment:** Crossref for works that have a DOI\n- **Citation and coverage enrichment:** Google Scholar via SerpApi (`cvEv8M4AAAAJ`)\n- **Secret required:** `SERPAPI_KEY` in GitHub Actions repository secrets
- **Generated file:** `publications.json`
- **Updater:** `scripts/update_publications.py`
- **Automation:** `.github/workflows/update-publications.yml`
- **Schedule:** every Sunday at 03:17 UTC, plus manual `workflow_dispatch`

### How it works

1. GitHub Actions queries the public ORCID works endpoint.
2. DOI-bearing works are enriched with Crossref metadata.
3. The script writes `publications.json`.
4. The workflow commits the JSON only if it changed.
5. `index.html` loads the JSON in the browser and renders the newest records.
6. If the JSON cannot be loaded, the embedded publication cards remain visible as a fallback.

### Run locally

```bash
python scripts/update_publications.py
python -m http.server 8000
```

Open `http://localhost:8000/`.

### GitHub Pages

Use the repository `main` branch and root folder as the Pages source. The workflow requires repository Actions to be enabled and the `GITHUB_TOKEN` to have permission to write repository contents.

## USI v2 visual portfolio

The homepage uses labelled visual placeholders for maps, charts, flowcharts, field photographs and analytical outputs. Replace placeholder blocks in `index.html` as project visuals become available. The visual system uses semantic accents: cyan for data/intelligence, amber for planning/policy and violet for design/human-scale work.


## Publication filtering and categories

The automated feed includes a curation layer before writing `publications.json`.

### Excluded from the public publication list
- ORCID records typed as `other`
- dissertations/theses
- lectures/speeches
- exact internal record: `Shreyas Lab Framework`
- empty/untitled records

### Public categories
- **Journal Articles** — journal articles and Scholar-only records with a publication venue
- **Books & Chapters** — books, edited books, book chapters and monographs
- **Conference Papers** — proceedings and conference/symposium/congress records
- **Preprints & Working Papers** — posted content, preprints and working papers
- **Data & Research Resources** — datasets, databases and online research resources
- **Other Scholarly Works** — Scholar records that cannot be classified confidently

The generated JSON includes `category`, `category_label`, `category_counts`,
`excluded_count` and a `filter_rules_version` for transparency and future maintenance.
