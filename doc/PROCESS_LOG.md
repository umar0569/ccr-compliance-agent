# 🛠️ Engineering Log: Crawler Implementation

## Phase 1: URL Discovery (The Crawling Strategy)

**Objective:** Reliably identify all valid law section URLs from the California Code of Regulations (Westlaw) without downloading duplicates or getting stuck in infinite loops.

### 1. Challenge: Dynamic Single-Page Application (SPA)
* **Observation:** The target site (`govt.westlaw.com`) uses heavy JavaScript. A standard HTTP GET request returns an empty shell without the actual links.
* **Solution:** Implemented `Crawl4AI` with browser automation:
    * **Scroll Logic:** Added `window.scrollTo(0, document.body.scrollHeight);` to trigger lazy-loading elements.
    * **Wait Conditions:** Added a strict `wait_for` condition (`document.querySelectorAll("a").length > 5`) to ensure the page is fully populated before scraping.

### 2. Challenge: URL Canonicalization
* **Issue:** Initial attempts stripped query parameters (`?guid=...`) to "clean" the URLs.
* **Discovery:** Westlaw relies on the `guid` parameter to distinguish between different Titles (e.g., Title 1 vs. Title 2). Stripping it caused the crawler to treat all 28 titles as the same page.
* **Fix:** Updated the crawler to preserve the full URL, including query parameters, ensuring distinct folders were correctly identified.

### 3. Challenge: Idempotency & Resumability
* **Requirement:** The crawl process is long (hours) and prone to network interruptions.
* **Strategy:** Implemented a "Smart Resume" system:
    * **Visited Set:** Tracks folders (Table of Contents) that have been fully scanned.
    * **Discovered Set:** Tracks individual Law Sections (Files) that have been found.
    * **Recovery Logic:** If the script stops, we can clear the "Visited Folders" log (to force re-scanning the directory structure) while keeping the "Discovered Sections" log (to prevent duplicate entries).
* **Outcome:** Successfully resumed the crawl after an interruption at ~3,100 URLs, ultimately collecting **5,300+ unique section URLs** without duplication.

### 4. Challenge: Infinite Loops & "Breadcrumbs"
* **Issue:** The crawler began following "Home" and "Back" links, causing it to re-crawl the root directory repeatedly.
* **Fix:** Added filtering logic to ignore breadcrumb links (`originationContext=documenttoc`) and focus strictly on "Browse" (Folder) and "Document" (File) paths.

## Phase 2: Content Extraction (Current Status)

**Objective:** Convert the identified 5,300+ URLs into structured data (JSONL) containing Clean Markdown and Metadata.

* **Status:** URL Discovery complete. Extraction script prepared.
* **Strategy:**
    * **Batch Processing:** Processing URLs in chunks of 5 (concurrent tabs) to balance speed with rate-limiting politeness.
    * **Selective Extraction:** Parsing specific HTML `div` IDs (`co_docContent`) to isolate legal text from website navigation clutter.
    * **Metadata:** Extracting Breadcrumbs (Title > Division > Chapter) to establish the "Canonical Hierarchy" required by the assignment.

---

### Technical Stats
* **Library:** `Crawl4AI` (AsyncWebCrawler)
* **Total URLs Discovered:** ~5,300+
* **Data Format:** JSON Lines (`.jsonl`)
* **Resilience:** Fully idempotent (safe to re-run without data loss).