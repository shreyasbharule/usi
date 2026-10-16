# USI — Urban Systems Intelligence website

## Automated publication feed

The publications section is data-driven.

- **Identity/source list:** ORCID `0000-0002-9507-1279`
- **Metadata enrichment:** Crossref for works that have a DOI
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
