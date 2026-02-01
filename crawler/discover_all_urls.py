import asyncio
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# --- CONFIGURATION ---
BASE_URL = "https://govt.westlaw.com"
START_URL = "https://govt.westlaw.com/calregs/Browse/Home/California/CaliforniaCodeofRegulations?transitionType=Default&contextData=%28sc.Default%29"

OUTPUT_FILE = "data/discovered_section_urls.jsonl"
CHECKPOINT_FILE = "data/visited_urls.txt"

# --- STATE MANAGEMENT ---
visited_urls = set()
existing_sections = set() # To track what we already found
urls_to_visit = [START_URL]

def load_state():
    # 1. Load Visited Folders (The "Done List")
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            for line in f:
                visited_urls.add(line.strip())
    
    # 2. Load Existing Sections (So we don't save duplicates)
    if os.path.exists(OUTPUT_FILE):
        print("Loading existing results to avoid duplicates...")
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    if line.strip():
                        data = json.loads(line)
                        existing_sections.add(data["section_url"])
                except:
                    pass # Ignore broken lines
        print(f" -> {len(existing_sections)} sections already saved. Skipping these.")

    print(f"Resuming... {len(visited_urls)} folders visited.")

def save_visit(url):
    visited_urls.add(url)
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(url + "\n")

async def discover_urls():
    load_state()
    os.makedirs("data", exist_ok=True)

    # Condition: Wait until we see at least 5 links (ensures page loaded)
    WAIT_CONDITION = """() => {
        return document.querySelectorAll("a").length > 5;
    }"""

    async with AsyncWebCrawler(verbose=True) as crawler:
        while urls_to_visit:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue

            print(f"\nCrawling: {current_url}")
            
            # --- FETCH PAGE ---
            result = await crawler.arun(
                url=current_url,
                js_code="window.scrollTo(0, document.body.scrollHeight);",
                wait_for=f"js:{WAIT_CONDITION}", 
                bypass_cache=True,
                magic=True
            )
            
            if not result.success:
                print(f"Failed to fetch: {current_url}")
                # Optional: Add back to end of queue to retry later
                # urls_to_visit.append(current_url) 
                continue

            soup = BeautifulSoup(result.html, "html.parser")
            all_links = soup.find_all("a", href=True)
            
            # print(f"   [Debug] Found {len(all_links)} links.")
            
            new_links_found = 0
            for a in all_links:
                href = a["href"]
                
                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = BASE_URL + href

                # CASE 1: Folder (Title, Chapter, etc.)
                if "/calregs/Browse/" in href:
                    if full_url not in visited_urls and full_url not in urls_to_visit:
                        if full_url != current_url:
                            urls_to_visit.append(full_url)
                            new_links_found += 1

                # CASE 2: File (Law Section)
                elif "/calregs/Document/" in href:
                    # --- SMART CHECK: SKIP IF ALREADY FOUND ---
                    if full_url in existing_sections:
                        continue 

                    record = {
                        "section_url": full_url,
                        "source_page": current_url,
                        "status": "discovered",
                        "retrieved_at": datetime.utcnow().isoformat()
                    }
                    
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record) + "\n")
                        print(f"  -> Found NEW Section: {full_url}")
                        existing_sections.add(full_url) # Add to memory so we don't save it again

            save_visit(current_url)
            print(f"  Processed. Added {new_links_found} new folders to queue.")
            
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(discover_urls())