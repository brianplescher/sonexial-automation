# Sonexial Automation (Retired Prototype)

> [!NOTE]
> **This standalone prototype has been retired and consolidated.**
> The GEO scanning, SSRF protection, scoring rubric, and agentic pitch generation logic have been ported into the production **`sonexial-website`** repository:
> - **Backend / Scanner Service**: [`agent/src/scanner.js`](https://github.com/brianplescher/sonexial-website/blob/main/agent/src/scanner.js) and [`agent/src/pitch.js`](https://github.com/brianplescher/sonexial-website/blob/main/agent/src/pitch.js)
> - **API Endpoints**: `POST /api/scan` and `POST /api/scan/pitch` in [`agent/src/index.js`](https://github.com/brianplescher/sonexial-website/blob/main/agent/src/index.js)
> - **Frontend Audit Tool**: [`/tools/author-geo-audit/`](https://github.com/brianplescher/sonexial-website/tree/main/tools/author-geo-audit)
